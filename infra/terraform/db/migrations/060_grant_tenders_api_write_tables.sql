-- Droits d'écriture métier de tenders_api_role — jamais dsql:DbConnectAdmin
-- pour cette Lambda (voir iam.tf : dsql:DbConnect uniquement).
GRANT SELECT, INSERT, UPDATE ON tenders, tender_categories, tender_status_history, audit_log, users TO tenders_api_role;
