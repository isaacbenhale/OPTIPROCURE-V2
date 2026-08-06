"""
Lambda de migration — exécute le schéma SQL d'OptiProcure sur Aurora DSQL.

Contraintes DSQL respectées (voir CLAUDE.md et infra/terraform/db/migrations) :
  - 1 seule instruction DDL par transaction : connexion en autocommit,
    jamais de BEGIN...COMMIT englobant plusieurs fichiers.
  - Retry/backoff sur SQLSTATE 40001 (OCC) — comportement normal sous DSQL,
    pas une erreur fatale.
  - Connexion IAM uniquement, via generate_db_connect_admin_auth_token.
  - Les fichiers de migration sont exécutés dans l'ordre lexicographique
    de leur préfixe numérique (001_..., 002_..., etc.).

Déclenchement : invoqué par Terraform (aws_lambda_invocation, voir
lambda_migrate.tf) après chaque changement du contenu du bucket de
migrations. Peut aussi être invoqué manuellement :
  aws lambda invoke --function-name <name> --payload '{}' out.json

Substitution de placeholders : certains fichiers de migration référencent
des valeurs connues uniquement de Terraform (ex. l'ARN IAM d'un rôle Lambda
consommateur, dans 059_role_tenders_api_iam_grant.sql) — jamais codées en
dur dans le SQL versionné. Ces fichiers contiennent un placeholder
__NOM__ remplacé ici par la variable d'environnement correspondante avant
exécution ; no-op si le placeholder est absent du fichier.
"""
import json
import os
import time

import boto3
import psycopg2
from botocore.exceptions import ClientError

REGION = os.environ["AWS_REGION"]
DSQL_ENDPOINT = os.environ["DSQL_ENDPOINT"]
MIGRATIONS_BUCKET = os.environ["MIGRATIONS_BUCKET"]

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.5
OCC_SQLSTATE = "40001"

# Placeholder -> variable d'environnement. Ajouter une entrée ici pour
# chaque nouveau placeholder introduit dans une migration.
PLACEHOLDER_ENV_VARS = {
    "__TENDERS_API_ROLE_ARN__": "TENDERS_API_ROLE_ARN",
}


def _substitute_placeholders(sql_text):
    for placeholder, env_var in PLACEHOLDER_ENV_VARS.items():
        if placeholder in sql_text:
            value = os.environ.get(env_var)
            if not value:
                raise RuntimeError(
                    f"Placeholder {placeholder} présent dans la migration mais "
                    f"variable d'environnement {env_var} absente/vide."
                )
            sql_text = sql_text.replace(placeholder, value)
    return sql_text


def _get_connection():
    dsql_client = boto3.client("dsql", region_name=REGION)
    token = dsql_client.generate_db_connect_admin_auth_token(DSQL_ENDPOINT, REGION)
    conn = psycopg2.connect(
        host=DSQL_ENDPOINT,
        port=5432,
        dbname="postgres",
        user="admin",
        password=token,
        sslmode="verify-full",
        sslrootcert="system",
    )
    conn.autocommit = True  # obligatoire : 1 DDL par transaction sous DSQL
    return conn


def _list_migration_files(s3):
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=MIGRATIONS_BUCKET):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".sql"):
                keys.append(obj["Key"])
    return sorted(keys)  # tri lexicographique = ordre numérique (001_, 002_, ...)


def _run_statement(conn, sql_text, key):
    attempt = 0
    while True:
        attempt += 1
        try:
            with conn.cursor() as cur:
                cur.execute(sql_text)
            return {"key": key, "status": "OK", "attempts": attempt}
        except Exception as exc:  # noqa: BLE001 — on inspecte le SQLSTATE ci-dessous
            sqlstate = getattr(exc, "pgcode", None)
            if sqlstate == OCC_SQLSTATE and attempt <= MAX_RETRIES:
                backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                time.sleep(backoff)
                continue
            raise


def handler(event, context):
    s3 = boto3.client("s3", region_name=REGION)
    keys = _list_migration_files(s3)

    if not keys:
        return {"statusCode": 200, "body": json.dumps({"message": "Aucun fichier de migration trouvé."})}

    conn = _get_connection()
    results = []
    try:
        for key in keys:
            obj = s3.get_object(Bucket=MIGRATIONS_BUCKET, Key=key)
            sql_text = _substitute_placeholders(obj["Body"].read().decode("utf-8"))
            # Retire les lignes de commentaire pur pour éviter d'exécuter
            # un "batch" vide (fichier composé uniquement de commentaires).
            meaningful = "\n".join(
                line for line in sql_text.splitlines() if line.strip() and not line.strip().startswith("--")
            )
            if not meaningful.strip():
                results.append({"key": key, "status": "SKIPPED_COMMENT_ONLY"})
                continue

            try:
                result = _run_statement(conn, sql_text, key)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                results.append({"key": key, "status": "FAILED", "error": str(exc)})
                # On arrête au premier échec réel (hors OCC déjà retenté) :
                # les migrations doivent être appliquées dans l'ordre.
                raise
    finally:
        conn.close()

    return {"statusCode": 200, "body": json.dumps({"applied": results}, default=str)}
