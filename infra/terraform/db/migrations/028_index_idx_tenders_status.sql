-- Filtrage multi-critères combinable (raison du choix DSQL)
CREATE INDEX idx_tenders_status ON tenders (status);
