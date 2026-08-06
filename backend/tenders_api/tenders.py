"""
Logique métier CRUD + workflow des AO (module 3, périmètre : DRAFT jusqu'à
APPROVED/REJECTED/ARCHIVED — QUEUED_FOR_PUBLICATION/PUBLISHED/EXPIRED sont
pilotés par le Publication Coordinator, voir transitions.py).

Chaque fonction reçoit un curseur ouvert dans une transaction déjà démarrée
par db.run_in_transaction (appelé depuis handler.py) — aucune I/O de
connexion ici.
"""
import base64
import json
import uuid
from datetime import datetime, timezone

from auth import require_active, require_mfa, require_role
from content_hash import compute_content_hash
from errors import ForbiddenError, NotFoundError, ValidationError
from transitions import can_transition

ALLOWED_SECTORS = {"PUBLIC", "PRIVATE"}
ALLOWED_PROCUREMENT_TYPES = {"TRAVAUX", "FOURNITURES", "SERVICES", "PRESTATIONS_INTELLECTUELLES"}
ALLOWED_PROCEDURE_TYPES = {"OUVERT", "RESTREINT", "GRE_A_GRE", "CONSULTATION", "CONCOURS"}

CREATE_REQUIRED_FIELDS = ("title", "description", "sector", "organization_id", "country_id", "submission_deadline")

# Colonnes de contenu métier modifiables via create/update (hors category_ids,
# géré à part dans tender_categories — table de liaison many-to-many).
CONTENT_COLUMNS = (
    "reference_number", "title", "description", "sector", "organization_id", "country_id",
    "procurement_type", "procedure_type", "location_region", "location_city",
    "estimated_budget", "currency", "submission_deadline",
    "eligibility_criteria", "required_documents",
    "contact_name", "contact_role", "contact_email", "contact_phone",
    "source_name", "source_url",
)

SUBMIT_REQUIRED_FIELDS = (
    "title", "description", "sector", "organization_id", "country_id",
    "submission_deadline", "procurement_type", "procedure_type", "contact_email",
)


# --- Visibilité par rôle ------------------------------------------------

def _visibility_where(user):
    if user["role"] == "ADMIN":
        return "TRUE", {}
    if user["role"] == "AGENT":
        return "created_by = %(self_id)s", {"self_id": user["id"]}
    if user["role"] == "REVIEWER":
        return "(status = 'PENDING_REVIEW' OR reviewed_by = %(self_id)s)", {"self_id": user["id"]}
    raise ForbiddenError("Rôle inconnu.")


# --- Validation -----------------------------------------------------------

def _validate_enum_fields(payload):
    fields = {}
    if payload.get("sector") is not None and payload["sector"] not in ALLOWED_SECTORS:
        fields["sector"] = f"doit être l'un de {sorted(ALLOWED_SECTORS)}"
    if payload.get("procurement_type") is not None and payload["procurement_type"] not in ALLOWED_PROCUREMENT_TYPES:
        fields["procurement_type"] = f"doit être l'un de {sorted(ALLOWED_PROCUREMENT_TYPES)}"
    if payload.get("procedure_type") is not None and payload["procedure_type"] not in ALLOWED_PROCEDURE_TYPES:
        fields["procedure_type"] = f"doit être l'un de {sorted(ALLOWED_PROCEDURE_TYPES)}"
    if fields:
        raise ValidationError("Champs invalides.", fields=fields)


def _require_fields(payload, required_fields):
    missing = [f for f in required_fields if not payload.get(f)]
    if missing:
        raise ValidationError("Champs obligatoires manquants.", fields={f: "requis" for f in missing})


def validate_references(cur, organization_id, country_id, category_ids):
    if organization_id is not None:
        cur.execute("SELECT 1 FROM organizations WHERE id = %(id)s AND deleted_at IS NULL", {"id": organization_id})
        if cur.fetchone() is None:
            raise ValidationError("organization_id introuvable.", fields={"organization_id": "n'existe pas"})
    if country_id is not None:
        cur.execute("SELECT 1 FROM countries WHERE id = %(id)s", {"id": country_id})
        if cur.fetchone() is None:
            raise ValidationError("country_id introuvable.", fields={"country_id": "n'existe pas"})
    if category_ids:
        cur.execute(
            "SELECT id FROM categories WHERE id = ANY(%(ids)s) AND is_active = TRUE",
            {"ids": list(category_ids)},
        )
        found = {row["id"] for row in cur.fetchall()}
        missing = set(category_ids) - found
        if missing:
            raise ValidationError("category_ids introuvables.", fields={"category_ids": sorted(missing)})


