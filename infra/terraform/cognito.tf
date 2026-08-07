# =====================================================================
# Amazon Cognito — source d'identité unique du back-office (CLAUDE.md §4)
# =====================================================================
# Le portail public n'a pas de User Pool ici : la création de compte
# abonné en libre-service (PRD §3.6) est un module applicatif séparé,
# à traiter avec sa propre logique métier (pas d'authentification back-office).

resource "aws_cognito_user_pool" "backoffice" {
  name = "${local.name_prefix}-backoffice"

  mfa_configuration = var.cognito_mfa_configuration

  software_token_mfa_configuration {
    enabled = true
  }

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  auto_verified_attributes = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = true # pas d'auto-inscription côté back-office
  }

  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false
  }

  tags = local.tags
}

resource "aws_cognito_user_pool_domain" "backoffice" {
  domain       = "${local.name_prefix}-backoffice"
  user_pool_id = aws_cognito_user_pool.backoffice.id
}

resource "aws_cognito_user_pool_client" "backoffice_spa" {
  name         = "${local.name_prefix}-backoffice-spa"
  user_pool_id = aws_cognito_user_pool.backoffice.id

  generate_secret = false # client SPA public, flux PKCE

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  # aws.cognito.signin.user.admin : sans ce scope, l'access token émis par le
  # flux Hosted UI (Authorization Code + PKCE) ne peut pas s'auto-interroger
  # via cognito-idp:GetUser (auth.py::fetch_cognito_user_info) — Cognito
  # rejette alors l'appel avec NotAuthorizedException "Access Token does not
  # have required scopes", même si le token est par ailleurs valide et bien
  # signé (bug réel constaté le 2026-08-07 : un token SRP direct, non soumis
  # à cette restriction de scope OAuth, fonctionnait alors que le token émis
  # par le vrai parcours de connexion du navigateur échouait systématiquement).
  # Pas de "email"/"profile" : Cognito rejette (invalid_scope) la combinaison
  # des 4 scopes ensemble alors que 3 quelconques passent (limite Hosted UI
  # constatée empiriquement le 2026-08-07) — et le frontend n'en a de toute
  # façon pas besoin, voir le commentaire équivalent dans auth/cognito.ts.
  allowed_oauth_scopes = ["openid", "aws.cognito.signin.user.admin"]

  supported_identity_providers = ["COGNITO"]

  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  access_token_validity  = 15 # minutes — jetons courts (CLAUDE.md §4.3)
  id_token_validity      = 15
  refresh_token_validity = 12 # heures

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "hours"
  }

  prevent_user_existence_errors = "ENABLED"
}

# --- Groupes = modèle de rôles (PRD §2.2 / CLAUDE.md) ------------------
# La précédence la plus basse gagne en cas d'appartenance à plusieurs groupes.

resource "aws_cognito_user_group" "admin" {
  name         = "ADMIN"
  user_pool_id = aws_cognito_user_pool.backoffice.id
  description  = "Approuve les AO, supervise les batches, traite les exceptions. MFA obligatoire."
  precedence   = 1
}

resource "aws_cognito_user_group" "reviewer" {
  name         = "REVIEWER"
  user_pool_id = aws_cognito_user_pool.backoffice.id
  description  = "Révise, commente et retourne un AO. Ne gère pas les utilisateurs."
  precedence   = 2
}

resource "aws_cognito_user_group" "agent" {
  name         = "AGENT"
  user_pool_id = aws_cognito_user_pool.backoffice.id
  description  = "Crée et modifie ses brouillons, soumet à révision. Ne peut ni approuver ni publier."
  precedence   = 3
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.backoffice.id
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.backoffice_spa.id
}

output "cognito_issuer_url" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.backoffice.id}"
}

# URL de base du Hosted UI Cognito (module 03) — /oauth2/authorize,
# /oauth2/token, /logout. Consommée par frontend-admin/.env (VITE_COGNITO_DOMAIN).
output "cognito_hosted_ui_domain" {
  value = "https://${aws_cognito_user_pool_domain.backoffice.domain}.auth.${var.aws_region}.amazoncognito.com"
}
