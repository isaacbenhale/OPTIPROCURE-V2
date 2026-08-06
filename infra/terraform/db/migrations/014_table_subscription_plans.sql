-- 7. PLANS D'ABONNEMENT — catalogue commercial (Découverte/Standard/Premium)
CREATE TABLE subscription_plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    price_amount    NUMERIC(12,2) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'XOF',
    duration_days   INT NOT NULL,
    features        JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
