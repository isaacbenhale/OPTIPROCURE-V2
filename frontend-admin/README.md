# OptiProcure — Back-office (`frontend-admin`)

SPA React + Vite + TypeScript pour AGENT/REVIEWER/ADMIN — workflow des AO (module 3), documents joints (module 02), référentiels en lecture (module 01). Authentification Cognito Hosted UI (Authorization Code + PKCE).

## Développement local

```bash
npm install
cp .env.example .env   # renseigner les valeurs réelles (voir infra/terraform/OUTPUTS.md)
npm run dev
```

`.env` :
- `VITE_API_BASE_URL` → `terraform output api_gateway_endpoint`
- `VITE_COGNITO_DOMAIN` → `terraform output cognito_hosted_ui_domain`
- `VITE_COGNITO_CLIENT_ID` → `terraform output cognito_user_pool_client_id`
- `VITE_REDIRECT_URI` / `VITE_LOGOUT_URI` → doivent figurer dans `cognito_callback_urls`/`cognito_logout_urls` (`terraform.tfvars`)

## Build et déploiement

Pas encore de CI (module 06) — déploiement manuel :

```bash
npm run build
aws s3 sync dist/ s3://$(terraform -chdir=../infra/terraform output -raw admin_site_bucket_name) --delete
aws cloudfront create-invalidation \
  --distribution-id $(terraform -chdir=../infra/terraform output -raw admin_cloudfront_distribution_id) \
  --paths "/*"
```

Après le premier déploiement, ajouter l'URL CloudFront réelle à `cognito_callback_urls`/`cognito_logout_urls` dans `terraform.tfvars` et ré-appliquer (bootstrap classique d'une app OAuth).

## Périmètre

Voir `../tasks/03-frontend-admin-backoffice.md`. Gestion des référentiels (créer un pays/une catégorie/une organisation) et statistiques/audit ADMIN volontairement hors périmètre de cette passe.
