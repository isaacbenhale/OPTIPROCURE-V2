# Module 01 — Référentiels admin (organisations, catégories, pays, partenariats)

> CRUD des référentiels (pays, catégories, organisations, partenariats de diffusion) — sans eux, aucun AO réel ne peut être créé. **Fait et déployé.**

## Objectif

Le module 3 (`backend/tenders_api/`) valide déjà l'existence de `organization_id`, `country_id` et `category_ids` avant tout create/update d'AO (`tenders.validate_references`), mais **rien ne permet de créer ou gérer ces référentiels** — les tables `organizations`, `categories`, `countries`, `diffusion_partnerships` n'ont aucune route API. Sans ce module, un AGENT ne peut créer aucun AO réel (aucun `organization_id`/`category_id` valide n'existe en base).

## Références

- `infra/terraform/db/migrations/003_table_countries.sql`, `004_table_categories.sql`, `006_table_organizations.sql`, `009_table_diffusion_partnerships.sql`
- CLAUDE.md §"Vue d'ensemble" (Lambda métier applique les autorisations), PRD §3.7 (back-office admin), VISION.md §"Circuits de diffusion formalisés" pour le sens métier de `diffusion_partnerships`

## Dépendances

Module 3 (Lambda `tenders_api`, pattern d'auth/permissions/db à réutiliser).

## Périmètre

**Dans le périmètre :**
- CRUD `countries` (référentiel simple, probablement peu volatil — seed initial + gestion ADMIN)
- CRUD `categories` (hiérarchique via `parent_id`, gestion des slugs, activation/désactivation)
- CRUD `organizations` (ADMIN uniquement — PUBLIC_BODY/PRIVATE_PARTNER/DONOR/AGGREGATOR)
- CRUD `diffusion_partnerships` (ADMIN uniquement — statut ACTIVE/SUSPENDED/EXPIRED/TERMINATED, lien vers `organization_id`)

**Hors périmètre :**
- Upload du document de convention (`diffusion_partnerships.document_s3_key`) — dépend du mécanisme S3 posé par le module 02, à réutiliser une fois écrit plutôt que dupliqué ici.

## À construire

- Nouvelle Lambda (ex. `backend/reference_data_api/`) ou extension de `backend/tenders_api/` avec de nouvelles routes — **à trancher** (voir ci-dessous), mais dans les deux cas : réutiliser `db.py`/`auth.py` (copier ou factoriser, à trancher aussi).
- Routes : `GET/POST /countries`, `GET/POST/PUT /categories`, `GET/POST/PUT /categories/{id}` (activation), `GET/POST/PUT /organizations`, `GET/POST/PUT /diffusion-partnerships`.
- Permissions : lecture (GET) ouverte à AGENT/REVIEWER/ADMIN (nécessaire pour les formulaires de création d'AO) ; écriture réservée à ADMIN (cohérent avec PRD §3.7 "Gestion complète... " côté admin).
- IAM : nouveau rôle Postgres non-admin si nouvelle Lambda séparée (même mécanisme que `tenders_api_role`, migrations à créer), ou extension des GRANT existants sur `tenders_api_role` si la même Lambda est étendue.
- Migration de seed initiale pour `countries` (au moins le Togo — voir PRD §10) — sans seed, impossible de créer un AO en environnement de test.

## Points à trancher avant de coder

1. **Lambda séparée ou extension de `tenders_api` ?** Une Lambda dédiée respecte mieux le principe de responsabilité unique et isole le risque (permissions d'écriture sur les référentiels ≠ permissions sur les AO), mais duplique `db.py`/`auth.py`. Étendre `tenders_api` évite la duplication mais mélange deux domaines métier dans un seul handler. Recommandation par défaut : Lambda séparée si le volume de code dépasse ~200 lignes, sinon extension — à confirmer avec l'utilisateur au moment de coder.
2. **Factorisation `db.py`/`auth.py`** : si Lambda séparée, ces deux fichiers sont identiques à ceux de `tenders_api`. Les dupliquer (simple, cohérent avec "pas d'abstraction prématurée") ou créer un Lambda Layer partagé (plus propre à moyen terme, plus de cérémonie Terraform) — à trancher quand le nombre de Lambdas Python dépassera 2-3.

## Définition de "terminé"

- Un ADMIN peut créer un pays, une catégorie (avec hiérarchie), une organisation et un partenariat via l'API.
- Un AGENT peut lister ces référentiels (lecture seule) pour peupler un formulaire de création d'AO.
- `tenders.create_tender` fonctionne de bout en bout avec de vraies références (test d'intégration manuel).
- Tests unitaires niveau 1/2 sur les permissions (écriture refusée à AGENT/REVIEWER) et la hiérarchie de catégories (parent_id valide).
