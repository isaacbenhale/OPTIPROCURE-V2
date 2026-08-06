-- 2. PAYS — référentiel géographique partagé (organisations, abonnés, AO)
CREATE TABLE countries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iso_code        TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL
);
