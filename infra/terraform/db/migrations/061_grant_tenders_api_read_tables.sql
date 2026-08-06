-- Droits de lecture seule sur les référentiels (pas de FK -> tenders_api
-- valide l'existence de ces UUID par SELECT avant tout INSERT/UPDATE).
GRANT SELECT ON countries, categories, organizations TO tenders_api_role;
