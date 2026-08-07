-- Rôle Postgres non-admin dédié à la Lambda users_api (module 13).
-- Connexion IAM (dsql:DbConnect, pas DbConnectAdmin) — même mécanisme que
-- tenders_api_role (058-061) et reference_data_api_role (062-064).
CREATE ROLE users_api_role WITH LOGIN;
