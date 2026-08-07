-- Droits de users_api_role — comptes internes (module 13) + audit_log.
-- audit_log inclus dès ce premier GRANT (pas en migration de rattrapage
-- comme 066 pour reference_data_api_role) : _write_audit y écrit à chaque
-- création/changement de groupes/activation, voir
-- docs/LECONS-APPRISES-AWS-SERVERLESS.md §13.
GRANT SELECT, INSERT, UPDATE ON users, audit_log TO users_api_role;
