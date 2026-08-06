"""Niveau 1 — logique pure (voir plan module 3, §5 et §8)."""
from decimal import Decimal

from content_hash import compute_content_hash

BASE_TENDER = {
    "reference_number": "REF-001",
    "title": "Construction d'un pont",
    "description": "Travaux de génie civil",
    "sector": "PUBLIC",
    "organization_id": "org-1",
    "country_id": "country-1",
    "category_ids": ["cat-2", "cat-1"],
    "procurement_type": "TRAVAUX",
    "procedure_type": "OUVERT",
    "location_region": "Maritime",
    "location_city": "Lomé",
    "estimated_budget": Decimal("1500000.00"),
    "currency": "XOF",
    "submission_deadline": "2026-09-01T00:00:00+00:00",
    "eligibility_criteria": "Agrément BTP catégorie 3",
    "required_documents": "Attestation fiscale, RCCM",
    "contact_name": "Jean Dupont",
    "contact_role": "Chef de projet",
    "contact_email": "jean@example.com",
    "contact_phone": "+228 90 00 00 00",
    "source_name": "ARCOP",
    "source_url": "https://arcop.tg/ao/001",
    "document_ids": ["doc-2", "doc-1"],
    # champs exclus du hash — ne doivent avoir aucun effet
    "id": "should-not-matter",
    "status": "DRAFT",
    "created_by": "should-not-matter",
    "created_at": "should-not-matter",
}


def test_hash_is_stable_across_calls():
    assert compute_content_hash(BASE_TENDER) == compute_content_hash(dict(BASE_TENDER))


def test_hash_ignores_category_ids_order():
    a = dict(BASE_TENDER, category_ids=["cat-1", "cat-2"])
    b = dict(BASE_TENDER, category_ids=["cat-2", "cat-1"])
    assert compute_content_hash(a) == compute_content_hash(b)


def test_hash_ignores_excluded_fields():
    a = dict(BASE_TENDER, status="DRAFT", id="aaa", created_by="user-1")
    b = dict(BASE_TENDER, status="APPROVED", id="bbb", created_by="user-2")
    assert compute_content_hash(a) == compute_content_hash(b)


def test_hash_changes_when_title_changes():
    a = compute_content_hash(BASE_TENDER)
    b = compute_content_hash(dict(BASE_TENDER, title="Autre titre"))
    assert a != b


def test_hash_changes_when_budget_changes():
    a = compute_content_hash(BASE_TENDER)
    b = compute_content_hash(dict(BASE_TENDER, estimated_budget=Decimal("1500000.01")))
    assert a != b


def test_hash_ignores_document_ids_order():
    a = dict(BASE_TENDER, document_ids=["doc-1", "doc-2"])
    b = dict(BASE_TENDER, document_ids=["doc-2", "doc-1"])
    assert compute_content_hash(a) == compute_content_hash(b)


def test_hash_changes_when_document_added():
    a = compute_content_hash(BASE_TENDER)
    b = compute_content_hash(dict(BASE_TENDER, document_ids=["doc-1", "doc-2", "doc-3"]))
    assert a != b
