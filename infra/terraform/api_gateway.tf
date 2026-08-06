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

# Route protégée type — les routes réelles du module 3 (CRUD complet des
# AO) remplaceront/complèteront celle-ci.
resource "aws_apigatewayv2_route" "tenders_list" {
  api_id             = aws_apigatewayv2_api.backoffice.id
  route_key          = "GET /tenders"
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
