# Infrastructure OptiProcure — Terraform

Crée l'ensemble du backend AWS décrit dans `CLAUDE.md` : Aurora DSQL, Cognito (back-office), API Gateway + Lambda, S3 + CloudFront (portail public), EventBridge Scheduler, fédération OIDC GitHub. Le schéma SQL (`db/migrations/`) est ensuite exécuté automatiquement contre le cluster via une Lambda dédiée.

## Prérequis

- Terraform >= 1.9
- Docker (pour construire le paquet Lambda `psycopg2-binary`, voir `Makefile`)
- Un compte AWS avec les droits nécessaires (Cognito, DSQL, Lambda, API Gateway, S3, CloudFront, EventBridge Scheduler, IAM)

## Étapes

```bash
cp terraform.tfvars.example terraform.tfvars
# éditer terraform.tfvars : github_org, github_repo, région, etc.

make build-all        # vendorise psycopg2-binary pour la Lambda de migration

terraform init
terraform plan
terraform apply
```

`terraform apply` crée toute l'infrastructure **et** exécute le schéma SQL : la ressource `aws_lambda_invocation.run_migrations` (dans `lambda_migrate.tf`) invoque la Lambda de migration après l'upload des 53 fichiers de `db/migrations/` dans S3. Elle ne se redéclenche que si le contenu de ces fichiers change (hash en `triggers`), donc un `apply` sans changement de schéma ne relance rien.

## Ordre logique des ressources

1. `dsql.tf` — cluster Aurora DSQL
2. `cognito.tf` — User Pool back-office + groupes AGENT/REVIEWER/ADMIN
3. `iam.tf` — rôles Lambda à privilèges minimaux
4. `s3_cloudfront.tf` — buckets (site public, manifestes, documents, migrations) + distribution CloudFront
5. `lambda_migrate.tf` — packaging + upload + **exécution du schéma SQL**
6. `lambda_api.tf` — Lambda tenders-api (placeholder module 3) et Publication Coordinator (placeholder module 5)
7. `api_gateway.tf` — HTTP API + autorizer JWT Cognito
8. `eventbridge.tf` — planification du batch quotidien
9. `github_oidc.tf` — rôle assumable par GitHub Actions pour le déploiement du frontend

## Ce qui reste des placeholders

- `lambda_src/tenders_api/handler.py` — à remplacer par le vrai CRUD des AO (module 3 du plan de développement).
- `lambda_src/publication_coordinator_stub/handler.py` — à remplacer par la vraie détection de changements + génération de manifeste (module 5).

Ces deux Lambdas sont déployées dès maintenant comme coquilles fonctionnelles pour que le reste de l'infra (routes API Gateway, planification EventBridge) soit déjà en place quand ces modules seront codés.

## Ce qui n'est pas encore couvert

- Portail public Next.js et pipeline GitHub Actions de build (le rôle IAM `github_actions_deploy` est prêt, le workflow `.github/workflows/*.yml` reste à écrire).
- Passerelle de paiement (mobile money / carte bancaire).
- Service d'envoi d'alertes email/SMS (SES/SNS).
- Certificat ACM + domaine personnalisé sur CloudFront (`public_site_domain` est prévu en variable mais pas encore câblé).
