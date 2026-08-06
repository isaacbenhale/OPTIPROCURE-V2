-- 16. ÉLÉMENTS DES BATCHES — un AO par ligne, reprise idempotente au niveau item
CREATE TABLE publication_batch_items (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_batch_id    UUID NOT NULL,
    tender_id               UUID NOT NULL,
    action                  TEXT NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'EXPIRE', 'DELETE')),
    status                  TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN
                                ('PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED', 'SKIPPED')),
    error_message           TEXT,
    retry_count             INT NOT NULL DEFAULT 0,
    processed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (publication_batch_id, tender_id)
);
