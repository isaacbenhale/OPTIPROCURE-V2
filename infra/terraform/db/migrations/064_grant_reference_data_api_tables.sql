-- Droits de reference_data_api_role — référentiels gérés par ce module
-- (module 01) + users pour le provisioning JIT (même pattern que
-- tenders_api, voir backend/reference_data_api/auth.py).
GRANT SELECT, INSERT, UPDATE ON countries, categories, organizations, diffusion_partnerships, users TO reference_data_api_role;
