-- 9. PAIEMENTS — transactions mobile money, idempotence via provider_reference
CREATE TABLE payments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscriber_id       UUID NOT NULL,
    subscription_id     UUID,
    provider            TEXT NOT NULL,
    provider_reference  TEXT NOT NULL UNIQUE,
    amount              NUMERIC(12,2) NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'XOF',
    status              TEXT NOT NULL CHECK (status IN
                            ('PENDING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'REFUNDED')),
    failure_reason      TEXT,
    paid_at             TIMESTAMPTZ,
    refunded_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