def validate_required_for_submit(tender, category_ids):
    missing = [f for f in SUBMIT_REQUIRED_FIELDS if not tender.get(f)]
    if not category_ids:
        missing.append("category_ids")
    deadline = tender.get("submission_deadline")
    if deadline and deadline <= datetime.now(timezone.utc):
        missing.append("submission_deadline (doit être future)")
    if missing:
        raise ValidationError(
            "Champs obligatoires manquants pour soumettre à révision.", fields={"missing": missing}
        )


# --- Helpers internes -------------------------------------------------

def _get_tender(cur, tender_id):
    cur.execute("SELECT * FROM tenders WHERE id = %(id)s", {"id": tender_id})
    return cur.fetchone()

def _get_visible_tender(cur, user, tender_id):
    visibility_sql, params = _visibility_where(user)
    params = {**params, "id": tender_id}
    cur.execute(
        f"SELECT * FROM tenders WHERE id = %(id)s AND deleted_at IS NULL AND {visibility_sql}", params
    )
    row = cur.fetchone()
    if row is None:
        raise NotFoundError("AO introuvable.")
    return row


def _get_category_ids(cur, tender_id):
    cur.execute("SELECT category_id FROM tender_categories WHERE tender_id = %(id)s", {"id": tender_id})
    return [row["category_id"] for row in cur.fetchall()]


def _set_categories(cur, tender_id, category_ids, primary_category_id):
    cur.execute("DELETE FROM tender_categories WHERE tender_id = %(id)s", {"id": tender_id})
    for category_id in category_ids or []:
        cur.execute(
            """
            INSERT INTO tender_categories (tender_id, category_id, is_primary)
            VALUES (%(tender_id)s, %(category_id)s, %(is_primary)s)
            """,
            {
                "tender_id": tender_id,
                "category_id": category_id,
                "is_primary": category_id == primary_category_id,
            },
        )


def _write_audit(cur, user, action, entity_id, details, correlation_id, ip_address):
    cur.execute(
        """
        INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, details, ip_address, correlation_id)
        VALUES (%(actor)s, %(action)s, 'tender', %(entity_id)s, %(details)s, %(ip)s, %(correlation_id)s)
        """,
        {
            "actor": user["id"],
            "action": action,
            "entity_id": entity_id,
            "details": json.dumps(details, default=str),
            "ip": ip_address,
            "correlation_id": correlation_id,
        },
    )


def _apply_transition(cur, tender, to_status, user, reason, correlation_id, ip_address, extra_updates=None):
    from_status = tender["status"]
    extra_updates = extra_updates or {}

    set_clauses = ["status = %(to_status)s", "updated_at = now()"]
    params = {"to_status": to_status, "id": tender["id"]}
    for column, value in extra_updates.items():
        set_clauses.append(f"{column} = %({column})s")
        params[column] = value

    cur.execute(f"UPDATE tenders SET {', '.join(set_clauses)} WHERE id = %(id)s RETURNING *", params)
    updated = cur.fetchone()

    cur.execute(
        """
        INSERT INTO tender_status_history (tender_id, from_status, to_status, changed_by, actor_type, reason)
        VALUES (%(tender_id)s, %(from_status)s, %(to_status)s, %(changed_by)s, 'USER', %(reason)s)
        """,
        {
            "tender_id": tender["id"], "from_status": from_status, "to_status": to_status,
            "changed_by": user["id"], "reason": reason,
        },
    )
    _write_audit(cur, user, f"STATUS_{to_status}", tender["id"], {"from": from_status, "to": to_status, "reason": reason}, correlation_id, ip_address)
    return updated


def _encode_cursor(row):
    raw = f"{row['created_at'].isoformat()}|{row['id']}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor):
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_str, tender_id = raw.split("|", 1)
        return datetime.fromisoformat(created_at_str), tender_id
    except Exception as exc:  # noqa: BLE001
        raise ValidationError("Curseur de pagination invalide.") from exc


# --- Opérations exposées à handler.py ----------------------------------

