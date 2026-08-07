# =====================================================================
# Rôles IAM — un rôle dédié par Lambda, permissions minimales (CLAUDE.md)
# =====================================================================

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# --- Lambda de migration (exécution du schéma SQL) ---------------------
# dsql:DbConnectAdmin : seule cette Lambda a le droit de se connecter en
# tant qu'admin DSQL, réservé à l'exécution des migrations (CLAUDE.md :
# "Connexion : IAM uniquement / DsqlSigner / generate-db-connect-admin-auth-token").

resource "aws_iam_role" "lambda_migrate" {
  name               = "${local.name_prefix}-lambda-migrate"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "lambda_migrate_policy" {
  statement {
    sid       = "DsqlAdminConnect"
    actions   = ["dsql:DbConnectAdmin"]
    resources = [aws_dsql_cluster.main.arn]
  }
  statement {
    sid       = "ReadMigrationFiles"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.migrations.arn, "${aws_s3_bucket.migrations.arn}/*"]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_migrate" {
  name   = "${local.name_prefix}-lambda-migrate-policy"
  role   = aws_iam_role.lambda_migrate.id
  policy = data.aws_iam_policy_document.lambda_migrate_policy.json
}

# --- Lambda métier back-office (CRUD des AO) ---------------------------
# dsql:DbConnect (non-admin) : la Lambda métier ne doit jamais utiliser
# le rôle admin DSQL — c'est elle qui applique les autorisations fines
# par rôle Cognito (AGENT/REVIEWER/ADMIN), pas la base.

resource "aws_iam_role" "lambda_tenders_api" {
  name               = "${local.name_prefix}-lambda-tenders-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "lambda_tenders_api_policy" {
  statement {
    sid       = "DsqlConnect"
    actions   = ["dsql:DbConnect"]
    resources = [aws_dsql_cluster.main.arn]
  }
  statement {
    sid       = "DocumentsBucket"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.documents.arn}/*"]
  }
  statement {
    # boto3 signe la requête cognito-idp:GetUser en SigV4 avec les
    # identifiants IAM de la Lambda — contrairement à un appel direct
    # depuis un navigateur (non signé, authentifié par le seul access
    # token), IAM évalue donc bien cette action pour le rôle appelant.
    # Sans ce Allow, l'appel échoue par déni implicite malgré un token
    # valide (bug réel observé et corrigé le 2026-08-07, voir auth.py).
    sid       = "CognitoGetUser"
    actions   = ["cognito-idp:GetUser"]
    resources = [aws_cognito_user_pool.backoffice.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_tenders_api" {
  name   = "${local.name_prefix}-lambda-tenders-api-policy"
  role   = aws_iam_role.lambda_tenders_api.id
  policy = data.aws_iam_policy_document.lambda_tenders_api_policy.json
}

# --- Lambda référentiels admin (pays/catégories/organisations/partenariats,
# module 01) -------------------------------------------------------------
# dsql:DbConnect (non-admin), rôle Postgres dédié reference_data_api_role
# (migrations 062-064) — jamais le même rôle que lambda_tenders_api, même
# principe de séparation que pour toutes les Lambdas de ce projet.

resource "aws_iam_role" "lambda_reference_data_api" {
  name               = "${local.name_prefix}-lambda-reference-data-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "lambda_reference_data_api_policy" {
  statement {
    sid       = "DsqlConnect"
    actions   = ["dsql:DbConnect"]
    resources = [aws_dsql_cluster.main.arn]
  }
  statement {
    # Voir le commentaire équivalent dans lambda_tenders_api_policy —
    # même auth.py, même besoin (boto3 signe GetUser en SigV4).
    sid       = "CognitoGetUser"
    actions   = ["cognito-idp:GetUser"]
    resources = [aws_cognito_user_pool.backoffice.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_reference_data_api" {
  name   = "${local.name_prefix}-lambda-reference-data-api-policy"
  role   = aws_iam_role.lambda_reference_data_api.id
  policy = data.aws_iam_policy_document.lambda_reference_data_api_policy.json
}

# --- Lambda Publication Coordinator (stub, module 5 à venir) -----------

resource "aws_iam_role" "lambda_publication_coordinator" {
  name               = "${local.name_prefix}-lambda-pub-coordinator"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.tags
}

data "aws_iam_policy_document" "lambda_publication_coordinator_policy" {
  statement {
    sid       = "DsqlConnect"
    actions   = ["dsql:DbConnect"]
    resources = [aws_dsql_cluster.main.arn]
  }
  statement {
    sid       = "WriteManifest"
    actions   = ["s3:PutObject", "s3:GetObject"]
    resources = ["${aws_s3_bucket.manifests.arn}/*"]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_publication_coordinator" {
  name   = "${local.name_prefix}-lambda-pub-coordinator-policy"
  role   = aws_iam_role.lambda_publication_coordinator.id
  policy = data.aws_iam_policy_document.lambda_publication_coordinator_policy.json
}
