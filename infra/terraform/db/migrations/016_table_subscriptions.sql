-- 8. ABONNEMENTS — droits d'accès achetés (paiement séparé, cf. table payments)
CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscriber_id   UUID NOT NULL,
    plan_id         UUID NOT NULL,
    status          TEXT NOT NULL CHECK (status IN
                        ('PENDING_PAYMENT', 'ACTIVE', 'EXPIRED', 'CANCELLED', 'SUSPENDED')),
    price_paid      NUMERIC(12,2) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'XOF',
    started_at      TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
