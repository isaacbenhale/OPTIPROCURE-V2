"""
Niveau 2 — fusion des groupes Cognito (ListUsersInGroup, filtrage explicite
par groupe — voir tasks/13-gestion-comptes-internes.md, "Décisions actées"
§3) avec les colonnes DSQL (is_active/mfa_enabled/last_login_at).
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from conftest import FakeCursor

import users

ADMIN = {"id": "admin-row-1", "cognito_sub": "admin-sub-1", "role": "ADMIN", "mfa_enabled": True}


def _fake_cognito_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(users, "_cognito_client", lambda: client)
    return client


def _cognito_user(sub, email):
    return {
        "Username": email,
        "Enabled": True,
        "UserStatus": "CONFIRMED",
        "Attributes": [{"Name": "sub", "Value": sub}, {"Name": "email", "Value": email}],
    }


def test_list_accounts_merges_multi_group_membership_and_dsql_row(monkeypatch):
    client = _fake_cognito_client(monkeypatch)

    pages_by_group = {
        "AGENT": [{"Users": [_cognito_user("sub-a", "a@x.test")]}],
        "REVIEWER": [{"Users": []}],
        "ADMIN": [{"Users": [_cognito_user("sub-a", "a@x.test")]}],
    }
    client.get_paginator.return_value.paginate.side_effect = lambda UserPoolId, GroupName: pages_by_group[GroupName]

    cur = FakeCursor(
        fetchall_results=[
            [
                {
                    "cognito_sub": "sub-a",
                    "full_name": "A A",
                    "is_active": True,
                    "mfa_enabled": True,
                    "last_login_at": datetime.now(timezone.utc),
                }
            ]
        ]
    )

    result = users.list_accounts(cur, ADMIN)

    assert len(result) == 1
    entry = result[0]
    assert entry["cognito_sub"] == "sub-a"
    assert set(entry["groups"]) == {"AGENT", "ADMIN"}
    assert entry["effective_role"] == "ADMIN"  # précédence : ADMIN > AGENT
    assert entry["full_name"] == "A A"
    assert entry["has_logged_in"] is True


def test_list_accounts_dsql_row_exists_but_never_logged_in(monkeypatch):
    # create_account insère la ligne `users` proactivement (voir users.py) —
    # une ligne peut donc exister sans qu'aucun login n'ait jamais eu lieu.
    # has_logged_in doit refléter last_login_at, pas la simple existence de
    # la ligne (bug réel constaté le 2026-08-07 en vérification post-déploiement).
    client = _fake_cognito_client(monkeypatch)
    client.get_paginator.return_value.paginate.side_effect = lambda UserPoolId, GroupName: {
        "AGENT": [{"Users": [_cognito_user("sub-c", "c@x.test")]}],
        "REVIEWER": [{"Users": []}],
        "ADMIN": [{"Users": []}],
    }[GroupName]

    cur = FakeCursor(
        fetchall_results=[
            [{"cognito_sub": "sub-c", "full_name": "c@x.test", "is_active": True, "mfa_enabled": False, "last_login_at": None}]
        ]
    )

    result = users.list_accounts(cur, ADMIN)
    assert result[0]["has_logged_in"] is False


def test_list_accounts_account_never_logged_in_has_defaults(monkeypatch):
    client = _fake_cognito_client(monkeypatch)

    pages_by_group = {
        "AGENT": [{"Users": [_cognito_user("sub-b", "b@x.test")]}],
        "REVIEWER": [{"Users": []}],
        "ADMIN": [{"Users": []}],
    }
    client.get_paginator.return_value.paginate.side_effect = lambda UserPoolId, GroupName: pages_by_group[GroupName]

    cur = FakeCursor(fetchall_results=[[]])  # aucune ligne DSQL : jamais connecté

    result = users.list_accounts(cur, ADMIN)

    assert len(result) == 1
    entry = result[0]
    assert entry["has_logged_in"] is False
    assert entry["is_active"] is True  # comportement par défaut avant premier login
    assert entry["mfa_enabled"] is False
    assert entry["effective_role"] == "AGENT"


def test_list_accounts_empty_pool_returns_empty_list(monkeypatch):
    client = _fake_cognito_client(monkeypatch)
    client.get_paginator.return_value.paginate.return_value = [{"Users": []}]

    cur = FakeCursor()
    result = users.list_accounts(cur, ADMIN)

    assert result == []
    assert cur.executed == []  # pas de SELECT inutile si aucun compte
