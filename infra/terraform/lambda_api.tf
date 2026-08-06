# =====================================================================
# Lambdas applicatives — tenders_api (module 3, CRUD + workflow des AO) et
# Publication Coordinator (module 5, encore un placeholder)
# =====================================================================
# tenders_api : code source dans backend/tenders_api/, packagé (avec
# psycopg2-binary vendorisé) par `make build-tenders-api-lambda` dans
# build/tenders_api/ avant `terraform apply` — voir Makefile.

data "archive_file" "lambda_tenders_api" {
  type        = "zip"
  source_dir  = "${path.module}/build/tenders_api"
  output_path = "${path.module}/build/tenders_api.zip"
}

resource "aws_lambda_function" "tenders_api" {
  function_name = "${local.name_prefix}-tenders-api"
  role          = aws_iam_role.lambda_tenders_api.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_tenders_api.output_path
  source_code_hash = data.archive_file.lambda_tenders_api.output_base64sha256

  environment {
    variables = {
      DSQL_ENDPOINT = local.dsql_endpoint
      # Rôle Postgres non-admin créé/lié par les migrations 058-061 —
      # jamais dsql:DbConnectAdmin pour cette Lambda (voir iam.tf).
      DSQL_APP_USER = "tenders_api_role"
    }
  }

  tags = local.tags
}

resource "aws_lambda_permission" "apigw_tenders_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tenders_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.backoffice.execution_arn}/*/*"
}

# reference_data_api (module 01) : référentiels countries/categories/
# organizations/diffusion_partnerships. Code source dans
# backend/reference_data_api/, packagé par `make build-reference-data-api-lambda`.

data "archive_file" "lambda_reference_data_api" {
  type        = "zip"
  source_dir  = "${path.module}/build/reference_data_api"
  output_path = "${path.module}/build/reference_data_api.zip"
}

resource "aws_lambda_function" "reference_data_api" {
  function_name = "${local.name_prefix}-reference-data-api"
  role          = aws_iam_role.lambda_reference_data_api.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_reference_data_api.output_path
  source_code_hash = data.archive_file.lambda_reference_data_api.output_base64sha256

  environment {
    variables = {
      DSQL_ENDPOINT = local.dsql_endpoint
      # Rôle Postgres non-admin créé/lié par les migrations 062-064 —
      # jamais dsql:DbConnectAdmin pour cette Lambda (voir iam.tf).
      DSQL_APP_USER = "reference_data_api_role"
    }
  }

  tags = local.tags
}

resource "aws_lambda_permission" "apigw_reference_data_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reference_data_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.backoffice.execution_arn}/*/*"
}

data "archive_file" "lambda_publication_coordinator" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_src/publication_coordinator_stub"
  output_path = "${path.module}/build/publication_coordinator.zip"
}

resource "aws_lambda_function" "publication_coordinator" {
  function_name = "${local.name_prefix}-publication-coordinator"
  role          = aws_iam_role.lambda_publication_coordinator.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 256

  filename         = data.archive_file.lambda_publication_coordinator.output_path
  source_code_hash = data.archive_file.lambda_publication_coordinator.output_base64sha256

  environment {
    variables = {
      DSQL_ENDPOINT    = local.dsql_endpoint
      MANIFESTS_BUCKET = aws_s3_bucket.manifests.bucket
    }
  }

  tags = local.tags
}
