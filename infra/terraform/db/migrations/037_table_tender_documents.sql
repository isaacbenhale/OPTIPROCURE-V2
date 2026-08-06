-- 12. DOCUMENTS JOINTS — métadonnées seulement, fichiers sur S3
CREATE TABLE tender_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id       UUID NOT NULL,
    file_name       TEXT NOT NULL,
    s3_key          TEXT NOT NULL,
    content_type    TEXT,
    size_bytes      BIGINT,
    uploaded_by     UUID NOT NULL,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
