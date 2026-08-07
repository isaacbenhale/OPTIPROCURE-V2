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
# created_by de l'AO — sauf ADMIN, qui contourne toujours cette contrainte
# (supervision globale, voir can_transition/compute_available_actions).
# "requires_reason" : un motif non vide est obligatoire. "requires_mfa" :
# l'acteur (ADMIN) doit avoir mfa_enabled=True (vérifié en direct via
# Cognito GetUser, pas seulement la valeur en base — double contrôle
# CLAUDE.md). ADMIN a tous les droits AGENT/REVIEWER en plus des siens —
# rôle de supervision globale, jamais l'inverse (AGENT/REVIEWER ne gagnent
# aucun droit ADMIN).
TRANSITIONS = {
    ("DRAFT", "PENDING_REVIEW"): {
        "roles": {"AGENT", "ADMIN"}, "owner_only": True, "requires_reason": False, "requires_mfa": False,
    },
    ("REVISION_REQUESTED", "PENDING_REVIEW"): {
        "roles": {"AGENT", "ADMIN"}, "owner_only": True, "requires_reason": False, "requires_mfa": False,
    },
    ("PENDING_REVIEW", "REVISION_REQUESTED"): {
        "roles": {"REVIEWER", "ADMIN"}, "owner_only": False, "requires_reason": True, "requires_mfa": False,
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

    if rule["owner_only"] and role != "ADMIN" and not is_owner:
        raise ForbiddenError("Seul le créateur de l'AO peut effectuer cette action.")

    if rule["requires_mfa"] and not mfa_enabled:
        raise ForbiddenError("Cette action ADMIN requiert le MFA activé sur le compte.")

    if rule["requires_reason"] and not (reason and reason.strip()):
        raise ValidationError("Un motif (reason) non vide est requis pour cette action.", fields={"reason": "requis"})


# --- Actions disponibles (module 03, frontend back-office) ----------------
# action_name -> to_status, pour les actions qui SONT des transitions de
# statut déjà couvertes par TRANSITIONS — réutilisées telles quelles, jamais
# dupliquées, pour éliminer tout risque de désynchronisation entre la
# matrice et la liste des boutons proposés au front.
STATUS_ACTIONS = {
    "submit": "PENDING_REVIEW",
    "return": "REVISION_REQUESTED",
    "approve": "APPROVED",
    "reject": "REJECTED",
    "archive": "ARCHIVED",
}

# Actions qui ne changent pas le statut d'un AO (update/endorse/delete) —
# hors de TRANSITIONS par nature, petite table séparée. ADMIN inclus partout
# (mêmes droits qu'AGENT/REVIEWER en plus des siens, voir TRANSITIONS).
NON_STATUS_ACTIONS = {
    "update": {"roles": {"AGENT", "ADMIN"}, "owner_only": True, "valid_statuses": {"DRAFT", "REVISION_REQUESTED"}},
    "endorse": {"roles": {"REVIEWER", "ADMIN"}, "owner_only": False, "valid_statuses": {"PENDING_REVIEW"}},
    "delete": {"roles": {"ADMIN"}, "owner_only": False, "valid_statuses": {"DRAFT"}},
}


def compute_available_actions(tender, user):
    """
    Liste des actions que cet utilisateur peut effectuer sur cet AO, sans
    I/O — consommée par tenders.get_tender/list_tenders et exposée au
    frontend (backend/tenders_api/.. -> frontend-admin) pour piloter
    l'affichage des boutons d'action sans dupliquer cette logique en TS.
    """
    is_owner = tender["created_by"] == user["id"]
    available = []

    is_admin = user["role"] == "ADMIN"

    for action, to_status in STATUS_ACTIONS.items():
        rule = TRANSITIONS.get((tender["status"], to_status))
        if rule is None or user["role"] not in rule["roles"]:
            continue
        if rule["owner_only"] and not is_admin and not is_owner:
            continue
        if rule["requires_mfa"] and not user["mfa_enabled"]:
            continue
        available.append(action)

    for action, rule in NON_STATUS_ACTIONS.items():
        if user["role"] not in rule["roles"]:
            continue
        if rule["owner_only"] and not is_admin and not is_owner:
            continue
        if tender["status"] not in rule["valid_statuses"]:
            continue
        available.append(action)

    return available
