"""
Point d'entrée Lambda users_api (module 13) — routage sur event["routeKey"],
provisioning JIT de l'ADMIN appelant, dispatch vers users.py, mapping des
erreurs métier en réponses HTTP.

Calqué sur backend/reference_data_api/handler.py (duplication délibérée,
voir tasks/13-gestion-comptes-internes.md) : une connexion DSQL par
invocation, pas de pool à chaud.
"""
import base64
import json
import logging
import uuid as uuid_module
from datetime import datetime, date
from decimal import Decimal

import auth
import db
import users as users_module
from errors import ApiError, NotFoundError, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=_json_default),
    }


def _error_response(exc: ApiError):
    return _response(exc.status_code, {"error": {"code": exc.code, "message": exc.message, "fields": exc.fields}})


def _parse_body(event):
    raw = event.get("body")
    if not raw:
        return {}
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError("Corps de requête JSON invalide.") from exc


def _route(cur, route_key, user, path_params, body, correlation_id, ip_address):
    if route_key == "GET /users":
        return 200, {"items": users_module.list_accounts(cur, user)}

    if route_key == "POST /users":
        return 201, users_module.create_account(cur, user, body, correlation_id, ip_address)

    if route_key == "PUT /users/{sub}/groups":
        return 200, users_module.update_groups(cur, user, path_params.get("sub"), body, correlation_id, ip_address)

    if route_key == "POST /users/{sub}/deactivate":
        return 200, users_module.deactivate_account(cur, user, path_params.get("sub"), correlation_id, ip_address)

    if route_key == "POST /users/{sub}/activate":
        return 200, users_module.activate_account(cur, user, path_params.get("sub"), correlation_id, ip_address)

    if route_key == "DELETE /users/{sub}":
        return 200, users_module.delete_account(cur, user, path_params.get("sub"), correlation_id, ip_address)

    raise NotFoundError(f"Route inconnue: {route_key}")


def handler(event, context):
    correlation_id = getattr(context, "aws_request_id", None) or str(uuid_module.uuid4())
    route_key = event.get("routeKey", "")
    ip_address = ((event.get("requestContext") or {}).get("http") or {}).get("sourceIp")

    conn = None
    try:
        claims = auth.get_claims(event)
        access_token = auth.get_bearer_token(event)
        cognito_info = auth.fetch_cognito_user_info(access_token)

        conn = db.get_connection()

        def _authenticate(cur):
            user, is_new_session = auth.upsert_user(cur, claims, cognito_info)
            auth.require_active(user)
            auth.maybe_log_login(cur, user, is_new_session, correlation_id, ip_address)
            return user

        user = db.run_in_transaction(conn, _authenticate)

        body = _parse_body(event)
        path_params = event.get("pathParameters") or {}

        status_code, payload = db.run_in_transaction(
            conn,
            lambda cur: _route(cur, route_key, user, path_params, body, correlation_id, ip_address),
        )

        logger.info(
            "request_ok route=%s user_id=%s status=%s correlation_id=%s",
            route_key, user.get("id"), status_code, correlation_id,
        )
        return _response(status_code, payload)

    except ApiError as exc:
        logger.warning(
            "request_error route=%s code=%s status=%s correlation_id=%s",
            route_key, exc.code, exc.status_code, correlation_id,
        )
        return _error_response(exc)
    except Exception:  # noqa: BLE001 — jamais de fuite de détail interne au client
        logger.exception("request_unhandled_error route=%s correlation_id=%s", route_key, correlation_id)
        return _response(500, {"error": {"code": "INTERNAL_ERROR", "message": "Erreur interne.", "fields": {}}})
    finally:
        if conn is not None:
            conn.close()
