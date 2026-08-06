-- Filtrage par type de marché (PRD §3.4)
CREATE INDEX idx_tenders_procurement_type ON tenders (procurement_type);
