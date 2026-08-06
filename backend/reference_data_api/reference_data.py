"""
Logique métier CRUD des référentiels (module 01) : countries, categories,
organizations, diffusion_partnerships. Lecture ouverte à AGENT/REVIEWER/
ADMIN (nécessaire pour peupler les formulaires de création d'AO côté
tenders_api) ; écriture réservée à ADMIN + MFA (même exigence que les
actions sensibles de tenders_api — approve/reject/archive).

Chaque fonction reçoit un curseur ouvert dans une transaction déjà démarrée
par db.run_in_transaction (appelé depuis handler.py).
"""
import json

from auth import require_mfa, require_role
from errors import NotFoundError, ValidationError

ALLOWED_ORG_TYPES = {"PUBLIC_BODY", "PRIVATE_PARTNER", "DONOR", "AGGREGATOR"}
ALLOWED_PARTNERSHIP_STATUSES = {"ACTIVE", "SUSPENDED", "EXPIRED", "TERMINATED"}

WRITE_ROLES = {"ADMIN"}


def _require_fields(payload, required_fields):
    missing = [f for f in required_fields if not payload.get(f)]
    if missing:
        raise ValidationError("Champs obligatoires manquants.", fields={f: "requis" for f in missing})


def _write_audit(cur, user, action, entity_type, entity_id, details, correlation_id, ip_address):
    cur.execute(
        """
        INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, details, ip_address, correlation_id)
        VALUES (%(actor)s, %(action)s, %(entity_type)s, %(entity_id)s, %(details)s, %(ip)s, %(correlation_id)s)
        """,
        {
            "actor": user["id"],
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": json.dumps(details, default=str),
            "ip": ip_address,
            "correlation_id": correlation_id,
        },
    )


# --- Pays -----------------------------------------------------------------

def list_countries(cur, user):
    cur.execute("SELECT id, iso_code, name FROM countries ORDER BY name")
    return cur.fetchall()


