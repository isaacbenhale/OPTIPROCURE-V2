-- 3. CATÉGORIES — classification hiérarchique des secteurs d'AO
CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id       UUID,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);
