"""
Connexion Aurora DSQL non-admin (rôle users_api_role, voir migrations
067-069) et exécution transactionnelle avec retry OCC.

Copie de backend/tenders_api/db.py (duplication délibérée plutôt qu'une
abstraction partagée prématurée — voir tasks/01-referentiels-admin.md et
tasks/13-gestion-comptes-internes.md).
Contrairement à lambda_src/migrate/handler.py (autocommit=True, 1 DDL par
transaction), cette Lambda fait du DML multi-instructions atomique : une
transaction explicite par opération métier, donc autocommit=False avec
commit/rollback explicites.
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
DB_USER = os.environ.get("DSQL_APP_USER", "users_api_role")

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 0.5
OCC_SQLSTATE = "40001"
UNIQUE_VIOLATION_SQLSTATE = "23505"  # ex. users.email, users.cognito_sub


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
        # attendu par libpq) — bundle CA public certifi.
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
                raise ConflictError("Une ligne avec cette valeur unique existe déjà.") from exc
            raise
