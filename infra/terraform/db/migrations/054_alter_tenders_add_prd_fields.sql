-- Extension de tenders — champs PRD §3.2 absents du schéma initial (module 3)
ALTER TABLE tenders
    ADD COLUMN procurement_type    TEXT CHECK (procurement_type IN
                                        ('TRAVAUX', 'FOURNITURES', 'SERVICES', 'PRESTATIONS_INTELLECTUELLES')),
    ADD COLUMN procedure_type      TEXT CHECK (procedure_type IN
                                        ('OUVERT', 'RESTREINT', 'GRE_A_GRE', 'CONSULTATION', 'CONCOURS')),
    ADD COLUMN location_region     TEXT,
    ADD COLUMN location_city       TEXT,
    ADD COLUMN eligibility_criteria TEXT,
    ADD COLUMN required_documents  TEXT,
    ADD COLUMN contact_name        TEXT,
    ADD COLUMN contact_role        TEXT,
    ADD COLUMN contact_email       TEXT,
    ADD COLUMN contact_phone       TEXT;
