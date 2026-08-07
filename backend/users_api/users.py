"""
Logique métier de gestion des comptes internes (module 13) : lister,
créer, changer les groupes (rôles) et activer/désactiver un compte
back-office (AGENT/REVIEWER/ADMIN). Écriture réservée à ADMIN + MFA (même
exigence que les actions sensibles de tenders_api/reference_data_api).

Chaque fonction reçoit un curseur ouvert dans une transaction déjà démarrée
par db.run_in_transaction (appelé depuis handler.py) — sauf pour les appels
Cognito eux-mêmes, qui ne sont pas transactionnels par nature (pas de
rollback possible côté IdP) : on écrit d'abord côté Cognito, puis en DSQL,
jamais l'inverse — voir tasks/13-gestion-comptes-internes.md, "Décisions
actées" §1 (AdminUserGlobalSignOut) et §3 (filtrage explicite par groupe).
"""
import json
import os

import boto3
from botocore.exceptions import ClientError

from auth import ROLE_PRECEDENCE, require_mfa, require_role
from errors import ConflictError, NotFoundError, ValidationError

REGION = os.environ["AWS_REGION"]
USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]

ALL_ROLES = set(ROLE_PRECEDENCE)  # {"ADMIN", "REVIEWER", "AGENT"}
WRITE_ROLES = {"ADMIN"}


def _cognito_client():
    return boto3.client("cognito-idp", region_name=REGION)


def effective_role(groups: set) -> str | None:
    """Rôle effectif d'un ensemble de groupes — même précédence que
    auth.resolve_role_from_groups (ADMIN > REVIEWER > AGENT)."""
    for role in ROLE_PRECEDENCE:
        if role in groups:
            return role
    return None


def _validate_groups(groups) -> set:
    groups = set(groups or [])
    if not groups or not groups.issubset(ALL_ROLES):
        raise ValidationError(
            "groups invalide.", fields={"groups": f"sous-ensemble non vide de {sorted(ALL_ROLES)} requis"}
        )
    return groups


def _write_audit(cur, user, action, entity_id, details, correlation_id, ip_address):
    cur.execute(
        """
        INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, details, ip_address, correlation_id)
        VALUES (%(actor)s, %(action)s, 'user_account', %(entity_id)s, %(details)s, %(ip)s, %(correlation_id)s)
        """,
        {
            "actor": user["id"],
            "action": action,
            "entity_id": entity_id,
            "details": json.dumps(details, default=str),
            "ip": ip_address,
            "correlation_id": correlation_id,
        },
    )


# --- Lecture ----------------------------------------------------------------

def list_accounts(cur, user):
    require_role(user, WRITE_ROLES)
    client = _cognito_client()

    # Filtrage explicite par groupe plutôt qu'un ListUsers brut sur tout le
    # pool — voir tasks/13-gestion-comptes-internes.md, "Décisions actées" §3 :
    # reste correct même si un compte orphelin (sans groupe) existait un jour.
    accounts = {}
    for group in ALL_ROLES:
        paginator = client.get_paginator("list_users_in_group")
        for page in paginator.paginate(UserPoolId=USER_POOL_ID, GroupName=group):
            for cognito_user in page["Users"]:
                attrs = {a["Name"]: a["Value"] for a in cognito_user.get("Attributes", [])}
                sub = attrs.get("sub")
                if sub is None:
                    continue
                entry = accounts.setdefault(
                    sub,
                    {
                        "cognito_sub": sub,
                        "email": attrs.get("email", cognito_user["Username"]),
                        "cognito_enabled": cognito_user["Enabled"],
                        "user_status": cognito_user["UserStatus"],
                        "groups": set(),
                    },
                )
                entry["groups"].add(group)

    if not accounts:
        return []

    subs = list(accounts.keys())
    cur.execute(
        "SELECT cognito_sub, full_name, is_active, mfa_enabled, last_login_at FROM users "
        "WHERE cognito_sub = ANY(%(subs)s) AND deleted_at IS NULL",
        {"subs": subs},
    )
    db_rows = {row["cognito_sub"]: row for row in cur.fetchall()}

    result = []
    for sub, entry in accounts.items():
        db_row = db_rows.get(sub)
        result.append(
            {
                "cognito_sub": sub,
                "email": entry["email"],
                "full_name": db_row["full_name"] if db_row else None,
                "groups": sorted(entry["groups"], key=ROLE_PRECEDENCE.index),
                "effective_role": effective_role(entry["groups"]),
                "cognito_enabled": entry["cognito_enabled"],
                "user_status": entry["user_status"],
                "is_active": db_row["is_active"] if db_row else True,
                "mfa_enabled": db_row["mfa_enabled"] if db_row else False,
                "last_login_at": db_row["last_login_at"] if db_row else None,
                # NB : db_row peut exister sans jamais s'être connecté — voir
                # create_account, qui insère la ligne `users` proactivement
                # dès la création pour que is_active soit gérable avant tout
                # premier login (sinon rien à UPDATE). Le vrai signal de
                # connexion est last_login_at, pas la simple existence de la
                # ligne (bug réel constaté le 2026-08-07 en vérification).
                "has_logged_in": bool(db_row and db_row["last_login_at"] is not None),
            }
        )
    result.sort(key=lambda r: r["email"])
    return result


