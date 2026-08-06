-- 10. APPELS D'OFFRES — entité centrale, du brouillon à la publication/expiration
CREATE TABLE tenders (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_number    TEXT,                   -- unique par organisation, cf. index plus bas
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    sector              TEXT NOT NULL CHECK (sector IN ('PUBLIC', 'PRIVATE')),
    organization_id     UUID NOT NULL,
    country_id          UUID NOT NULL,
    source_name         TEXT,
    source_url          TEXT,
    status              TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN
                            ('DRAFT', 'PENDING_REVIEW', 'REVISION_REQUESTED', 'APPROVED',
                             'QUEUED_FOR_PUBLICATION', 'PUBLISHED', 'EXPIRED', 'REJECTED', 'ARCHIVED')),
    estimated_budget    NUMERIC(14,2),
    currency            TEXT DEFAULT 'XOF',
    publication_date    TIMESTAMPTZ,
    submission_deadline TIMESTAMPTZ NOT NULL,
    expired_at          TIMESTAMPTZ,
    created_by          UUID NOT NULL,
    reviewed_by         UUID,
    approved_by         UUID,
    content_hash        TEXT,                   -- détection de changements pour le pipeline de publication
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);
