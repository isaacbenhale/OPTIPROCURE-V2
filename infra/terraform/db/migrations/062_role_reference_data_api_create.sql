-- Rôle Postgres non-admin dédié à la Lambda reference_data_api (module 01).
-- Connexion IAM (dsql:DbConnect, pas DbConnectAdmin) — même mécanisme que
-- tenders_api_role (058-061).
CREATE ROLE reference_data_api_role WITH LOGIN;
