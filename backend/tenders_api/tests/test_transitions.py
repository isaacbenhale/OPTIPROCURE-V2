"""Niveau 1 — logique pure, aucune I/O (voir plan module 3, §8)."""
import pytest

from errors import ForbiddenError, ValidationError
from transitions import can_transition


def test_valid_agent_submit_passes():
    can_transition(role="AGENT", from_status="DRAFT", to_status="PENDING_REVIEW", is_owner=True, mfa_enabled=False, reason=None)


def test_transition_not_in_matrix_is_forbidden():
    with pytest.raises(ForbiddenError):
        can_transition(role="ADMIN", from_status="DRAFT", to_status="APPROVED", is_owner=False, mfa_enabled=True, reason=None)


@pytest.mark.parametrize("to_status", ["QUEUED_FOR_PUBLICATION", "PUBLISHED", "EXPIRED"])
def test_coordinator_only_statuses_always_forbidden_even_for_admin(to_status):
    # Même en forgeant un statut de départ plausible et un ADMIN avec MFA,
    # ces statuts ne doivent jamais être atteignables via cette Lambda.
    with pytest.raises(ForbiddenError):
        can_transition(role="ADMIN", from_status="APPROVED", to_status=to_status, is_owner=False, mfa_enabled=True, reason=None)


def test_wrong_role_is_forbidden():
    with pytest.raises(ForbiddenError):
        can_transition(role="AGENT", from_status="PENDING_REVIEW", to_status="APPROVED", is_owner=False, mfa_enabled=False, reason=None)


def test_reviewer_cannot_reject():
    with pytest.raises(ForbiddenError):
        can_transition(role="REVIEWER", from_status="PENDING_REVIEW", to_status="REJECTED", is_owner=False, mfa_enabled=False, reason="motif")


def test_owner_only_violation_is_forbidden():
    with pytest.raises(ForbiddenError):
        can_transition(role="AGENT", from_status="DRAFT", to_status="PENDING_REVIEW", is_owner=False, mfa_enabled=False, reason=None)


def test_admin_action_without_mfa_is_forbidden_even_with_correct_role():
    with pytest.raises(ForbiddenError):
        can_transition(role="ADMIN", from_status="PENDING_REVIEW", to_status="APPROVED", is_owner=False, mfa_enabled=False, reason=None)


def test_admin_action_with_mfa_passes():
    can_transition(role="ADMIN", from_status="PENDING_REVIEW", to_status="APPROVED", is_owner=False, mfa_enabled=True, reason=None)


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_missing_or_blank_reason_is_validation_error(reason):
    with pytest.raises(ValidationError):
        can_transition(role="REVIEWER", from_status="PENDING_REVIEW", to_status="REVISION_REQUESTED", is_owner=False, mfa_enabled=False, reason=reason)


def test_reason_present_passes():
    can_transition(role="REVIEWER", from_status="PENDING_REVIEW", to_status="REVISION_REQUESTED", is_owner=False, mfa_enabled=False, reason="Pièces manquantes")


def test_admin_can_archive_expired_with_mfa():
    can_transition(role="ADMIN", from_status="EXPIRED", to_status="ARCHIVED", is_owner=False, mfa_enabled=True, reason=None)


def test_cannot_archive_non_expired():
    with pytest.raises(ForbiddenError):
        can_transition(role="ADMIN", from_status="DRAFT", to_status="ARCHIVED", is_owner=False, mfa_enabled=True, reason=None)
