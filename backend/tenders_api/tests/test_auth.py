"""
Niveau 1/2 — résolution de rôle (pure) et upsert JIT (curseur mocké, voir
plan module 3 §8 : reflet immédiat d'un changement de groupe Cognito, rejet
propre d'un token sans cognito:groups, jamais un crash).
"""
from datetime import datetime, timedelta, timezone

import pytest
from conftest import FakeCursor

import auth
from errors import ForbiddenError, UnauthorizedError


def test_resolve_role_from_groups_picks_admin_first_by_precedence():
    assert auth.resolve_role_from_groups({"cognito:groups": "AGENT,ADMIN,REVIEWER"}) == "ADMIN"


def test_resolve_role_from_groups_single_group():
    assert auth.resolve_role_from_groups({"cognito:groups": "AGENT"}) == "AGENT"


def test_resolve_role_from_groups_absent_returns_none():
    assert auth.resolve_role_from_groups({}) is None


def test_resolve_role_from_groups_empty_string_returns_none():
    assert auth.resolve_role_from_groups({"cognito:groups": ""}) is None


def test_upsert_user_without_groups_is_forbidden_not_a_crash():
    cur = FakeCursor()
    claims = {"sub": "sub-123", "email": "a@example.com"}
    cognito_info = {"email": "a@example.com", "name": "A", "mfa_enabled": False}
    with pytest.raises(ForbiddenError):
        auth.upsert_user(cur, claims, cognito_info)


def test_upsert_user_without_sub_is_unauthorized():
    cur = FakeCursor()
    claims = {"cognito:groups": "AGENT"}
    cognito_info = {"email": "a@example.com", "name": "A", "mfa_enabled": False}
    with pytest.raises(UnauthorizedError):
        auth.upsert_user(cur, claims, cognito_info)


def test_upsert_user_reflects_role_change_immediately():
    # Le token porte désormais ADMIN alors que l'utilisateur était AGENT en
    # base : l'upsert doit refléter le nouveau groupe, pas garder un rôle
    # périmé (pas de cache de rôle).
    cur = FakeCursor(
        fetchone_results=[
            {"last_login_at": None},  # SELECT last_login_at
            {"id": "user-1", "cognito_sub": "sub-123", "email": "a@example.com",
             "full_name": "A", "role": "ADMIN", "is_active": True, "mfa_enabled": True,
             "last_login_at": datetime.now(timezone.utc)},  # RETURNING de l'upsert
        ]
    )
    claims = {"sub": "sub-123", "cognito:groups": "ADMIN"}
    cognito_info = {"email": "a@example.com", "name": "A", "mfa_enabled": True}

    user, is_new_session = auth.upsert_user(cur, claims, cognito_info)

    assert user["role"] == "ADMIN"
    assert is_new_session is True
    insert_call = next(sql for sql, _ in cur.executed if sql.startswith("INSERT INTO users"))
    assert "ON CONFLICT" in insert_call


def test_upsert_user_full_name_falls_back_to_email_when_cognito_name_missing():
    cur = FakeCursor(
        fetchone_results=[
            None,
            {"id": "user-2", "cognito_sub": "sub-456", "email": "b@example.com",
             "full_name": "b@example.com", "role": "AGENT", "is_active": True, "mfa_enabled": False,
             "last_login_at": datetime.now(timezone.utc)},
        ]
    )
    claims = {"sub": "sub-456", "cognito:groups": "AGENT"}
    cognito_info = {"email": "b@example.com", "name": None, "mfa_enabled": False}

    user, _ = auth.upsert_user(cur, claims, cognito_info)
    assert user["full_name"] == "b@example.com"


def test_maybe_log_login_skips_when_not_new_session():
    cur = FakeCursor()
    user = {"id": "user-1", "role": "AGENT"}
    auth.maybe_log_login(cur, user, is_new_session=False, correlation_id="corr-1", ip_address="1.2.3.4")
    assert cur.executed == []


def test_maybe_log_login_writes_audit_when_new_session():
    cur = FakeCursor()
    user = {"id": "user-1", "role": "AGENT"}
    auth.maybe_log_login(cur, user, is_new_session=True, correlation_id="corr-1", ip_address="1.2.3.4")
    assert cur.executed_sql_contains("INSERT INTO audit_log")


def test_require_active_raises_when_inactive():
    with pytest.raises(ForbiddenError):
        auth.require_active({"is_active": False})


def test_require_role_raises_when_not_allowed():
    with pytest.raises(ForbiddenError):
        auth.require_role({"role": "AGENT"}, {"ADMIN"})


def test_require_mfa_raises_when_disabled():
    with pytest.raises(ForbiddenError):
        auth.require_mfa({"mfa_enabled": False})


def test_require_mfa_passes_when_enabled():
    auth.require_mfa({"mfa_enabled": True})
