"""
Point d'entrée Lambda reference_data_api (module 01) — routage sur
event["routeKey"], provisioning JIT de l'utilisateur, dispatch vers
reference_data.py, mapping des erreurs métier en réponses HTTP.

Calqué sur backend/tenders_api/handler.py (duplication délibérée, voir
tasks/01-referentiels-admin.md) : une connexion DSQL par invocation, pas de
pool à chaud — le volume de ce back-office ne le justifie pas.
"""
import base64
import json
import logging
import uuid as uuid_module
from decimal import Decimal
from datetime import datetime, date

import auth
import db
import reference_data
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
    if route_key == "GET /countries":
        return 200, {"items": reference_data.list_countries(cur, user)}

    if route_key == "POST /countries":
        return 201, reference_data.create_country(cur, user, body, correlation_id, ip_address)

    if route_key == "GET /categories":
        return 200, {"items": reference_data.list_categories(cur, user)}

    if route_key == "POST /categories":
        return 201, reference_data.create_category(cur, user, body, correlation_id, ip_address)

    if route_key == "PUT /categories/{id}":
        return 200, reference_data.update_category(cur, user, path_params.get("id"), body, correlation_id, ip_address)

    if route_key == "GET /organizations":
        return 200, {"items": reference_data.list_organizations(cur, user)}

    if route_key == "POST /organizations":
        return 201, reference_data.create_organization(cur, user, body, correlation_id, ip_address)

    if route_key == "PUT /organizations/{id}":
        return 200, reference_data.update_organization(cur, user, path_params.get("id"), body, correlation_id, ip_address)

    if route_key == "GET /diffusion-partnerships":
        return 200, {"items": reference_data.list_diffusion_partnerships(cur, user)}

    if route_key == "POST /diffusion-partnerships":
        return 201, reference_data.create_diffusion_partnership(cur, user, body, correlation_id, ip_address)

    if route_key == "PUT /diffusion-partnerships/{id}":
        return 200, reference_data.update_diffusion_partnership(
            cur, user, path_params.get("id"), body, correlation_id, ip_address
        )

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
