"""
Authentification/autorisation — double contrôle CLAUDE.md : groupe Cognito
(JWT, déjà validé par l'API Gateway JWT Authorizer en amont) ET permission
métier fine relue en base (role/is_active/mfa_enabled sur la ligne `users`
upsertée à chaque requête).

Copie de backend/tenders_api/auth.py (duplication délibérée plutôt qu'une
abstraction partagée prématurée — voir tasks/01-referentiels-admin.md).

Le frontend doit envoyer l'ACCESS TOKEN Cognito (pas l'ID token) — c'est
celui-ci que le JWT Authorizer HTTP API valide via client_id/aud. L'access
token ne porte ni email ni name, donc on appelle cognito-idp:GetUser avec
ce même token pour les récupérer, ainsi que le statut MFA réel — cet appel
s'authentifie par le token lui-même, aucune permission IAM supplémentaire
requise sur le rôle Lambda (principe du moindre privilège respecté).
"""
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

from errors import ForbiddenError, UnauthorizedError

REGION = os.environ["AWS_REGION"]

# Précédence Cognito (cognito.tf) : la plus basse gagne. ADMIN=1, REVIEWER=2,
# AGENT=3 — on résout donc dans cet ordre si un token porte plusieurs groupes.
ROLE_PRECEDENCE = ("ADMIN", "REVIEWER", "AGENT")

LOGIN_LOG_WINDOW = timedelta(minutes=30)


def get_claims(event) -> dict:
    try:
        return event["requestContext"]["authorizer"]["jwt"]["claims"]
    except KeyError as exc:
        raise UnauthorizedError("Requête non authentifiée (claims JWT absents).") from exc


def get_bearer_token(event) -> str:
    headers = event.get("headers") or {}
    raw = headers.get("authorization") or headers.get("Authorization") or ""
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    raise UnauthorizedError("En-tête Authorization manquant ou mal formé.")


def resolve_role_from_groups(claims: dict) -> str | None:
    groups_raw = claims.get("cognito:groups", "")
    groups = {g.strip() for g in groups_raw.split(",") if g.strip()} if groups_raw else set()
    for role in ROLE_PRECEDENCE:
        if role in groups:
            return role
    return None


def fetch_cognito_user_info(access_token: str) -> dict:
    client = boto3.client("cognito-idp", region_name=REGION)
    try:
        resp = client.get_user(AccessToken=access_token)
    except ClientError as exc:
        raise UnauthorizedError("Token invalide ou expiré (cognito-idp:GetUser a échoué).") from exc

    attrs = {a["Name"]: a["Value"] for a in resp.get("UserAttributes", [])}
    mfa_settings = resp.get("UserMFASettingList") or []
    return {
        "email": attrs.get("email"),
        "name": attrs.get("name"),
        "mfa_enabled": len(mfa_settings) > 0,
    }


def upsert_user(cur, claims: dict, cognito_info: dict) -> tuple[dict, bool]:
    """
    Provisioning "just-in-time" : aucun trigger Cognito Post-Confirmation
    n'existe dans cette infra, donc chaque requête authentifiée synchronise
    la ligne `users` à partir du JWT + GetUser. Renvoie (user, is_new_session)
    — is_new_session sert à maybe_log_login pour ne pas polluer audit_log à
    chaque GET.
    """
    sub = claims.get("sub")
    if not sub:
        raise UnauthorizedError("Token sans claim 'sub'.")

    role = resolve_role_from_groups(claims)
    if role is None:
        raise ForbiddenError("Utilisateur sans groupe Cognito (AGENT/REVIEWER/ADMIN) — accès refusé.")

    email = cognito_info.get("email") or claims.get("email")
    if not email:
        raise UnauthorizedError("Impossible de déterminer l'email de l'utilisateur.")
    # users.full_name est NOT NULL mais l'attribut Cognito "name" n'est pas
    # requis (cognito.tf ne rend obligatoire que "email") — repli sur l'email.
    full_name = cognito_info.get("name") or email
    mfa_enabled = cognito_info["mfa_enabled"]

    cur.execute("SELECT last_login_at FROM users WHERE cognito_sub = %(sub)s", {"sub": sub})
    existing = cur.fetchone()
    is_new_session = (
        existing is None
        or existing["last_login_at"] is None
        or (datetime.now(timezone.utc) - existing["last_login_at"]) > LOGIN_LOG_WINDOW
    )

    cur.execute(
        """
        INSERT INTO users (cognito_sub, email, full_name, role, mfa_enabled, last_login_at)
        VALUES (%(sub)s, %(email)s, %(full_name)s, %(role)s, %(mfa_enabled)s, now())
        ON CONFLICT (cognito_sub) DO UPDATE SET
            email         = EXCLUDED.email,
            full_name     = EXCLUDED.full_name,
            role          = EXCLUDED.role,
            mfa_enabled   = EXCLUDED.mfa_enabled,
            last_login_at = now(),
            updated_at    = now()
        RETURNING id, cognito_sub, email, full_name, role, is_active, mfa_enabled, last_login_at
        """,
        {"sub": sub, "email": email, "full_name": full_name, "role": role, "mfa_enabled": mfa_enabled},
    )
    return cur.fetchone(), is_new_session


def maybe_log_login(cur, user: dict, is_new_session: bool, correlation_id: str, ip_address: str | None):
    if not is_new_session:
        return
    cur.execute(
        """
        INSERT INTO audit_log (actor_user_id, action, entity_type, entity_id, details, ip_address, correlation_id)
        VALUES (%(actor)s, 'LOGIN', 'user', %(actor)s, %(details)s, %(ip)s, %(correlation_id)s)
        """,
        {
            "actor": user["id"],
            "details": '{"role": "%s"}' % user["role"],
            "ip": ip_address,
            "correlation_id": correlation_id,
        },
    )


def require_active(user: dict):
    if not user["is_active"]:
        raise ForbiddenError("Compte désactivé.")


def require_role(user: dict, allowed: set[str]):
    if user["role"] not in allowed:
        raise ForbiddenError(f"Action réservée à {', '.join(sorted(allowed))}.")


def require_mfa(user: dict):
    if not user["mfa_enabled"]:
        raise ForbiddenError("Cette action ADMIN requiert le MFA activé sur le compte.")
