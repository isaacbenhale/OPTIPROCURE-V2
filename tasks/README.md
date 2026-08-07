# Découpage des modules restants — OptiProcure

Index de travail pour construire l'application complète décrite dans `docs/PRD.md` / `docs/VISION.md`, dans le cadre technique de `CLAUDE.md`. Chaque fichier de ce dossier est une spec de module, suffisamment précise pour être exécutée directement (comme le plan qui a servi à coder le module 3) — à lire et suivre au moment de coder ce module, pas avant.

## État actuel

Fait (infra AWS complète + module 3) :
- Terraform : Cognito, API Gateway, Aurora DSQL, S3+CloudFront, EventBridge, OIDC GitHub (`infra/terraform/`)
- Schéma DB : 61 migrations (`infra/terraform/db/migrations/`)
- **Module 3** — `backend/tenders_api/` : CRUD + workflow de statuts des AO (DRAFT → PENDING_REVIEW → REVISION_REQUESTED/APPROVED/REJECTED, archivage EXPIRED→ARCHIVED), double contrôle rôle/MFA, audit log, tests

Tout le reste (référentiels, documents joints, back-office UI, publication, portail public, abonnés, paiement, alertes) reste à construire — c'est l'objet des fichiers ci-dessous.

## Ordre recommandé

L'ordre suit les dépendances réelles, pas la numérotation seule — certains modules sont parallélisables (notés ci-dessous).

| # | Module | Dépend de | Peut être fait en parallèle avec |
|---|---|---|---|
| 01 | [Référentiels admin](01-referentiels-admin.md) | Module 3 | — |
| 02 | [Documents joints des AO](02-documents-joints-ao.md) | Module 3 | 01, 03 |
| 03 | [Frontend back-office](03-frontend-admin-backoffice.md) | Module 3, 01 (partiellement) | 02 |
| 04 | [Publication Coordinator](04-publication-coordinator.md) | Module 3 | 01, 02, 03 |
| 05 | [Générateur du portail public](05-generateur-portail-public.md) | Module 04 | — |
| 06 | [Pipeline de déploiement frontend](06-pipeline-deploiement-frontend.md) | Module 05 | — |
| 07 | [Recherche publique](07-recherche-publique.md) | Module 05 | — |
| 08 | [Comptes abonnés](08-comptes-abonnes-authentification.md) | — (indépendant de 01-07) | 01 à 07 |
| 09 | [Abonnements et paiement](09-abonnements-paiement.md) | Module 08 | — |
| 10 | [Alertes et notifications](10-alertes-notifications.md) | Module 08, 09, 04 | — |
| 11 | [Tableau de bord abonné](11-tableau-de-bord-abonne.md) | Module 08, 09 | 10 |
| 12 | [Back-office admin — stats & audit](12-backoffice-admin-stats-audit.md) | Module 03, 09 | 10, 11 |
| 13 | [Gestion des comptes internes](13-gestion-comptes-internes.md) | Module 03 | 04 à 12 |

## Correspondance avec les phases PRD §7

- **Phase 1 (MVP)** : modules 01 à 08 (jusqu'à l'inscription abonné en libre-service), plus une version minimale de 10 (alertes email seules) et le module 13 (sans lui, l'onboarding des AGENT/REVIEWER réels reste bloqué sur un accès AWS CLI/Console).
- **Phase 2 (Consolidation)** : 09 complet, 10 multi-canal, 11, 12.
- **Phase 3 (Extension)** : app mobile, API partenaires, import automatisé — volontairement hors de ce découpage, trop tôt pour spécifier en détail (voir PRD §7 et §12).

## Convention de chaque fichier

Chaque module suit la même structure : **Objectif**, **Références**, **Dépendances**, **Périmètre** (in/out), **À construire**, **Points à trancher avant de coder** (questions d'architecture réellement ouvertes, à poser à l'utilisateur — pas à deviner), **Définition de "terminé"**. Cette dernière section sert de check-list de vérification, sur le modèle de la section "Vérification" du plan du module 3.