def _get_account_email(cur, cognito_sub: str) -> str:
    """Username Cognito == email (voir create_account, Username=email à la
    création) — DSQL sert de table de correspondance sub -> email plutôt que
    de refaire un appel Cognito pour le résoudre."""
    cur.execute("SELECT email FROM users WHERE cognito_sub = %(sub)s AND deleted_at IS NULL", {"sub": cognito_sub})
    row = cur.fetchone()
    if row is None:
        raise NotFoundError("Compte introuvable.")
    return row["email"]


def _reject_self_action(user, target_sub: str, message: str):
    if user["cognito_sub"] == target_sub:
        raise ValidationError(message)


# --- Création -----------------------------------------------------------

def create_account(cur, user, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)

    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise ValidationError("Champ obligatoire manquant.", fields={"email": "requis"})
    groups = _validate_groups(payload.get("groups"))

    client = _cognito_client()
    try:
        resp = client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            # Sans ceci, DesiredDeliveryMediums vaut ["SMS"] par défaut chez
            # Cognito — aucun email d'invitation n'était donc envoyé, ces
            # comptes n'ayant pas de numéro de téléphone (bug réel constaté
            # le 2026-08-07). Pas de MessageAction=SUPPRESS : on veut
            # l'envoi automatique du mot de passe temporaire par Cognito
            # (décision "Format de l'email d'invitation", tasks/13-gestion-
            # comptes-internes.md). Ni TemporaryPassword ni statut ne sont
            # fixés ici : Cognito en génère un et place le compte en
            # FORCE_CHANGE_PASSWORD par défaut — le Hosted UI (pas de
            # formulaire de login custom dans ce projet) gère nativement
            # l'écran de changement de mot de passe à la première connexion,
            # aucun code applicatif supplémentaire n'est nécessaire ici.
            DesiredDeliveryMediums=["EMAIL"],
        )
    except client.exceptions.UsernameExistsException as exc:
        raise ConflictError("Un compte avec cet email existe déjà.") from exc
    except ClientError as exc:
        raise ValidationError(f"Échec de la création du compte Cognito : {exc}.") from exc

    attrs = {a["Name"]: a["Value"] for a in resp["User"]["Attributes"]}
    sub = attrs["sub"]

    for group in groups:
        client.admin_add_user_to_group(UserPoolId=USER_POOL_ID, Username=email, GroupName=group)

    role = effective_role(groups)
    cur.execute(
        """
        INSERT INTO users (cognito_sub, email, full_name, role, is_active, mfa_enabled)
        VALUES (%(sub)s, %(email)s, %(full_name)s, %(role)s, TRUE, FALSE)
        """,
        {"sub": sub, "email": email, "full_name": email, "role": role},
    )
    _write_audit(cur, user, "CREATE", sub, {"email": email, "groups": sorted(groups)}, correlation_id, ip_address)

    return {
        "cognito_sub": sub,
        "email": email,
        "groups": sorted(groups, key=ROLE_PRECEDENCE.index),
        "effective_role": role,
        "is_active": True,
        "mfa_enabled": False,
    }


# --- Changement de rôle (groupes) ---------------------------------------

