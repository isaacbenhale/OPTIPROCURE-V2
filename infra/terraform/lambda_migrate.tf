# =====================================================================
# Lambda de migration — exécute infra/terraform/db/migrations/*.sql
# =====================================================================
# Prérequis : `make build-migrate-lambda` avant `terraform apply` (voir
# Makefile) pour vendoriser psycopg2-binary dans build/migrate/.

data "archive_file" "lambda_migrate" {
  type        = "zip"
  source_dir  = "${path.module}/build/migrate"
  output_path = "${path.module}/build/migrate.zip"
}

resource "aws_lambda_function" "db_migrate" {
  function_name = "${local.name_prefix}-db-migrate"
  role          = aws_iam_role.lambda_migrate.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 256

  filename         = data.archive_file.lambda_migrate.output_path
  source_code_hash = data.archive_file.lambda_migrate.output_base64sha256

  environment {
    variables = {
      DSQL_ENDPOINT     = local.dsql_endpoint
      MIGRATIONS_BUCKET = aws_s3_bucket.migrations.bucket
    }
  }

  tags = local.tags
}

# --- Upload des fichiers de migration dans S3 ---------------------------

locals {
  migration_files = fileset("${path.module}/db/migrations", "*.sql")
}

resource "aws_s3_object" "migrations" {
  for_each = local.migration_files

  bucket = aws_s3_bucket.migrations.id
  key    = each.value
  source = "${path.module}/db/migrations/${each.value}"
  etag   = filemd5("${path.module}/db/migrations/${each.value}")
}

# --- Exécution automatique après chaque changement de schéma -----------
# S'invoque à nouveau uniquement si le contenu des fichiers de migration
# change (triggers basés sur le hash combiné) — jamais à chaque apply
# sans changement, pour rester idempotent.

resource "aws_lambda_invocation" "run_migrations" {
  function_name = aws_lambda_function.db_migrate.function_name
  input         = jsonencode({})

  triggers = {
    migrations_hash  = md5(join("", [for f in local.migration_files : filemd5("${path.module}/db/migrations/${f}")]))
    function_version = aws_lambda_function.db_migrate.source_code_hash
  }

  depends_on = [aws_s3_object.migrations]
}

output "migration_lambda_result" {
  description = "Sortie brute de la dernière exécution des migrations (statuts par fichier)"
  value       = aws_lambda_invocation.run_migrations.result
}
