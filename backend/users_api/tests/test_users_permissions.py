"""
Niveau 2 — curseur mocké + client Cognito mocké. Vérifie que les
permissions (ADMIN + MFA pour toute écriture) et l'auto-protection (un
ADMIN ne peut pas agir sur son propre compte) bloquent avant tout appel
Cognito/DSQL, sur le modèle de
backend/reference_data_api/tests/test_reference_data_permissions.py.
"""
from unittest.mock import MagicMock

import pytest
from conftest import FakeCursor

import users
from errors import ForbiddenError, ValidationError

ADMIN = {"id": "admin-row-1", "cognito_sub": "admin-sub-1", "role": "ADMIN", "mfa_enabled": True}
ADMIN_NO_MFA = {"id": "admin-row-2", "cognito_sub": "admin-sub-2", "role": "ADMIN", "mfa_enabled": False}
AGENT = {"id": "agent-row-1", "cognito_sub": "agent-sub-1", "role": "AGENT", "mfa_enabled": False}


def _fake_cognito_client(monkeypatch, **overrides):
    client = MagicMock()
    client.exceptions.UsernameExistsException = type("UsernameExistsException", (Exception,), {})
    client.admin_create_user.return_value = {
        "User": {"Attributes": [{"Name": "sub", "Value": "new-sub"}, {"Name": "email", "Value": "new@x.test"}]}
    }
    for name, value in overrides.items():
        setattr(client, name, value)
    monkeypatch.setattr(users, "_cognito_client", lambda: client)
    return client


# --- create_account -------------------------------------------------------

