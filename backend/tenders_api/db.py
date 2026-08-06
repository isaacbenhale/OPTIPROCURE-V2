"""
Connexion Aurora DSQL non-admin (rôle tenders_api_role, voir migrations
058-061) et exécution transactionnelle avec retry OCC.

Contrairement à lambda_src/migrate/handler.py (autocommit=True, 1 DDL par
transaction), cette Lambda fait du DML multi-instructions atomique : une
transaction explicite par opération métier (ex. UPDATE tenders + INSERT
tender_status_history + INSERT audit_log doivent réussir ou échouer
ensemble), donc autocommit=False avec commit/rollback explicites.
"""
import os
import time

import boto3
import certifi
import psycopg2
import psycopg2.extras

from errors import ConflictError

REGION = os.environ["AWS_REGION"]
DSQL_ENDPOINT = os.environ["DSQL_ENDPOINT"]
DB_USER = os.environ.get("DSQL_APP_USER", "tenders_api_role")

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 0.5
OCC_SQLSTATE = "40001"
UNIQUE_VIOLATION_SQLSTATE = "23505"  # ex. idx_tenders_org_reference — conflit réel, jamais retenté


def get_connection():
    dsql_client = boto3.client("dsql", region_name=REGION)
    token = dsql_client.generate_db_connect_auth_token(DSQL_ENDPOINT, REGION)
    conn = psycopg2.connect(
        host=DSQL_ENDPOINT,
        port=5432,
        dbname="postgres",
        user=DB_USER,
        password=token,
        sslmode="verify-full",
        # "system" échoue en Lambda zip (pas de magasin CA OS à l'emplacement
        # attendu par libpq) — bundle CA public certifi, voir migrate/handler.py.
        sslrootcert=certifi.where(),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = False
    return conn


def run_in_transaction(conn, fn, *, max_retries=MAX_RETRIES, base_backoff=BASE_BACKOFF_SECONDS):
    """
    Exécute fn(cursor) dans une transaction ; retry avec backoff exponentiel
    sur SQLSTATE 40001 (OCC — comportement normal sous DSQL, jamais fatal
    au premier échec). Au-delà de max_retries, lève ConflictError (409),
    jamais une 500 silencieuse.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            with conn.cursor() as cur:
                result = fn(cur)
            conn.commit()
            return result
        except Exception as exc:  # noqa: BLE001 — inspection du SQLSTATE ci-dessous
            conn.rollback()
            sqlstate = getattr(exc, "pgcode", None)
            if sqlstate == OCC_SQLSTATE:
                if attempt <= max_retries:
                    time.sleep(base_backoff * (2 ** (attempt - 1)))
                    continue
                raise ConflictError("Conflit de concurrence (OCC) après plusieurs tentatives — réessayer.") from exc
            if sqlstate == UNIQUE_VIOLATION_SQLSTATE:
                raise ConflictError("Un AO avec cette référence existe déjà pour cette organisation.") from exc
            raise
