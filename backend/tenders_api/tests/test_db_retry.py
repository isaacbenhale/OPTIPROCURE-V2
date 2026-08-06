"""
Niveau 2 — connexion/curseur mockés (aucune vraie base). Vérifie le retry
OCC (SQLSTATE 40001, comportement normal sous DSQL, jamais fatal au premier
échec) et la conversion en ConflictError propre après épuisement des
tentatives (voir plan module 3, §8).
"""
import pytest

import db
from errors import ConflictError


class _FakeOCCError(Exception):
    pgcode = "40001"


class _FakeOtherDbError(Exception):
    pgcode = "42601"  # erreur de syntaxe, non-OCC — ne doit jamais être retentée


class _FakeUniqueViolationError(Exception):
    pgcode = "23505"  # ex. idx_tenders_org_reference


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
    assert conn.rollback_count == 2  # un rollback par tentative échouée


def test_gives_up_after_max_retries_raises_conflict_error_not_silent():
    conn = _FakeConnection()

    def fn(cur):
        raise _FakeOCCError("conflit persistant")

    with pytest.raises(ConflictError):
        db.run_in_transaction(conn, fn, max_retries=2, base_backoff=0)

    assert conn.rollback_count == 3  # tentative initiale + 2 retries
    assert conn.commit_count == 0


def test_non_occ_error_is_never_retried():
    conn = _FakeConnection()
    calls = {"count": 0}

    def fn(cur):
        calls["count"] += 1
        raise _FakeOtherDbError("erreur de syntaxe")

    with pytest.raises(_FakeOtherDbError):
        db.run_in_transaction(conn, fn, max_retries=5, base_backoff=0)

    assert calls["count"] == 1  # aucune tentative supplémentaire
    assert conn.rollback_count == 1


def test_unique_violation_is_conflict_not_500_and_never_retried():
    conn = _FakeConnection()
    calls = {"count": 0}

    def fn(cur):
        calls["count"] += 1
        raise _FakeUniqueViolationError("idx_tenders_org_reference dupliqué")

    with pytest.raises(ConflictError):
        db.run_in_transaction(conn, fn, max_retries=5, base_backoff=0)

    assert calls["count"] == 1  # un conflit réel n'est jamais retenté, contrairement à l'OCC
