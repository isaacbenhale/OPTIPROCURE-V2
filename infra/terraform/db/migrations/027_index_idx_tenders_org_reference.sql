-- reference_number unique par organisation, pas globalement
CREATE UNIQUE INDEX ASYNC idx_tenders_org_reference ON tenders (organization_id, reference_number);
