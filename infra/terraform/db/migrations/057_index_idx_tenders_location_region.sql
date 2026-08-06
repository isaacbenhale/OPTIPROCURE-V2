-- Filtrage par zone géographique détaillée (PRD §3.4)
CREATE INDEX ASYNC idx_tenders_location_region ON tenders (location_region);
