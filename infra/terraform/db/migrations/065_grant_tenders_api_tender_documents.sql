-- Droits de tenders_api_role sur tender_documents (module 02, jamais
-- accordés jusqu'ici — le rôle initial (060) ne couvrait que tenders,
-- tender_categories, tender_status_history, audit_log, users).
GRANT SELECT, INSERT, UPDATE ON tender_documents TO tenders_api_role;
