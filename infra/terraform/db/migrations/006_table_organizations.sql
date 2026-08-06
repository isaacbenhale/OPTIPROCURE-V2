-- 4. ORGANISATIONS — émetteurs d'AO (publics, partenaires privés, bailleurs, agrégateurs)
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    org_type        TEXT NOT NULL CHECK (org_type IN
                        ('PUBLIC_BODY', 'PRIVATE_PARTNER', 'DONOR', 'AGGREGATOR')),
    country_id      UUID,
    website         TEXT,
    contact_email   TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