def update_groups(cur, user, target_sub, payload, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    _reject_self_action(user, target_sub, "Un ADMIN ne peut pas modifier ses propres groupes (risque de blocage).")

    desired = _validate_groups(payload.get("groups"))
    email = _get_account_email(cur, target_sub)

    client = _cognito_client()
    current_resp = client.admin_list_groups_for_user(Username=email, UserPoolId=USER_POOL_ID)
    current = {g["GroupName"] for g in current_resp["Groups"] if g["GroupName"] in ALL_ROLES}

    to_add = desired - current
    to_remove = current - desired
    for group in to_add:
        client.admin_add_user_to_group(UserPoolId=USER_POOL_ID, Username=email, GroupName=group)
    for group in to_remove:
        client.admin_remove_user_from_group(UserPoolId=USER_POOL_ID, Username=email, GroupName=group)

    if to_add or to_remove:
        # Révoque les refresh tokens actifs — voir "Décisions actées" §1 :
        # effet garanti sous ~15 min (durée de vie résiduelle de l'access
        # token en cours), pas un vrai effet à la requête suivante.
        client.admin_user_global_sign_out(UserPoolId=USER_POOL_ID, Username=email)

    role = effective_role(desired)
    cur.execute(
        "UPDATE users SET role = %(role)s, updated_at = now() WHERE cognito_sub = %(sub)s",
        {"role": role, "sub": target_sub},
    )
    _write_audit(cur, user, "UPDATE_GROUPS", target_sub, {"groups": sorted(desired)}, correlation_id, ip_address)

    return {
        "cognito_sub": target_sub,
        "groups": sorted(desired, key=ROLE_PRECEDENCE.index),
        "effective_role": role,
    }


# --- Activation / désactivation ------------------------------------------

def _set_active(cur, user, target_sub, is_active, correlation_id, ip_address):
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    if not is_active:
        _reject_self_action(user, target_sub, "Un ADMIN ne peut pas désactiver son propre compte.")

    cur.execute(
        "SELECT email, is_active FROM users WHERE cognito_sub = %(sub)s AND deleted_at IS NULL", {"sub": target_sub}
    )
    row = cur.fetchone()
    if row is None:
        raise NotFoundError("Compte introuvable.")
    if row["is_active"] == is_active:
        return {"cognito_sub": target_sub, "is_active": is_active}

    client = _cognito_client()
    email = row["email"]
    if is_active:
        client.admin_enable_user(UserPoolId=USER_POOL_ID, Username=email)
    else:
        # Ceinture et bretelles : is_active en DSQL (source d'autorité,
        # vérifiée à chaque requête via require_active) suffit déjà à
        # bloquer le compte, mais AdminDisableUser bloque aussi une
        # authentification Cognito qui n'aurait pas encore de ligne `users`
        # (compte jamais connecté), et AdminUserGlobalSignOut tue toute
        # session déjà active immédiatement.
        client.admin_disable_user(UserPoolId=USER_POOL_ID, Username=email)
        client.admin_user_global_sign_out(UserPoolId=USER_POOL_ID, Username=email)

    cur.execute(
        "UPDATE users SET is_active = %(is_active)s, updated_at = now() WHERE cognito_sub = %(sub)s",
        {"is_active": is_active, "sub": target_sub},
    )
    _write_audit(
        cur, user, "ACTIVATE" if is_active else "DEACTIVATE", target_sub, {}, correlation_id, ip_address
    )
    return {"cognito_sub": target_sub, "is_active": is_active}


def deactivate_account(cur, user, target_sub, correlation_id, ip_address):
    return _set_active(cur, user, target_sub, False, correlation_id, ip_address)


def activate_account(cur, user, target_sub, correlation_id, ip_address):
    return _set_active(cur, user, target_sub, True, correlation_id, ip_address)


# --- Suppression ----------------------------------------------------------

def delete_account(cur, user, target_sub, correlation_id, ip_address):
    """Suppression définitive côté Cognito (AdminDeleteUser — pas de
    « corbeille » côté IdP), et soft-delete côté DSQL (deleted_at) plutôt
    qu'un vrai DELETE : préserve l'historique (tenders.created_by,
    audit_log.actor_user_id référencent users.id, sans FK sous DSQL — voir
    CLAUDE.md) au lieu de casser ces références. Le compte disparaît de
    list_accounts dès l'appel : il n'appartient plus à aucun groupe Cognito
    une fois supprimé, donc invisible au filtrage par groupe (§3)."""
    require_role(user, WRITE_ROLES)
    require_mfa(user)
    _reject_self_action(user, target_sub, "Un ADMIN ne peut pas supprimer son propre compte.")

    email = _get_account_email(cur, target_sub)

    client = _cognito_client()
    try:
        client.admin_delete_user(UserPoolId=USER_POOL_ID, Username=email)
    except client.exceptions.UserNotFoundException:
        pass  # déjà supprimé côté Cognito — on continue pour nettoyer DSQL

    cur.execute(
        "UPDATE users SET deleted_at = now(), updated_at = now() WHERE cognito_sub = %(sub)s",
        {"sub": target_sub},
    )
    _write_audit(cur, user, "DELETE", target_sub, {"email": email}, correlation_id, ip_address)

    return {"cognito_sub": target_sub, "deleted": True}
