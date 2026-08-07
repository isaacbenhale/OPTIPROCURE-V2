"""
Point d'entrée Lambda tenders_api (module 3) — routage sur event["routeKey"],
provisioning JIT de l'utilisateur, dispatch vers tenders.py, mapping des
erreurs métier en réponses HTTP. Une connexion DSQL par invocation (comme
lambda_src/migrate/handler.py) — simple et robuste, le volume back-office
ne justifie pas une gestion de pool de connexions à chaud.
"""
import base64
import json
import logging
import uuid as uuid_module
from decimal import Decimal
from datetime import datetime

import auth
import db
import documents as documents_module
import tenders as tenders_module
from errors import ApiError, NotFoundError, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
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


def _route(cur, route_key, user, tender_id, document_id, body, query_params, correlation_id, ip_address, access_token):
    if route_key == "GET /tenders":
        filters = {k: v for k, v in query_params.items() if k in ("status", "sector", "procedure_type", "country_id", "category_id", "q")}
        cursor = query_params.get("cursor")
        page_size = int(query_params.get("page_size", 20))
        items, next_cursor = tenders_module.list_tenders(cur, user, filters, cursor, page_size)
        return 200, {"items": items, "next_cursor": next_cursor}

    if route_key == "POST /tenders":
        return 201, tenders_module.create_tender(cur, user, body, correlation_id, ip_address)

    if route_key == "GET /tenders/{id}":
        return 200, tenders_module.get_tender(cur, user, tender_id)

    if route_key == "PUT /tenders/{id}":
        return 200, tenders_module.update_tender(cur, user, tender_id, body, correlation_id, ip_address)

    if route_key == "DELETE /tenders/{id}":
        tenders_module.delete_tender(cur, user, tender_id, correlation_id, ip_address)
        return 200, {"status": "deleted"}

    if route_key == "POST /tenders/{id}/submit":
        return 200, tenders_module.submit_for_review(cur, user, tender_id, correlation_id, ip_address)

    if route_key == "POST /tenders/{id}/return":
        return 200, tenders_module.return_to_agent(cur, user, tender_id, body.get("reason"), correlation_id, ip_address)

    if route_key == "POST /tenders/{id}/endorse":
        return 200, tenders_module.endorse(cur, user, tender_id, correlation_id, ip_address)

    if route_key == "POST /tenders/{id}/approve":
        return 200, tenders_module.approve(cur, user, tender_id, correlation_id, ip_address)

    if route_key == "POST /tenders/{id}/reject":
        return 200, tenders_module.reject(cur, user, tender_id, body.get("reason"), correlation_id, ip_address)

    if route_key == "POST /tenders/{id}/archive":
        return 200, tenders_module.archive(cur, user, tender_id, correlation_id, ip_address)

    if route_key == "GET /tenders/{id}/history":
        return 200, {"items": tenders_module.get_status_history(cur, user, tender_id)}

    if route_key == "POST /tenders/{id}/documents":
        return 201, documents_module.create_upload(cur, user, tender_id, body, correlation_id, ip_address)

    if route_key == "GET /tenders/{id}/documents":
        return 200, {"items": documents_module.list_documents(cur, user, tender_id)}

    if route_key == "GET /tenders/{id}/documents/{docId}":
        return 200, documents_module.get_document_download_url(cur, user, tender_id, document_id)

    if route_key == "DELETE /tenders/{id}/documents/{docId}":
        documents_module.delete_document(cur, user, tender_id, document_id, correlation_id, ip_address)
        return 200, {"status": "deleted"}

    if route_key == "GET /me":
        return 200, user

    if route_key == "POST /me/mfa/setup":
        return 200, auth.associate_mfa(access_token)

    if route_key == "POST /me/mfa/verify":
        auth.verify_mfa(access_token, body.get("code", ""))
        return 200, {"status": "mfa_enabled"}

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
        query_params = event.get("queryStringParameters") or {}
        tender_id = path_params.get("id")
        document_id = path_params.get("docId")

        status_code, payload = db.run_in_transaction(
            conn,
            lambda cur: _route(
                cur, route_key, user, tender_id, document_id, body, query_params, correlation_id, ip_address,
                access_token,
            ),
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
