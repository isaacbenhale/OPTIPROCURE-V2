-- Filtrage par type de procédure (PRD §3.4)
CREATE INDEX idx_tenders_procedure_type ON tenders (procedure_type);
