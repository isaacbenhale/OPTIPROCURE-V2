# =====================================================================
# API Gateway — API Gateway valide les JWT Cognito, Lambda applique les
# autorisations métier fines (CLAUDE.md, principe d'architecture)
# =====================================================================

resource "aws_apigatewayv2_api" "backoffice" {
  name          = "${local.name_prefix}-backoffice-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.cognito_callback_urls
    allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
  }

  tags = local.tags
}

resource "aws_apigatewayv2_authorizer" "cognito_jwt" {
  api_id           = aws_apigatewayv2_api.backoffice.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-cognito-jwt"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.backoffice_spa.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.backoffice.id}"
  }
}

resource "aws_apigatewayv2_integration" "tenders_api" {
  api_id                 = aws_apigatewayv2_api.backoffice.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.tenders_api.invoke_arn
  payload_format_version = "2.0"
}

# Routes CRUD + workflow des AO (module 3, backend/tenders_api) — toutes
# protégées par le même JWT Authorizer, routées par event["routeKey"] dans
# la Lambda (voir backend/tenders_api/handler.py). QUEUED_FOR_PUBLICATION,
# PUBLISHED, EXPIRED n'ont volontairement aucune route ici : pilotés par
# le Publication Coordinator (module 5).
locals {
  tenders_api_routes = toset([
    "GET /tenders",
    "POST /tenders",
    "GET /tenders/{id}",
    "PUT /tenders/{id}",
    "DELETE /tenders/{id}",
    "POST /tenders/{id}/submit",
    "POST /tenders/{id}/return",
    "POST /tenders/{id}/endorse",
    "POST /tenders/{id}/approve",
    "POST /tenders/{id}/reject",
    "POST /tenders/{id}/archive",
    "GET /tenders/{id}/history",
    "GET /me",
  ])
}

resource "aws_apigatewayv2_route" "tenders_api" {
  for_each = local.tenders_api_routes

  api_id             = aws_apigatewayv2_api.backoffice.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.tenders_api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_jwt.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.backoffice.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      integrationError = "$context.integration.error"
    })
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-backoffice-api"
  retention_in_days = 90
  tags              = local.tags
}

output "api_gateway_endpoint" {
  value = aws_apigatewayv2_stage.default.invoke_url
}
