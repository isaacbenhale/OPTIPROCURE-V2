-- 5. CONVENTIONS DE DIFFUSION — état des partenariats privés (pas le contrat lui-même)
CREATE TABLE diffusion_partnerships (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id       UUID NOT NULL,
    convention_reference  TEXT NOT NULL UNIQUE,
    signed_at             DATE NOT NULL,
    valid_from            DATE NOT NULL,
    valid_until           DATE,
    status                TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUSPENDED', 'EXPIRED', 'TERMINATED')),
    document_s3_key       TEXT,
    notes                 TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