def create_country(cur, user, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    _require_fields(payload, ("iso_code", "name"))
    cur.execute(
        "INSERT INTO countries (iso_code, name) VALUES (%(iso_code)s, %(name)s) RETURNING id, iso_code, name",
        {"iso_code": payload["iso_code"], "name": payload["name"]},
    )
    country = cur.fetchone()
    _write_audit(cur, user, "CREATE", "country", country["id"], {"name": payload["name"]}, correlation_id, ip_address)
    return country


# --- Catégories -------------------------------------------------------------

def list_categories(cur, user):
    cur.execute("SELECT id, parent_id, name, slug, is_active FROM categories ORDER BY name")
    return cur.fetchall()


def _validate_parent_category(cur, parent_id, self_id=None):
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise ValidationError("Une catégorie ne peut pas être son propre parent.", fields={"parent_id": "invalide"})
    cur.execute("SELECT 1 FROM categories WHERE id = %(id)s", {"id": parent_id})
    if cur.fetchone() is None:
        raise ValidationError("parent_id introuvable.", fields={"parent_id": "n'existe pas"})


def create_category(cur, user, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    _require_fields(payload, ("name", "slug"))
    parent_id = payload.get("parent_id")
    _validate_parent_category(cur, parent_id)
    cur.execute(
        """
        INSERT INTO categories (parent_id, name, slug, is_active)
        VALUES (%(parent_id)s, %(name)s, %(slug)s, %(is_active)s)
        RETURNING id, parent_id, name, slug, is_active
        """,
        {
            "parent_id": parent_id, "name": payload["name"], "slug": payload["slug"],
            "is_active": payload.get("is_active", True),
        },
    )
    category = cur.fetchone()
    _write_audit(cur, user, "CREATE", "category", category["id"], {"name": payload["name"]}, correlation_id, ip_address)
    return category


def update_category(cur, user, category_id, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    cur.execute(
        "SELECT id, parent_id, name, slug, is_active FROM categories WHERE id = %(id)s", {"id": category_id}
    )
    existing = cur.fetchone()
    if existing is None:
        raise NotFoundError("Catégorie introuvable.")

    parent_id = payload.get("parent_id", existing["parent_id"])
    _validate_parent_category(cur, parent_id, self_id=category_id)

    merged = {
        "parent_id": parent_id,
        "name": payload.get("name", existing["name"]),
        "slug": payload.get("slug", existing["slug"]),
        "is_active": payload.get("is_active", existing["is_active"]),
        "id": category_id,
    }
    cur.execute(
        """
        UPDATE categories SET parent_id = %(parent_id)s, name = %(name)s, slug = %(slug)s, is_active = %(is_active)s
        WHERE id = %(id)s
        RETURNING id, parent_id, name, slug, is_active
        """,
        merged,
    )
    updated = cur.fetchone()
    _write_audit(cur, user, "UPDATE", "category", category_id, {"fields": list(payload.keys())}, correlation_id, ip_address)
    return updated


# --- Organisations ----------------------------------------------------------

def list_organizations(cur, user):
    cur.execute(
        "SELECT id, name, org_type, country_id, website, contact_email, is_active "
        "FROM organizations WHERE deleted_at IS NULL ORDER BY name"
    )
    return cur.fetchall()


def _validate_org_type(org_type):
    if org_type not in ALLOWED_ORG_TYPES:
        raise ValidationError("org_type invalide.", fields={"org_type": f"doit être l'un de {sorted(ALLOWED_ORG_TYPES)}"})


def _validate_country(cur, country_id):
    if country_id is None:
        return
    cur.execute("SELECT 1 FROM countries WHERE id = %(id)s", {"id": country_id})
    if cur.fetchone() is None:
        raise ValidationError("country_id introuvable.", fields={"country_id": "n'existe pas"})


def create_organization(cur, user, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    _require_fields(payload, ("name", "org_type"))
    _validate_org_type(payload["org_type"])
    country_id = payload.get("country_id")
    _validate_country(cur, country_id)

    cur.execute(
        """
        INSERT INTO organizations (name, org_type, country_id, website, contact_email, is_active)
        VALUES (%(name)s, %(org_type)s, %(country_id)s, %(website)s, %(contact_email)s, %(is_active)s)
        RETURNING id, name, org_type, country_id, website, contact_email, is_active
        """,
        {
            "name": payload["name"], "org_type": payload["org_type"], "country_id": country_id,
            "website": payload.get("website"), "contact_email": payload.get("contact_email"),
            "is_active": payload.get("is_active", True),
        },
    )
    org = cur.fetchone()
    _write_audit(cur, user, "CREATE", "organization", org["id"], {"name": payload["name"]}, correlation_id, ip_address)
    return org


def update_organization(cur, user, org_id, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    cur.execute(
        "SELECT id, name, org_type, country_id, website, contact_email, is_active "
        "FROM organizations WHERE id = %(id)s AND deleted_at IS NULL",
        {"id": org_id},
    )
    existing = cur.fetchone()
    if existing is None:
        raise NotFoundError("Organisation introuvable.")

    org_type = payload.get("org_type", existing["org_type"])
    _validate_org_type(org_type)
    country_id = payload.get("country_id", existing["country_id"])
    _validate_country(cur, country_id)

    merged = {
        "name": payload.get("name", existing["name"]),
        "org_type": org_type,
        "country_id": country_id,
        "website": payload.get("website", existing["website"]),
        "contact_email": payload.get("contact_email", existing["contact_email"]),
        "is_active": payload.get("is_active", existing["is_active"]),
        "id": org_id,
    }
    cur.execute(
        """
        UPDATE organizations SET name=%(name)s, org_type=%(org_type)s, country_id=%(country_id)s,
            website=%(website)s, contact_email=%(contact_email)s, is_active=%(is_active)s
        WHERE id = %(id)s
        RETURNING id, name, org_type, country_id, website, contact_email, is_active
        """,
        merged,
    )
    updated = cur.fetchone()
    _write_audit(cur, user, "UPDATE", "organization", org_id, {"fields": list(payload.keys())}, correlation_id, ip_address)
    return updated


# --- Partenariats de diffusion ----------------------------------------------

def list_diffusion_partnerships(cur, user):
    cur.execute(
        "SELECT id, organization_id, convention_reference, signed_at, valid_from, valid_until, "
        "status, document_s3_key, notes FROM diffusion_partnerships ORDER BY signed_at DESC"
    )
    return cur.fetchall()


def _validate_partnership_status(status):
    if status not in ALLOWED_PARTNERSHIP_STATUSES:
        raise ValidationError(
            "status invalide.", fields={"status": f"doit être l'un de {sorted(ALLOWED_PARTNERSHIP_STATUSES)}"}
        )


def _validate_organization(cur, organization_id):
    cur.execute("SELECT 1 FROM organizations WHERE id = %(id)s AND deleted_at IS NULL", {"id": organization_id})
    if cur.fetchone() is None:
        raise ValidationError("organization_id introuvable.", fields={"organization_id": "n'existe pas"})


def create_diffusion_partnership(cur, user, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    _require_fields(payload, ("organization_id", "convention_reference", "signed_at", "valid_from"))
    status = payload.get("status", "ACTIVE")
    _validate_partnership_status(status)
    _validate_organization(cur, payload["organization_id"])

    cur.execute(
        """
        INSERT INTO diffusion_partnerships
            (organization_id, convention_reference, signed_at, valid_from, valid_until, status, document_s3_key, notes)
        VALUES
            (%(organization_id)s, %(convention_reference)s, %(signed_at)s, %(valid_from)s, %(valid_until)s,
             %(status)s, %(document_s3_key)s, %(notes)s)
        RETURNING id, organization_id, convention_reference, signed_at, valid_from, valid_until, status, document_s3_key, notes
        """,
        {
            "organization_id": payload["organization_id"],
            "convention_reference": payload["convention_reference"],
            "signed_at": payload["signed_at"],
            "valid_from": payload["valid_from"],
            "valid_until": payload.get("valid_until"),
            "status": status,
            "document_s3_key": payload.get("document_s3_key"),
            "notes": payload.get("notes"),
        },
    )
    partnership = cur.fetchone()
    _write_audit(
        cur, user, "CREATE", "diffusion_partnership", partnership["id"],
        {"convention_reference": payload["convention_reference"]}, correlation_id, ip_address,
    )
    return partnership


def update_diffusion_partnership(cur, user, partnership_id, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    cur.execute(
        "SELECT id, organization_id, convention_reference, signed_at, valid_from, valid_until, "
        "status, document_s3_key, notes FROM diffusion_partnerships WHERE id = %(id)s",
        {"id": partnership_id},
    )
    existing = cur.fetchone()
    if existing is None:
        raise NotFoundError("Partenariat introuvable.")

    status = payload.get("status", existing["status"])
    _validate_partnership_status(status)
    organization_id = payload.get("organization_id", existing["organization_id"])
    _validate_organization(cur, organization_id)

    merged = {
        "organization_id": organization_id,
        "convention_reference": payload.get("convention_reference", existing["convention_reference"]),
        "signed_at": payload.get("signed_at", existing["signed_at"]),
        "valid_from": payload.get("valid_from", existing["valid_from"]),
        "valid_until": payload.get("valid_until", existing["valid_until"]),
        "status": status,
        "document_s3_key": payload.get("document_s3_key", existing["document_s3_key"]),
        "notes": payload.get("notes", existing["notes"]),
        "id": partnership_id,
    }
    cur.execute(
        """
        UPDATE diffusion_partnerships SET organization_id=%(organization_id)s,
            convention_reference=%(convention_reference)s, signed_at=%(signed_at)s, valid_from=%(valid_from)s,
            valid_until=%(valid_until)s, status=%(status)s, document_s3_key=%(document_s3_key)s, notes=%(notes)s
        WHERE id = %(id)s
        RETURNING id, organization_id, convention_reference, signed_at, valid_from, valid_until, status, document_s3_key, notes
        """,
        merged,
    )
    updated = cur.fetchone()
    _write_audit(
        cur, user, "UPDATE", "diffusion_partnership", partnership_id,
        {"fields": list(payload.keys())}, correlation_id, ip_address,
    )
    return updated