def list_tenders(cur, user, filters, cursor, page_size=20):
    where_clauses = ["deleted_at IS NULL"]
    visibility_sql, params = _visibility_where(user)
    where_clauses.append(visibility_sql)

    if filters.get("status"):
        where_clauses.append("status = %(status)s")
        params["status"] = filters["status"]
    if filters.get("sector"):
        where_clauses.append("sector = %(sector)s")
        params["sector"] = filters["sector"]
    if filters.get("procedure_type"):
        where_clauses.append("procedure_type = %(procedure_type)s")
        params["procedure_type"] = filters["procedure_type"]
    if filters.get("country_id"):
        where_clauses.append("country_id = %(country_id)s")
        params["country_id"] = filters["country_id"]
    if filters.get("category_id"):
        where_clauses.append(
            "id IN (SELECT tender_id FROM tender_categories WHERE category_id = %(category_id)s)"
        )
        params["category_id"] = filters["category_id"]
    if filters.get("q"):
        where_clauses.append("(title ILIKE %(q)s OR reference_number ILIKE %(q)s)")
        params["q"] = f"%{filters['q']}%"
    if cursor:
        cursor_created_at, cursor_id = _decode_cursor(cursor)
        where_clauses.append("(created_at, id) < (%(cursor_created_at)s, %(cursor_id)s)")
        params["cursor_created_at"] = cursor_created_at
        params["cursor_id"] = cursor_id

    params["limit"] = page_size + 1
    cur.execute(
        f"""
        SELECT * FROM tenders
        WHERE {' AND '.join(where_clauses)}
        ORDER BY created_at DESC, id DESC
        LIMIT %(limit)s
        """,
        params,
    )
    rows = cur.fetchall()
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = _encode_cursor(rows[-1]) if has_more and rows else None
    for row in rows:
        row["category_ids"] = _get_category_ids(cur, row["id"])
    return rows, next_cursor


def get_tender(cur, user, tender_id):
    tender = _get_visible_tender(cur, user, tender_id)
    tender["category_ids"] = _get_category_ids(cur, tender_id)
    return tender


def get_status_history(cur, user, tender_id):
    _get_visible_tender(cur, user, tender_id)  # lève NotFoundError si non visible
    cur.execute(
        """
        SELECT from_status, to_status, changed_by, actor_type, reason, created_at
        FROM tender_status_history WHERE tender_id = %(id)s ORDER BY created_at ASC
        """,
        {"id": tender_id},
    )
    return cur.fetchall()


def create_tender(cur, user, payload, correlation_id, ip_address):
    require_role(user, {"AGENT"})
    _require_fields(payload, CREATE_REQUIRED_FIELDS)
    _validate_enum_fields(payload)

    category_ids = payload.get("category_ids") or []
    primary_category_id = payload.get("primary_category_id")
    if primary_category_id and primary_category_id not in category_ids:
        raise ValidationError("primary_category_id doit être dans category_ids.")

    validate_references(cur, payload["organization_id"], payload["country_id"], category_ids)

    tender_id = str(uuid.uuid4())
    content = {col: payload.get(col) for col in CONTENT_COLUMNS}
    content["category_ids"] = category_ids
    content_hash = compute_content_hash(content)

    columns = ["id", "created_by", "status", "content_hash", *CONTENT_COLUMNS]
    params = {"id": tender_id, "created_by": user["id"], "status": "DRAFT", "content_hash": content_hash, **content}
    placeholders = ", ".join(f"%({c})s" for c in columns)
    cur.execute(
        f"INSERT INTO tenders ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *",
        params,
    )
    tender = cur.fetchone()

    _set_categories(cur, tender_id, category_ids, primary_category_id)
    cur.execute(
        """
        INSERT INTO tender_status_history (tender_id, from_status, to_status, changed_by, actor_type, reason)
        VALUES (%(tender_id)s, NULL, 'DRAFT', %(changed_by)s, 'USER', NULL)
        """,
        {"tender_id": tender_id, "changed_by": user["id"]},
    )
    _write_audit(cur, user, "CREATE", tender_id, {"title": payload.get("title")}, correlation_id, ip_address)

    tender["category_ids"] = category_ids
    return tender