def test_create_account_wrong_role_is_forbidden_before_any_call(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        users.create_account(cur, AGENT, {"email": "x@x.test", "groups": ["AGENT"]}, "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_create_user.assert_not_called()


def test_create_account_admin_without_mfa_is_forbidden(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        users.create_account(cur, ADMIN_NO_MFA, {"email": "x@x.test", "groups": ["AGENT"]}, "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_create_user.assert_not_called()


def test_create_account_missing_email():
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        users.create_account(cur, ADMIN, {"groups": ["AGENT"]}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_account_invalid_groups():
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        users.create_account(cur, ADMIN, {"email": "x@x.test", "groups": []}, "corr-1", "1.2.3.4")
    assert cur.executed == []


def test_create_account_happy_path_multi_group(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    result = users.create_account(
        cur, ADMIN, {"email": "new@x.test", "groups": ["AGENT", "REVIEWER"]}, "corr-1", "1.2.3.4"
    )
    assert result["cognito_sub"] == "new-sub"
    assert result["effective_role"] == "REVIEWER"  # REVIEWER > AGENT en précédence
    assert set(result["groups"]) == {"AGENT", "REVIEWER"}
    assert client.admin_add_user_to_group.call_count == 2
    assert cur.executed_sql_contains("INSERT INTO users")
    assert cur.executed_sql_contains("INSERT INTO audit_log")
    # DesiredDeliveryMediums=["EMAIL"] explicite requis — sans lui, Cognito
    # défaut à ["SMS"] et n'envoie jamais l'email d'invitation (bug réel
    # constaté le 2026-08-07, ces comptes n'ayant pas de numéro de téléphone).
    _, create_kwargs = client.admin_create_user.call_args
    assert create_kwargs["DesiredDeliveryMediums"] == ["EMAIL"]


# --- update_groups ----------------------------------------------------------

def test_update_groups_wrong_role_is_forbidden(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        users.update_groups(cur, AGENT, "some-sub", {"groups": ["ADMIN"]}, "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_list_groups_for_user.assert_not_called()


def test_update_groups_rejects_self_action(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        users.update_groups(cur, ADMIN, ADMIN["cognito_sub"], {"groups": ["AGENT"]}, "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_list_groups_for_user.assert_not_called()


def test_update_groups_happy_path_diffs_and_signs_out(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    client.admin_list_groups_for_user.return_value = {"Groups": [{"GroupName": "AGENT"}]}
    cur = FakeCursor(fetchone_results=[{"email": "target@x.test"}])
    result = users.update_groups(cur, ADMIN, "target-sub", {"groups": ["REVIEWER"]}, "corr-1", "1.2.3.4")
    assert result["effective_role"] == "REVIEWER"
    client.admin_add_user_to_group.assert_called_once_with(
        UserPoolId="us-east-1_TESTPOOL", Username="target@x.test", GroupName="REVIEWER"
    )
    client.admin_remove_user_from_group.assert_called_once_with(
        UserPoolId="us-east-1_TESTPOOL", Username="target@x.test", GroupName="AGENT"
    )
    client.admin_user_global_sign_out.assert_called_once()
    assert cur.executed_sql_contains("UPDATE users SET role")


def test_update_groups_no_diff_skips_global_sign_out(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    client.admin_list_groups_for_user.return_value = {"Groups": [{"GroupName": "AGENT"}]}
    cur = FakeCursor(fetchone_results=[{"email": "target@x.test"}])
    users.update_groups(cur, ADMIN, "target-sub", {"groups": ["AGENT"]}, "corr-1", "1.2.3.4")
    client.admin_user_global_sign_out.assert_not_called()


def test_update_groups_target_not_found(monkeypatch):
    _fake_cognito_client(monkeypatch)
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(Exception):  # NotFoundError
        users.update_groups(cur, ADMIN, "missing-sub", {"groups": ["AGENT"]}, "corr-1", "1.2.3.4")


# --- activation / désactivation ---------------------------------------------

def test_deactivate_account_rejects_self_action(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        users.deactivate_account(cur, ADMIN, ADMIN["cognito_sub"], "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_disable_user.assert_not_called()


def test_deactivate_account_happy_path(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor(fetchone_results=[{"email": "target@x.test", "is_active": True}])
    result = users.deactivate_account(cur, ADMIN, "target-sub", "corr-1", "1.2.3.4")
    assert result["is_active"] is False
    client.admin_disable_user.assert_called_once()
    client.admin_user_global_sign_out.assert_called_once()
    assert cur.executed_sql_contains("UPDATE users SET is_active")


def test_deactivate_account_idempotent_when_already_inactive(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor(fetchone_results=[{"email": "target@x.test", "is_active": False}])
    users.deactivate_account(cur, ADMIN, "target-sub", "corr-1", "1.2.3.4")
    client.admin_disable_user.assert_not_called()


def test_activate_account_wrong_role_is_forbidden(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        users.activate_account(cur, AGENT, "target-sub", "corr-1", "1.2.3.4")
    client.admin_enable_user.assert_not_called()


# --- delete_account ---------------------------------------------------------

def test_delete_account_wrong_role_is_forbidden(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        users.delete_account(cur, AGENT, "target-sub", "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_delete_user.assert_not_called()


def test_delete_account_admin_without_mfa_is_forbidden(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ForbiddenError):
        users.delete_account(cur, ADMIN_NO_MFA, "target-sub", "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_delete_user.assert_not_called()


def test_delete_account_rejects_self_action(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor()
    with pytest.raises(ValidationError):
        users.delete_account(cur, ADMIN, ADMIN["cognito_sub"], "corr-1", "1.2.3.4")
    assert cur.executed == []
    client.admin_delete_user.assert_not_called()


def test_delete_account_not_found(monkeypatch):
    _fake_cognito_client(monkeypatch)
    cur = FakeCursor(fetchone_results=[None])
    with pytest.raises(Exception):  # NotFoundError
        users.delete_account(cur, ADMIN, "missing-sub", "corr-1", "1.2.3.4")


def test_delete_account_happy_path(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    cur = FakeCursor(fetchone_results=[{"email": "target@x.test"}])
    result = users.delete_account(cur, ADMIN, "target-sub", "corr-1", "1.2.3.4")
    assert result == {"cognito_sub": "target-sub", "deleted": True}
    client.admin_delete_user.assert_called_once_with(UserPoolId="us-east-1_TESTPOOL", Username="target@x.test")
    assert cur.executed_sql_contains("UPDATE users SET deleted_at")
    assert cur.executed_sql_contains("INSERT INTO audit_log")


def test_delete_account_tolerates_already_deleted_in_cognito(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    client.exceptions.UserNotFoundException = type("UserNotFoundException", (Exception,), {})
    client.admin_delete_user.side_effect = client.exceptions.UserNotFoundException()
    cur = FakeCursor(fetchone_results=[{"email": "target@x.test"}])
    result = users.delete_account(cur, ADMIN, "target-sub", "corr-1", "1.2.3.4")
    assert result == {"cognito_sub": "target-sub", "deleted": True}
    assert cur.executed_sql_contains("UPDATE users SET deleted_at")
