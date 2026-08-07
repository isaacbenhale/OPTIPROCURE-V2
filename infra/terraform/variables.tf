variable "project_name" {
  description = "Nom court du projet, utilisé comme préfixe des ressources"
  type        = string
  default     = "optiprocure"
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Région AWS cible. Vérifier la disponibilité d'Aurora DSQL dans la région choisie avant de changer cette valeur (service en expansion rapide)."
  type        = string
  default     = "us-east-1"
}

variable "dsql_deletion_protection" {
  description = "Active la protection contre la suppression du cluster Aurora DSQL (recommandé pour prod)"
  type        = bool
  default     = false
}

variable "cognito_mfa_configuration" {
  description = "Configuration MFA du User Pool Cognito : OFF, ON ou OPTIONAL"
  type        = string
  default     = "OPTIONAL" # passer à ON en prod pour rendre le MFA obligatoire à l'échelle du pool
}

variable "cognito_callback_urls" {
  description = "URLs de redirection autorisées après authentification (portail privé / back-office)"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
}

variable "cognito_logout_urls" {
  description = "URLs de redirection autorisées après déconnexion"
  type        = list(string)
  default     = ["http://localhost:3000/logout"]
}

variable "public_site_domain" {
  description = "Nom de domaine du portail public (ex. optiprocure.pro). Laisser vide pour utiliser uniquement le domaine CloudFront par défaut au démarrage."
  type        = string
  default     = ""
}

variable "github_org" {
  description = "Organisation ou compte GitHub propriétaire du repo (pour la fédération OIDC)"
  type        = string
}

variable "github_repo" {
  description = "Nom du repo GitHub (pour la fédération OIDC), sans l'organisation"
  type        = string
}

variable "github_allowed_branches" {
  description = "Branches autorisées à assumer le rôle de déploiement via OIDC"
  type        = list(string)
  default     = ["main"]
}

variable "publication_batch_schedule" {
  description = "Expression EventBridge Scheduler pour le batch de publication quotidien"
  type        = string
  default     = "cron(0 2 * * ? *)" # 02h00 UTC chaque jour
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  # CORS attend une ORIGINE (scheme://host[:port]), jamais un chemin —
  # contrairement à cognito_callback_urls qui contient "/callback" (requis
  # par Cognito). Sans ce strip, le navigateur envoie "Origin: https://host"
  # (jamais avec le chemin) et API Gateway ne matche jamais rien : aucun
  # en-tête Access-Control-Allow-Origin renvoyé, la SPA ne peut lire aucune
  # réponse de l'API (bug réel observé le 2026-08-07 : boucle infinie
  # login/callback côté frontend-admin, GET /me silencieusement bloqué).
  cors_allowed_origins = distinct([for url in var.cognito_callback_urls : regex("^[a-zA-Z]+://[^/]+", url)])
}
