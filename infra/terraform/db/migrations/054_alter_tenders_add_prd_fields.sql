-- Extension de tenders — champs PRD §3.2 absents du schéma initial (module 3)
-- Pas de CHECK inline ici : DSQL ne supporte pas "ALTER TABLE ADD COLUMN
-- ... CHECK" (contrairement à CREATE TABLE) — voir 062/063 pour les
-- contraintes CHECK ajoutées séparément via ADD CONSTRAINT.
ALTER TABLE tenders
    ADD COLUMN procurement_type    TEXT,
    ADD COLUMN procedure_type      TEXT,
    ADD COLUMN location_region     TEXT,
    ADD COLUMN location_city       TEXT,
    ADD COLUMN eligibility_criteria TEXT,
    ADD COLUMN required_documents  TEXT,
    ADD COLUMN contact_name        TEXT,
    ADD COLUMN contact_role        TEXT,
    ADD COLUMN contact_email       TEXT,
    ADD COLUMN contact_phone       TEXT;
