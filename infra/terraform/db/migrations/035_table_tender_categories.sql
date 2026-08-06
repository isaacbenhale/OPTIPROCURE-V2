-- 11. LIAISON AO <-> CATÉGORIES — many-to-many
CREATE TABLE tender_categories (
    tender_id       UUID NOT NULL,
    category_id     UUID NOT NULL,
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (tender_id, category_id)
);
