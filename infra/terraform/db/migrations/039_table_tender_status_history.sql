-- 13. HISTORIQUE DES STATUTS D'AO — reconstruit le parcours d'un AO
CREATE TABLE tender_status_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id       UUID NOT NULL,
    from_status     TEXT,
    to_status       TEXT NOT NULL,
    changed_by      UUID,
    actor_type      TEXT NOT NULL DEFAULT 'USER' CHECK (actor_type IN ('USER', 'SYSTEM', 'PIPELINE')),
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
