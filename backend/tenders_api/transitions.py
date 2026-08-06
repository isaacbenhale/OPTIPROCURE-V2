"""
Matrice pure des transitions de statut autorisées pour un AO (module 3).

Volontairement séparée de tenders.py : aucune I/O ici, testable sans mock.
QUEUED_FOR_PUBLICATION, PUBLISHED et EXPIRED n'apparaissent JAMAIS comme
`to_status` : ces transitions sont pilotées par le Publication Coordinator
(module 5, hors périmètre de cette Lambda) — toute tentative, même par
ADMIN via un payload forgé, doit être un refus explicite, jamais un 500
silencieux qui laisserait deviner une faille.
"""
from errors import ForbiddenError, ValidationError

# (from_status, to_status) -> règles. "roles" : rôles autorisés à déclencher
# cette transition. "owner_only" : en plus du rôle, l'acteur doit être
# created_by de l'AO. "requires_reason" : un motif non vide est obligatoire.
# "requires_mfa" : l'acteur (ADMIN) doit avoir mfa_enabled=True (vérifié en
# direct via Cognito GetUser, pas seulement la valeur en base — double
# contrôle CLAUDE.md).
TRANSITIONS = {
    ("DRAFT", "PENDING_REVIEW"): {
        "roles": {"AGENT"}, "owner_only": True, "requires_reason": False, "requires_mfa": False,
    },
    ("REVISION_REQUESTED", "PENDING_REVIEW"): {
        "roles": {"AGENT"}, "owner_only": True, "requires_reason": False, "requires_mfa": False,
    },
    ("PENDING_REVIEW", "REVISION_REQUESTED"): {
        "roles": {"REVIEWER"}, "owner_only": False, "requires_reason": True, "requires_mfa": False,
    },
    ("PENDING_REVIEW", "APPROVED"): {
        "roles": {"ADMIN"}, "owner_only": False, "requires_reason": False, "requires_mfa": True,
    },
    ("PENDING_REVIEW", "REJECTED"): {
        "roles": {"ADMIN"}, "owner_only": False, "requires_reason": True, "requires_mfa": True,
    },
    ("EXPIRED", "ARCHIVED"): {
        "roles": {"ADMIN"}, "owner_only": False, "requires_reason": False, "requires_mfa": True,
    },
}

# Statuts qu'aucune transition gérée par cette Lambda ne doit jamais
# atteindre — pilotés exclusivement par le Publication Coordinator.
COORDINATOR_ONLY_STATUSES = {"QUEUED_FOR_PUBLICATION", "PUBLISHED", "EXPIRED"}


def can_transition(*, role, from_status, to_status, is_owner, mfa_enabled, reason):
    """Lève ForbiddenError/ValidationError si la transition est refusée, sinon ne renvoie rien."""
    if to_status in COORDINATOR_ONLY_STATUSES:
        raise ForbiddenError(
            f"La transition vers {to_status} est pilotée par le Publication Coordinator, pas par ce module."
        )

    rule = TRANSITIONS.get((from_status, to_status))
    if rule is None:
        raise ForbiddenError(f"Transition {from_status} -> {to_status} non autorisée.")

    if role not in rule["roles"]:
        raise ForbiddenError(f"Le rôle {role} ne peut pas effectuer la transition {from_status} -> {to_status}.")

    if rule["owner_only"] and not is_owner:
        raise ForbiddenError("Seul le créateur de l'AO peut effectuer cette action.")

    if rule["requires_mfa"] and not mfa_enabled:
        raise ForbiddenError("Cette action ADMIN requiert le MFA activé sur le compte.")

    if rule["requires_reason"] and not (reason and reason.strip()):
        raise ValidationError("Un motif (reason) non vide est requis pour cette action.", fields={"reason": "requis"})
