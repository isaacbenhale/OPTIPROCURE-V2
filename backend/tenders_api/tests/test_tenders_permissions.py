"""
Niveau 2 — curseur mocké. Vérifie que les validations et contrôles de
permission bloquent avant toute écriture (voir plan module 3, §8).
"""
from datetime import datetime, timedelta, timezone

import pytest
from conftest import FakeCursor

import tenders
from errors import ForbiddenError, NotFoundError, ValidationError


def test_create_tender_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    user = {"id": "u1", "role": "REVIEWER"}
    with pytest.raises(ForbiddenError):
        tenders.create_tender(cur, user, {"title": "x"}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_tender_missing_required_fields_before_any_write():
    cur = FakeCursor()
    user = {"id": "u1", "role": "AGENT"}
    with pytest.raises(ValidationError):
        tenders.create_tender(cur, user, {}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_validate_references_missing_organization():
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(ValidationError):
        tenders.validate_references(cur, "org-missing", None, [])


def test_validate_references_missing_country():
    cur = FakeCursor(fetchone_results=[{"exists": 1}, None])
    with pytest.raises(ValidationError):
        tenders.validate_references(cur, "org-1", "country-missing", [])


def test_validate_references_missing_categories():
    cur = FakeCursor(
        fetchone_results=[{"exists": 1}, {"exists": 1}],
        fetchall_results=[[{"id": "cat-1"}]],
    )
    with pytest.raises(ValidationError):
        tenders.validate_references(cur, "org-1", "country-1", ["cat-1", "cat-2"])


def test_validate_references_all_present_does_not_raise():
    cur = FakeCursor(
        fetchone_results=[{"exists": 1}, {"exists": 1}],
        fetchall_results=[[{"id": "cat-1"}, {"id": "cat-2"}]],
    )
    tenders.validate_references(cur, "org-1", "country-1", ["cat-1", "cat-2"])


def test_validate_required_for_submit_missing_fields():
    with pytest.raises(ValidationError):
        tenders.validate_required_for_submit({"title": "x"}, [])


def test_validate_required_for_submit_deadline_in_past():
    tender = {
        "title": "x", "description": "y", "sector": "PUBLIC", "organization_id": "o",
        "country_id": "c", "submission_deadline": datetime.now(timezone.utc) - timedelta(days=1),
        "procurement_type": "TRAVAUX", "procedure_type": "OUVERT", "contact_email": "a@b.com",
    }
    with pytest.raises(ValidationError):
        tenders.validate_required_for_submit(tender, ["cat-1"])


def test_validate_required_for_submit_passes_when_complete():
    tender = {
        "title": "x", "description": "y", "sector": "PUBLIC", "organization_id": "o",
        "country_id": "c", "submission_deadline": datetime.now(timezone.utc) + timedelta(days=10),
        "procurement_type": "TRAVAUX", "procedure_type": "OUVERT", "contact_email": "a@b.com",
    }
    tenders.validate_required_for_submit(tender, ["cat-1"])  # ne doit pas lever


def test_update_tender_not_found():
    cur = FakeCursor(fetchone_results=[None])
    user = {"id": "u1", "role": "AGENT"}
    with pytest.raises(NotFoundError):
        tenders.update_tender(cur, user, "tender-x", {}, "corr-1", "1.2.3.4")


def test_update_tender_not_owner_is_forbidden():
    cur = FakeCursor(fetchone_results=[
        {"id": "t1", "deleted_at": None, "created_by": "someone-else", "status": "DRAFT"},
    ])
    user = {"id": "u1", "role": "AGENT"}
    with pytest.raises(ForbiddenError):
        tenders.update_tender(cur, user, "t1", {}, "corr-1", "1.2.3.4")


def test_admin_can_create_tender_role_check_passes():
    # ADMIN a tous les droits AGENT — le rôle passe, l'échec suivant (champs
    # manquants) prouve qu'on a dépassé le contrôle de rôle, pas qu'on a été
    # bloqué dessus.
    cur = FakeCursor()
    user = {"id": "admin-1", "role": "ADMIN"}
    with pytest.raises(ValidationError):
        tenders.create_tender(cur, user, {}, "corr-1", "1.2.3.4")


def test_admin_update_bypasses_ownership_but_still_checks_status():
    # ADMIN sur un AO qu'il ne possède pas : pas de ForbiddenError de
    # propriété (contrairement à test_update_tender_not_owner_is_forbidden
    # pour AGENT) — mais le contrôle de statut suivant s'applique toujours.
    cur = FakeCursor(fetchone_results=[
        {"id": "t1", "deleted_at": None, "created_by": "someone-else", "status": "APPROVED"},
    ])
    user = {"id": "admin-1", "role": "ADMIN"}
    with pytest.raises(ForbiddenError, match="statut"):
        tenders.update_tender(cur, user, "t1", {}, "corr-1", "1.2.3.4")


def test_update_tender_wrong_status_is_forbidden():
    cur = FakeCursor(fetchone_results=[
        {"id": "t1", "deleted_at": None, "created_by": "u1", "status": "APPROVED"},
    ])
    user = {"id": "u1", "role": "AGENT"}
    with pytest.raises(ForbiddenError):
        tenders.update_tender(cur, user, "t1", {}, "corr-1", "1.2.3.4")


def test_delete_tender_non_draft_is_forbidden():
    cur = FakeCursor(fetchone_results=[
        {"id": "t1", "deleted_at": None, "status": "PENDING_REVIEW"},
    ])
    user = {"id": "u1", "role": "ADMIN"}
    with pytest.raises(ForbiddenError):
        tenders.delete_tender(cur, user, "t1", "corr-1", "1.2.3.4")


def test_delete_tender_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    user = {"id": "u1", "role": "AGENT"}
    with pytest.raises(ForbiddenError):
        tenders.delete_tender(cur, user, "t1", "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_approve_without_mfa_is_forbidden():
    cur = FakeCursor()
    user = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": False}
    with pytest.raises(ForbiddenError):
        tenders.approve(cur, user, "t1", "corr-1", "1.2.3.4")
    assert cur.executed == []
