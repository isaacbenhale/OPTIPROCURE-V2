"""
Documents joints des AO (module 02) — upload/téléchargement via URL S3
présignées, jamais de payload de fichier transitant par la Lambda.

Flux volontairement simplifié en une seule étape (pas de round-trip
"confirm" séparé) : la ligne tender_documents est créée au moment où l'URL
présignée est générée. Si le navigateur n'upload jamais le fichier, la
métadonnée reste orpheline (pas de job de nettoyage pour cette première
passe) — compromis assumé pour éviter une colonne de statut supplémentaire
et un aller-retour réseau de plus, cohérent avec le périmètre MVP de
tasks/02-documents-joints-ao.md.

La limite de taille (MAX_DOCUMENT_SIZE_BYTES) porte sur la valeur déclarée
par le client à la génération de l'URL, pas sur les octets réellement
envoyés à S3 (une URL présignée PUT ne permet pas d'imposer une
Content-Length-Range côté serveur, contrairement à une URL présignée POST
avec policy — plus complexe, hors périmètre de cette passe). Acceptable ici
car seuls des utilisateurs authentifiés AGENT/REVIEWER/ADMIN du back-office
appellent cette API, jamais le public.
"""
import os
import uuid

import boto3

import tenders
from auth import require_role
from errors import ForbiddenError, NotFoundError, ValidationError

REGION = os.environ["AWS_REGION"]
DOCUMENTS_BUCKET = os.environ["DOCUMENTS_BUCKET"]

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}
MAX_DOCUMENT_SIZE_BYTES = 25 * 1024 * 1024  # 25 Mo
PRESIGNED_URL_EXPIRY_SECONDS = 300  # 5 minutes — court, cohérent avec le plan module 02

REQUIRED_UPLOAD_FIELDS = ("file_name", "content_type", "size_bytes")


def _s3_client():
    return boto3.client("s3", region_name=REGION)


def _get_owned_editable_tender(cur, user, tender_id):
    """Même règle que tenders.update_tender : propriétaire + DRAFT/REVISION_REQUESTED."""
    tender = tenders.get_tender_row(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    if tender["created_by"] != user["id"] and user["role"] != "ADMIN":
        raise ForbiddenError("Seul le créateur peut gérer les documents de cet AO.")
    if tender["status"] not in ("DRAFT", "REVISION_REQUESTED"):
        raise ForbiddenError(f"Impossible de gérer les documents d'un AO au statut {tender['status']}.")
    return tender


def _get_document_row(cur, tender_id, document_id):
    cur.execute(
        "SELECT id, tender_id, file_name, s3_key, content_type, size_bytes, uploaded_by, uploaded_at "
        "FROM tender_documents WHERE id = %(doc_id)s AND tender_id = %(tender_id)s AND deleted_at IS NULL",
        {"doc_id": document_id, "tender_id": tender_id},
    )
    document = cur.fetchone()
    if document is None:
        raise NotFoundError("Document introuvable.")
    return document


def create_upload(cur, user, tender_id, payload, correlation_id, ip_address):
    require_role(user, {"AGENT", "ADMIN"})
    _get_owned_editable_tender(cur, user, tender_id)

    missing = [f for f in REQUIRED_UPLOAD_FIELDS if not payload.get(f)]
    if missing:
        raise ValidationError("Champs obligatoires manquants.", fields={f: "requis" for f in missing})

    content_type = payload["content_type"]
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            "Type de fichier non autorisé.", fields={"content_type": sorted(ALLOWED_CONTENT_TYPES)}
        )

    size_bytes = payload["size_bytes"]
    if not isinstance(size_bytes, int) or not (0 < size_bytes <= MAX_DOCUMENT_SIZE_BYTES):
        raise ValidationError(
            "Taille de fichier invalide.",
            fields={"size_bytes": f"doit être un entier entre 1 et {MAX_DOCUMENT_SIZE_BYTES} octets"},
        )

    document_id = str(uuid.uuid4())
    s3_key = f"tenders/{tender_id}/{document_id}/{payload['file_name']}"

    cur.execute(
        """
        INSERT INTO tender_documents (id, tender_id, file_name, s3_key, content_type, size_bytes, uploaded_by)
        VALUES (%(id)s, %(tender_id)s, %(file_name)s, %(s3_key)s, %(content_type)s, %(size_bytes)s, %(uploaded_by)s)
        RETURNING id, tender_id, file_name, s3_key, content_type, size_bytes, uploaded_by, uploaded_at
        """,
        {
            "id": document_id, "tender_id": tender_id, "file_name": payload["file_name"],
            "s3_key": s3_key, "content_type": content_type, "size_bytes": size_bytes,
            "uploaded_by": user["id"],
        },
    )
    document = cur.fetchone()

    tenders.recompute_content_hash(cur, tender_id)
    tenders.write_audit(
        cur, user, "DOCUMENT_UPLOAD", tender_id, {"file_name": payload["file_name"], "document_id": document_id},
        correlation_id, ip_address,
    )

    document["upload_url"] = _s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": DOCUMENTS_BUCKET, "Key": s3_key, "ContentType": content_type},
        ExpiresIn=PRESIGNED_URL_EXPIRY_SECONDS,
    )
    return document


def list_documents(cur, user, tender_id):
    tenders.get_tender(cur, user, tender_id)  # lève NotFoundError si non visible pour ce rôle
    cur.execute(
        "SELECT id, tender_id, file_name, content_type, size_bytes, uploaded_by, uploaded_at "
        "FROM tender_documents WHERE tender_id = %(id)s AND deleted_at IS NULL ORDER BY uploaded_at DESC",
        {"id": tender_id},
    )
    return cur.fetchall()


def get_document_download_url(cur, user, tender_id, document_id):
    tenders.get_tender(cur, user, tender_id)  # visibilité
    document = _get_document_row(cur, tender_id, document_id)
    document["download_url"] = _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": DOCUMENTS_BUCKET, "Key": document["s3_key"]},
        ExpiresIn=PRESIGNED_URL_EXPIRY_SECONDS,
    )
    return document


def delete_document(cur, user, tender_id, document_id, correlation_id, ip_address):
    require_role(user, {"AGENT", "ADMIN"})
    _get_owned_editable_tender(cur, user, tender_id)
    _get_document_row(cur, tender_id, document_id)  # 404 propre si déjà supprimé/inexistant

    cur.execute(
        "UPDATE tender_documents SET deleted_at = now() WHERE id = %(doc_id)s AND tender_id = %(tender_id)s",
        {"doc_id": document_id, "tender_id": tender_id},
    )
    tenders.recompute_content_hash(cur, tender_id)
    tenders.write_audit(
        cur, user, "DOCUMENT_DELETE", tender_id, {"document_id": document_id}, correlation_id, ip_address
    )
