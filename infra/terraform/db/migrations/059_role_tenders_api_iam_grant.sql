-- Liaison du rôle Postgres tenders_api_role au rôle IAM lambda_tenders_api,
-- pour que generate_db_connect_auth_token (non-admin) fonctionne pour cette
-- Lambda. Le placeholder ci-dessous est substitué à l'exécution par la
-- Lambda de migration (variable d'environnement TENDERS_API_ROLE_ARN,
-- voir infra/terraform/lambda_migrate.tf) — ne jamais coder l'ARN en dur
-- ici, il dépend du compte/région. Syntaxe "AWS IAM GRANT" à revérifier
-- contre la doc AWS DSQL au moment du déploiement (cf. 058).
AWS IAM GRANT tenders_api_role TO '__TENDERS_API_ROLE_ARN__';
