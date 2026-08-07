"""
Niveau 2 — curseur mocké (module 02, documents joints). Vérifie que les
permissions (propriétaire + statut DRAFT/REVISION_REQUESTED pour toute
écriture) et les validations bloquent avant toute écriture, sur le modèle
de test_tenders_permissions.py.
"""
import pytest
from conftest import FakeCursor

import documents
from errors import ForbiddenError, NotFoundError, ValidationError

AGENT = {"id": "u1", "role": "AGENT", "mfa_enabled": False}
REVIEWER = {"id": "rev-1", "role": "REVIEWER", "mfa_enabled": False}
ADMIN = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": False}

OWNED_DRAFT_TENDER = {"id": "t1", "deleted_at": None, "created_by": "u1", "status": "DRAFT"}
NOT_OWNED_TENDER = {"id": "t1", "deleted_at": None, "created_by": "someone-else", "status": "DRAFT"}
OWNED_APPROVED_TENDER = {"id": "t1", "deleted_at": None, "created_by": "u1", "status": "APPROVED"}

VALID_UPLOAD_PAYLOAD = {"file_name": "dao.pdf", "content_type": "application/pdf", "size_bytes": 1024}


class _FakeS3:
    def generate_presigned_url(self, operation, Params=None, ExpiresIn=None):
        return f"https://example.com/fake/{operation}"


@pytest.fixture(autouse=True)
def _fake_s3(monkeypatch):
    monkeypatch.setattr(documents, "_s3_client", lambda: _FakeS3())


# --- create_upload ----------------------------------------------------

def test_create_upload_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        documents.create_upload(cur, REVIEWER, "t1", VALID_UPLOAD_PAYLOAD, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_upload_not_owner_is_forbidden():
    cur = FakeCursor(fetchone_results=[NOT_OWNED_TENDER])
    with pytest.raises(ForbiddenError):
        documents.create_upload(cur, AGENT, "t1", VALID_UPLOAD_PAYLOAD, "corr-1", "1.2.3.4")


def test_create_upload_wrong_status_is_forbidden():
    cur = FakeCursor(fetchone_results=[OWNED_APPROVED_TENDER])
    with pytest.raises(ForbiddenError):
        documents.create_upload(cur, AGENT, "t1", VALID_UPLOAD_PAYLOAD, "corr-1", "1.2.3.4")


def test_admin_create_upload_bypasses_ownership_but_still_checks_status():
    # ADMIN sur un AO qu'il ne possède pas : pas de blocage sur la
    # propriété (contrairement à AGENT), mais le contrôle de statut suivant
    # s'applique toujours.
    cur = FakeCursor(fetchone_results=[dict(NOT_OWNED_TENDER, status="APPROVED")])
    with pytest.raises(ForbiddenError, match="statut"):
        documents.create_upload(cur, ADMIN, "t1", VALID_UPLOAD_PAYLOAD, "corr-1", "1.2.3.4")


def test_create_upload_missing_fields():
    cur = FakeCursor(fetchone_results=[OWNED_DRAFT_TENDER])
    with pytest.raises(ValidationError):
        documents.create_upload(cur, AGENT, "t1", {}, "corr-1", "1.2.3.4")
    assert not cur.executed_sql_contains("INSERT INTO tender_documents")


def test_create_upload_invalid_content_type():
    cur = FakeCursor(fetchone_results=[OWNED_DRAFT_TENDER])
    payload = dict(VALID_UPLOAD_PAYLOAD, content_type="application/x-msdownload")
    with pytest.raises(ValidationError):
        documents.create_upload(cur, AGENT, "t1", payload, "corr-1", "1.2.3.4")
    assert not cur.executed_sql_contains("INSERT INTO tender_documents")


@pytest.mark.parametrize("size_bytes", [0, -1, 999_999_999, "1024"])
def test_create_upload_invalid_size(size_bytes):
    cur = FakeCursor(fetchone_results=[OWNED_DRAFT_TENDER])
    payload = dict(VALID_UPLOAD_PAYLOAD, size_bytes=size_bytes)
    with pytest.raises(ValidationError):
        documents.create_upload(cur, AGENT, "t1", payload, "corr-1", "1.2.3.4")
    assert not cur.executed_sql_contains("INSERT INTO tender_documents")


def test_create_upload_happy_path():
    document_row = {
        "id": "doc-1", "tender_id": "t1", "file_name": "dao.pdf", "s3_key": "tenders/t1/doc-1/dao.pdf",
        "content_type": "application/pdf", "size_bytes": 1024, "uploaded_by": "u1", "uploaded_at": "2026-08-06",
    }
    cur = FakeCursor(
        fetchone_results=[
            OWNED_DRAFT_TENDER,  # get_tender_row (ownership check)
            document_row,        # INSERT ... RETURNING
            OWNED_DRAFT_TENDER,  # recompute_content_hash: SELECT * FROM tenders
        ],
        fetchall_results=[[], []],  # category_ids, document_ids
    )
    result = documents.create_upload(cur, AGENT, "t1", VALID_UPLOAD_PAYLOAD, "corr-1", "1.2.3.4")

    assert result["upload_url"] == "https://example.com/fake/put_object"
    assert cur.executed_sql_contains("INSERT INTO tender_documents")
    assert cur.executed_sql_contains("UPDATE tenders SET content_hash")
    assert cur.executed_sql_contains("INSERT INTO audit_log")


# --- list_documents / get_document_download_url ----------------------

def test_list_documents_not_visible_raises_not_found():
    cur = FakeCursor(fetchone_results=[None])  # tenders.get_tender -> visibilité échoue
    with pytest.raises(NotFoundError):
        documents.list_documents(cur, AGENT, "t1")


# --- delete_document ----------------------------------------------------

def test_delete_document_wrong_role_is_forbidden_before_any_write():
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        documents.delete_document(cur, REVIEWER, "t1", "doc-1", "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_delete_document_not_owner_is_forbidden():
    cur = FakeCursor(fetchone_results=[NOT_OWNED_TENDER])
    with pytest.raises(ForbiddenError):
        documents.delete_document(cur, AGENT, "t1", "doc-1", "corr-1", "1.2.3.4")


def test_delete_document_wrong_status_is_forbidden():
    cur = FakeCursor(fetchone_results=[OWNED_APPROVED_TENDER])
    with pytest.raises(ForbiddenError):
        documents.delete_document(cur, AGENT, "t1", "doc-1", "corr-1", "1.2.3.4")


def test_delete_document_not_found():
    cur = FakeCursor(fetchone_results=[OWNED_DRAFT_TENDER, None])
    with pytest.raises(NotFoundError):
        documents.delete_document(cur, AGENT, "t1", "doc-missing", "corr-1", "1.2.3.4")
    assert not cur.executed_sql_contains("UPDATE tender_documents")
