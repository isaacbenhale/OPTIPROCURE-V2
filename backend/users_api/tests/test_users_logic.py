"""Niveau 1 — fonctions pures (précédence de rôle, validation de groupes)."""
import pytest

import users
from errors import ValidationError


def test_effective_role_single_group():
    assert users.effective_role({"AGENT"}) == "AGENT"


def test_effective_role_precedence_admin_wins():
    assert users.effective_role({"AGENT", "REVIEWER", "ADMIN"}) == "ADMIN"


def test_effective_role_precedence_reviewer_over_agent():
    assert users.effective_role({"AGENT", "REVIEWER"}) == "REVIEWER"


def test_effective_role_empty_set_returns_none():
    assert users.effective_role(set()) is None


def test_validate_groups_accepts_valid_subset():
    assert users._validate_groups(["AGENT", "ADMIN"]) == {"AGENT", "ADMIN"}


def test_validate_groups_rejects_empty():
    with pytest.raises(ValidationError):
        users._validate_groups([])


def test_validate_groups_rejects_unknown_role():
    with pytest.raises(ValidationError):
        users._validate_groups(["AGENT", "SUPERUSER"])


def test_validate_groups_rejects_none():
    with pytest.raises(ValidationError):
        users._validate_groups(None)
