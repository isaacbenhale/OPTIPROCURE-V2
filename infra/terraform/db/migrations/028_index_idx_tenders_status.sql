-- Filtrage multi-critères combinable (raison du choix DSQL)
CREATE INDEX ASYNC idx_tenders_status ON tenders (status);
