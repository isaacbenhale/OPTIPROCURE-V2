-- 15. BATCHES DE PUBLICATION — suivi du Publication Coordinator
CREATE TABLE publication_batches (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id            TEXT NOT NULL UNIQUE,
    status              TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN
                            ('PENDING', 'RUNNING', 'PARTIALLY_SUCCEEDED', 'SUCCEEDED', 'FAILED')),
    window_start        TIMESTAMPTZ NOT NULL,
    window_end          TIMESTAMPTZ NOT NULL,
    manifest_s3_key     TEXT,
    tenders_created     INT DEFAULT 0,
    tenders_modified    INT DEFAULT 0,
    tenders_expired     INT DEFAULT 0,
    tenders_deleted     INT DEFAULT 0,
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);
