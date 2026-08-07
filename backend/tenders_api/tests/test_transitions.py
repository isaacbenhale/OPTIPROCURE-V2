"""Niveau 1 — logique pure, aucune I/O (voir plan module 3, §8)."""
import pytest

from errors import ForbiddenError, ValidationError
from transitions import can_transition, compute_available_actions


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


def test_admin_bypasses_owner_only_restriction():
    # ADMIN a tous les droits AGENT y compris sur un AO qu'il ne possède pas.
    can_transition(role="ADMIN", from_status="DRAFT", to_status="PENDING_REVIEW", is_owner=False, mfa_enabled=False, reason=None)


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


# --- compute_available_actions (module 03) ------------------------------

def test_owner_agent_sees_update_and_submit_on_draft():
    tender = {"status": "DRAFT", "created_by": "u1"}
    user = {"id": "u1", "role": "AGENT", "mfa_enabled": False}
    assert set(compute_available_actions(tender, user)) == {"update", "submit"}


def test_non_owner_agent_sees_nothing_on_draft():
    tender = {"status": "DRAFT", "created_by": "someone-else"}
    user = {"id": "u1", "role": "AGENT", "mfa_enabled": False}
    assert compute_available_actions(tender, user) == []


def test_reviewer_sees_return_and_endorse_on_pending_review():
    tender = {"status": "PENDING_REVIEW", "created_by": "u1"}
    user = {"id": "rev-1", "role": "REVIEWER", "mfa_enabled": False}
    assert set(compute_available_actions(tender, user)) == {"return", "endorse"}


def test_admin_without_mfa_sees_reviewer_actions_but_not_approve_or_reject():
    # ADMIN hérite des droits REVIEWER (non soumis au MFA) mais pas de ses
    # propres droits approve/reject tant que le MFA n'est pas activé.
    tender = {"status": "PENDING_REVIEW", "created_by": "u1"}
    user = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": False}
    assert set(compute_available_actions(tender, user)) == {"return", "endorse"}


def test_admin_with_mfa_sees_all_pending_review_actions():
    # ADMIN a tous les droits REVIEWER (return/endorse) + ses propres droits
    # (approve/reject, avec MFA) — jamais l'inverse.
    tender = {"status": "PENDING_REVIEW", "created_by": "u1"}
    user = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": True}
    assert set(compute_available_actions(tender, user)) == {"approve", "reject", "return", "endorse"}


def test_admin_with_mfa_sees_only_archive_on_expired():
    tender = {"status": "EXPIRED", "created_by": "u1"}
    user = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": True}
    assert compute_available_actions(tender, user) == ["archive"]


def test_admin_sees_agent_actions_even_as_non_owner_on_draft():
    # ADMIN hérite des droits AGENT (update/submit) sans restriction de
    # propriété — supervision globale, contrairement à AGENT lui-même
    # (voir test_non_owner_agent_sees_nothing_on_draft).
    tender = {"status": "DRAFT", "created_by": "someone-else"}
    user = {"id": "admin-1", "role": "ADMIN", "mfa_enabled": False}
    assert set(compute_available_actions(tender, user)) == {"submit", "update", "delete"}


def test_no_action_ever_targets_coordinator_only_statuses():
    # QUEUED_FOR_PUBLICATION/PUBLISHED/EXPIRED ne doivent jamais apparaître
    # comme cible d'une action, même en théorie — vérifie STATUS_ACTIONS
    # directement plutôt qu'un cas d'usage précis.
    from transitions import COORDINATOR_ONLY_STATUSES, STATUS_ACTIONS
    assert set(STATUS_ACTIONS.values()).isdisjoint(COORDINATOR_ONLY_STATUSES)