def update_tender(cur, user, tender_id, payload, correlation_id, ip_address):
    require_role(user, {"AGENT"})
    _validate_enum_fields(payload)

    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    if tender["created_by"] != user["id"]:
        raise ForbiddenError("Seul le créateur peut modifier cet AO.")
    if tender["status"] not in ("DRAFT", "REVISION_REQUESTED"):
        raise ForbiddenError(f"Impossible de modifier un AO au statut {tender['status']}.")

    category_ids = payload.get("category_ids")
    if category_ids is None:
        category_ids = _get_category_ids(cur, tender_id)
    primary_category_id = payload.get("primary_category_id")

    merged = {col: payload.get(col, tender.get(col)) for col in CONTENT_COLUMNS}
    validate_references(cur, merged["organization_id"], merged["country_id"], category_ids)

    content = dict(merged)
    content["category_ids"] = category_ids
    content_hash = compute_content_hash(content)

    set_clauses = [f"{c} = %({c})s" for c in CONTENT_COLUMNS] + ["content_hash = %(content_hash)s", "updated_at = now()"]
    params = {**merged, "content_hash": content_hash, "id": tender_id}
    cur.execute(
        f"UPDATE tenders SET {', '.join(set_clauses)} WHERE id = %(id)s RETURNING *",
        params,
    )
    updated = cur.fetchone()

    if "category_ids" in payload:
        _set_categories(cur, tender_id, category_ids, primary_category_id)
    _write_audit(cur, user, "UPDATE", tender_id, {"fields": list(payload.keys())}, correlation_id, ip_address)

    updated["category_ids"] = category_ids
    return updated


def submit_for_review(cur, user, tender_id, correlation_id, ip_address):
    require_role(user, {"AGENT"})
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    is_owner = tender["created_by"] == user["id"]
    category_ids = _get_category_ids(cur, tender_id)

    can_transition(
        role=user["role"], from_status=tender["status"], to_status="PENDING_REVIEW",
        is_owner=is_owner, mfa_enabled=user["mfa_enabled"], reason=None,
    )
    validate_required_for_submit(tender, category_ids)
    return _apply_transition(cur, tender, "PENDING_REVIEW", user, None, correlation_id, ip_address)


def return_to_agent(cur, user, tender_id, reason, correlation_id, ip_address):
    require_role(user, {"REVIEWER"})
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    can_transition(
        role=user["role"], from_status=tender["status"], to_status="REVISION_REQUESTED",
        is_owner=False, mfa_enabled=user["mfa_enabled"], reason=reason,
    )
    return _apply_transition(cur, tender, "REVISION_REQUESTED", user, reason, correlation_id, ip_address, {"reviewed_by": user["id"]})


def endorse(cur, user, tender_id, correlation_id, ip_address):
    require_role(user, {"REVIEWER"})
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    if tender["status"] != "PENDING_REVIEW":
        raise ForbiddenError("Seul un AO PENDING_REVIEW peut être endossé.")

    cur.execute(
        "UPDATE tenders SET reviewed_by = %(reviewer)s, updated_at = now() WHERE id = %(id)s RETURNING *",
        {"reviewer": user["id"], "id": tender_id},
    )
    updated = cur.fetchone()
    _write_audit(cur, user, "ENDORSE", tender_id, {}, correlation_id, ip_address)
    return updated


def approve(cur, user, tender_id, correlation_id, ip_address):
    require_role(user, {"ADMIN"})
    require_mfa(user)
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    can_transition(
        role=user["role"], from_status=tender["status"], to_status="APPROVED",
        is_owner=False, mfa_enabled=user["mfa_enabled"], reason=None,
    )
    return _apply_transition(cur, tender, "APPROVED", user, None, correlation_id, ip_address, {"approved_by": user["id"]})


def reject(cur, user, tender_id, reason, correlation_id, ip_address):
    require_role(user, {"ADMIN"})
    require_mfa(user)
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    can_transition(
        role=user["role"], from_status=tender["status"], to_status="REJECTED",
        is_owner=False, mfa_enabled=user["mfa_enabled"], reason=reason,
    )
    return _apply_transition(cur, tender, "REJECTED", user, reason, correlation_id, ip_address)


def archive(cur, user, tender_id, correlation_id, ip_address):
    require_role(user, {"ADMIN"})
    require_mfa(user)
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    can_transition(
        role=user["role"], from_status=tender["status"], to_status="ARCHIVED",
        is_owner=False, mfa_enabled=user["mfa_enabled"], reason=None,
    )
    return _apply_transition(cur, tender, "ARCHIVED", user, None, correlation_id, ip_address)


def delete_tender(cur, user, tender_id, correlation_id, ip_address):
    require_role(user, {"ADMIN"})
    tender = _get_tender(cur, tender_id)
    if tender is None or tender["deleted_at"] is not None:
        raise NotFoundError("AO introuvable.")
    if tender["status"] != "DRAFT":
        raise ForbiddenError("Seul un AO DRAFT peut être supprimé.")

    cur.execute(
        "UPDATE tenders SET deleted_at = now(), updated_at = now() WHERE id = %(id)s",
        {"id": tender_id},
    )
    _write_audit(cur, user, "DELETE", tender_id, {}, correlation_id, ip_address)
