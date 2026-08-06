"""
Non-régression minimale : db.py est une copie de backend/tenders_api/db.py
(déjà testé en profondeur là-bas, voir test_db_retry.py) — on vérifie juste
ici que le retry OCC et le mapping de conflit d'unicité fonctionnent encore
après duplication, pas besoin de dupliquer l'exhaustivité des cas.
"""
import pytest

import db
from errors import ConflictError


class _FakeOCCError(Exception):
    pgcode = "40001"


class _FakeUniqueViolationError(Exception):
    pgcode = "23505"


class _FakeCursorCM:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeConnection:
    def __init__(self):
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self):
        return _FakeCursorCM()

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    monkeypatch.setattr(db.time, "sleep", lambda seconds: None)


def test_retries_on_occ_then_succeeds():
    conn = _FakeConnection()
    calls = {"count": 0}

    def fn(cur):
        calls["count"] += 1
        if calls["count"] < 3:
            raise _FakeOCCError("conflit de concurrence")
        return "ok"

    result = db.run_in_transaction(conn, fn, max_retries=5, base_backoff=0)
    assert result == "ok"
    assert calls["count"] == 3
    assert conn.commit_count == 1


def test_unique_violation_is_generic_conflict_message():
    conn = _FakeConnection()

    def fn(cur):
        raise _FakeUniqueViolationError("duplicate")

    with pytest.raises(ConflictError, match="Une ligne avec cette valeur unique existe déjà."):
        db.run_in_transaction(conn, fn, max_retries=5, base_backoff=0)
