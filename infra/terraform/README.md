# Infrastructure OptiProcure — Terraform

Crée l'ensemble du backend AWS décrit dans `CLAUDE.md` : Aurora DSQL, Cognito (back-office), API Gateway + Lambda, S3 + CloudFront (portail public), EventBridge Scheduler, fédération OIDC GitHub. Le schéma SQL (`db/migrations/`) est ensuite exécuté automatiquement contre le cluster via une Lambda dédiée.

## Prérequis

- Terraform >= 1.9
- Docker (pour construire les paquets Lambda `psycopg2-binary`, voir `Makefile`)
- Un compte AWS avec les droits nécessaires (Cognito, DSQL, Lambda, API Gateway, S3, CloudFront, EventBridge Scheduler, IAM)

## Étapes

```bash
cp terraform.tfvars.example terraform.tfvars
# éditer terraform.tfvars : github_org, github_repo, région, etc.

make build-all        # vendorise psycopg2-binary pour les Lambdas migrate + tenders_api

terraform init
terraform plan
terraform apply
```

`terraform apply` crée toute l'infrastructure **et** exécute le schéma SQL : la ressource `aws_lambda_invocation.run_migrations` (dans `lambda_migrate.tf`) invoque la Lambda de migration après l'upload des 61 fichiers de `db/migrations/` dans S3. Elle ne se redéclenche que si le contenu de ces fichiers change (hash en `triggers`), donc un `apply` sans changement de schéma ne relance rien.

## Ordre logique des ressources

1. `dsql.tf` — cluster Aurora DSQL
2. `cognito.tf` — User Pool back-office + groupes AGENT/REVIEWER/ADMIN
3. `iam.tf` — rôles Lambda à privilèges minimaux
4. `s3_cloudfront.tf` — buckets (site public, manifestes, documents, migrations) + distribution CloudFront
5. `lambda_migrate.tf` — packaging + upload + **exécution du schéma SQL** (dont le rôle Postgres non-admin `tenders_api_role`, migrations 058-061)
6. `lambda_api.tf` — Lambda tenders-api (module 3, code réel dans `../../backend/tenders_api/`) et Publication Coordinator (encore un placeholder, module 5)
7. `api_gateway.tf` — HTTP API + autorizer JWT Cognito + 12 routes CRUD/workflow des AO
8. `eventbridge.tf` — planification du batch quotidien
9. `github_oidc.tf` — rôle assumable par GitHub Actions pour le déploiement du frontend

## Ce qui reste un placeholder

- `lambda_src/publication_coordinator_stub/handler.py` — à remplacer par la vraie détection de changements + génération de manifeste (module 5).

`tenders_api` (module 3) est implémenté : CRUD des AO + workflow de statuts DRAFT→PENDING_REVIEW→REVISION_REQUESTED/APPROVED/REJECTED, archivage manuel EXPIRED→ARCHIVED. L'upload de documents joints (`tender_documents`/S3) et les transitions QUEUED_FOR_PUBLICATION/PUBLISHED/EXPIRED (pilotées par le Publication Coordinator) restent hors périmètre de cette Lambda — voir `../../backend/tenders_api/`.

## Ce qui n'est pas encore couvert

- Portail public Next.js et pipeline GitHub Actions de build (le rôle IAM `github_actions_deploy` est prêt, le workflow `.github/workflows/*.yml` reste à écrire).
- Passerelle de paiement (mobile money / carte bancaire).
- Service d'envoi d'alertes email/SMS (SES/SNS).
- Certificat ACM + domaine personnalisé sur CloudFront (`public_site_domain` est prévu en variable mais pas encore câblé).
