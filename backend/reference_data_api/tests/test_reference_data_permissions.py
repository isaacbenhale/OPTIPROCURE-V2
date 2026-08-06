"""
Niveau 2 — curseur mocké. Vérifie que les permissions (ADMIN + MFA pour
toute écriture) et les validations bloquent avant toute écriture, sur le
modèle de backend/tenders_api/tests/test_tenders_permissions.py.
"""
import pytest
from conftest import FakeCursor

import reference_data
from errors import ForbiddenError, NotFoundError, ValidationError

ADMIN = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": True}
ADMIN_NO_MFA = {"id": "admin-2", "role": "ADMIN", "mfa_enabled": False}
AGENT = {"id": "agent-1", "role": "AGENT", "mfa_enabled": False}


# --- Pays -------------------------------------------------------------

def test_create_country_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        reference_data.create_country(cur, AGENT, {"iso_code": "TG", "name": "Togo"}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_country_admin_without_mfa_is_forbidden():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        reference_data.create_country(cur, ADMIN_NO_MFA, {"iso_code": "TG", "name": "Togo"}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_country_missing_fields():
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        reference_data.create_country(cur, ADMIN, {}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_country_happy_path():
    cur = FakeCursor(fetchone_results=[{"id": "c1", "iso_code": "TG", "name": "Togo"}])
    country = reference_data.create_country(cur, ADMIN, {"iso_code": "TG", "name": "Togo"}, "corr-1", "1.2.3.4")
    assert country["iso_code"] == "TG"
    assert cur.executed_sql_contains("INSERT INTO countries")
    assert cur.executed_sql_contains("INSERT INTO audit_log")


# --- Catégories ---------------------------------------------------------

def test_create_category_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        reference_data.create_category(cur, AGENT, {"name": "BTP", "slug": "btp"}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_category_parent_not_found():
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(ValidationError):
        reference_data.create_category(
            cur, ADMIN, {"name": "Sous-BTP", "slug": "sous-btp", "parent_id": "missing"}, "corr-1", "1.2.3.4"
        )
    assert not cur.executed_sql_contains("INSERT INTO categories")


def test_update_category_not_found():
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(NotFoundError):
        reference_data.update_category(cur, ADMIN, "missing-id", {"name": "x"}, "corr-1", "1.2.3.4")


def test_update_category_self_parent_is_forbidden():
    cur = FakeCursor(fetchone_results=[
        {"id": "cat-1", "parent_id": None, "name": "BTP", "slug": "btp", "is_active": True},
    ])
    with pytest.raises(ValidationError):
        reference_data.update_category(cur, ADMIN, "cat-1", {"parent_id": "cat-1"}, "corr-1", "1.2.3.4")


# --- Organisations --------------------------------------------------------

def test_create_organization_invalid_org_type():
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        reference_data.create_organization(cur, ADMIN, {"name": "ARCOP", "org_type": "BOGUS"}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_organization_country_not_found():
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(ValidationError):
        reference_data.create_organization(
            cur, ADMIN, {"name": "ARCOP", "org_type": "PUBLIC_BODY", "country_id": "missing"}, "corr-1", "1.2.3.4"
        )
    assert not cur.executed_sql_contains("INSERT INTO organizations")


def test_update_organization_not_found():
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(NotFoundError):
        reference_data.update_organization(cur, ADMIN, "missing-id", {"name": "x"}, "corr-1", "1.2.3.4")


def test_create_organization_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        reference_data.create_organization(cur, AGENT, {"name": "ARCOP", "org_type": "PUBLIC_BODY"}, "corr-1", "1.2.3.4")
    assert cur.executed == []


# --- Partenariats de diffusion ---------------------------------------------

def test_create_diffusion_partnership_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        reference_data.create_diffusion_partnership(
            cur, AGENT,
            {"organization_id": "org-1", "convention_reference": "CONV-1", "signed_at": "2026-01-01", "valid_from": "2026-01-01"},
            "corr-1", "1.2.3.4",
        )
    assert cur.executed == []


def test_create_diffusion_partnership_organization_not_found():
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(ValidationError):
        reference_data.create_diffusion_partnership(
            cur, ADMIN,
            {"organization_id": "missing", "convention_reference": "CONV-1", "signed_at": "2026-01-01", "valid_from": "2026-01-01"},
            "corr-1", "1.2.3.4",
        )
    assert not cur.executed_sql_contains("INSERT INTO diffusion_partnerships")


def test_create_diffusion_partnership_invalid_status():
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        reference_data.create_diffusion_partnership(
            cur, ADMIN,
            {
                "organization_id": "org-1", "convention_reference": "CONV-1", "signed_at": "2026-01-01",
                "valid_from": "2026-01-01", "status": "BOGUS",
            },
            "corr-1", "1.2.3.4",
        )
    assert cur.executed == []
