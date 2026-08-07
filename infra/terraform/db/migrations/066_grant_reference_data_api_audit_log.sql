-- Droits de reference_data_api_role sur audit_log — jamais accordés
-- jusqu'ici (le GRANT initial, 064, ne couvrait que countries, categories,
-- organizations, diffusion_partnerships, users). reference_data.py::
-- _write_audit et auth.py::maybe_log_login écrivent tous deux dans
-- audit_log ; sans ce GRANT, toute création/modification de référentiel
-- échoue avec psycopg2.errors.InsufficientPrivilege (bug réel constaté le
-- 2026-08-07, même classe d'erreur que 065 pour tenders_api_role).
GRANT SELECT, INSERT ON audit_log TO reference_data_api_role;
