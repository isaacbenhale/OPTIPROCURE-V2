"""
Calcul de content_hash — sert au Publication Coordinator (module 5) pour
détecter les AO réellement modifiés depuis le dernier batch. Recalculé
quand le CONTENU métier change (create_tender/update_tender) ou quand la
liste des documents joints change (module 02, voir documents.py) — jamais
sur une simple transition de statut.
"""
import hashlib
import json

# Champs de contenu métier visibles une fois l'AO publié. Exclut
# explicitement : id, status, created_by, reviewed_by, approved_by,
# created_at, updated_at, deleted_at, content_hash lui-même.
# document_ids : liste des documents joints non supprimés (module 02) — un
# ajout/retrait de pièce jointe doit invalider le hash, la fiche publique
# affichera la liste des documents disponibles.
CONTENT_FIELDS = (
    "reference_number", "title", "description", "sector",
    "organization_id", "country_id", "category_ids",
    "procurement_type", "procedure_type",
    "location_region", "location_city",
    "estimated_budget", "currency",
    "submission_deadline",
    "eligibility_criteria", "required_documents",
    "contact_name", "contact_role", "contact_email", "contact_phone",
    "source_name", "source_url",
    "document_ids",
)


def compute_content_hash(tender: dict) -> str:
    canonical = {}
    for field in CONTENT_FIELDS:
        value = tender.get(field)
        if isinstance(value, list):
            value = sorted(value)
        canonical[field] = value
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
