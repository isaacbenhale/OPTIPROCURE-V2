# CLAUDE.md — OptiProcure

Ce fichier donne à Claude (ou tout autre assistant de développement) le contexte technique nécessaire pour travailler sur le code d'OptiProcure. Pour le "pourquoi" produit, voir `PRD.md` et `VISION.md` — ce fichier se concentre sur le "comment" technique et les décisions d'architecture actées.

## Résumé de l'architecture

OptiProcure adopte une **architecture de publication statique et incrémentale**. Le portail public est généré sous forme de fichiers HTML optimisés SEO, distribué par **Amazon S3 + CloudFront**. Aucun serveur Node.js ne reste actif en production : **GitHub Actions** fournit uniquement un runner temporaire pendant les builds.

Le portail privé (back-office) est protégé par **Amazon Cognito**. Chaque agent, réviseur ou administrateur doit s'authentifier avant de créer, modifier, réviser ou approuver un appel d'offres (AO). **API Gateway** valide les JWT émis par Cognito, et **Lambda** applique les autorisations métier fines avant tout accès aux données.

**Principe fondamental à respecter dans tout le code** : cette architecture découple totalement l'identité et la logique métier (Cognito, API Gateway, Lambda, Aurora DSQL) de la génération et de la diffusion du contenu public (GitHub Actions, Next.js, S3, CloudFront). Ce sont deux domaines qui évoluent et se mettent à l'échelle indépendamment — ne pas les recoupler.

## Principes d'architecture (non négociables)

- Amazon Cognito est la **source d'identité unique** du back-office.
- API Gateway protège les API avec un **JWT Authorizer**.
- Lambda reste responsable des règles métier et des autorisations fines (le contrôle des groupes Cognito ne suffit pas seul).
- **Aurora DSQL** (serverless, compatible PostgreSQL) est la source de vérité des AO et des états de publication — choisie pour sa capacité à traiter nativement les recherches multi-critères combinables (secteur, région, montant, date, procédure) sans service de recherche additionnel, avec cohérence forte (ACID) pour abonnements et paiements.
- GitHub Actions exécute les builds sur un **runner éphémère** — jamais de serveur permanent pour le frontend public.
- Le frontend public est servi par **S3 + CloudFront**, généré via Next.js en rendu statique.
- Les **publications de données** et les **déploiements du code frontend** sont deux workflows distincts (voir §4).

## Authentification et autorisation

Le back-office n'est **jamais** accessible de manière anonyme. Cognito gère la connexion, le MFA, les groupes utilisateurs et l'émission des jetons. Le navigateur transmet un access token à chaque appel d'API protégé.

### Modèle de rôles (groupes Cognito)

| Rôle | Droits principaux | Restrictions |
|---|---|---|
| AGENT | Créer et modifier ses brouillons ; soumettre à révision | Ne peut ni approuver ni publier |
| REVIEWER | Réviser, commenter et retourner un AO | Ne gère pas les utilisateurs |
| ADMIN | Approuver, superviser les batches et traiter les exceptions — **et hérite de tous les droits AGENT/REVIEWER** (créer/modifier/soumettre/retourner/endosser n'importe quel AO, y compris ceux qu'il n'a pas créés), jamais l'inverse | MFA obligatoire pour ses actions propres (approuver/rejeter/archiver) ; pas requis pour les actions héritées d'AGENT/REVIEWER |

### Contrôles de sécurité à implémenter

- MFA obligatoire pour ADMIN, recommandé pour AGENT/REVIEWER.
- Jetons courts ; aucun secret permanent conservé dans le navigateur.
- Double contrôle : groupes Cognito **et** permissions métier vérifiées côté Lambda (ne jamais faire confiance au seul JWT/groupe pour une autorisation fine).
- Journalisation systématique : connexions, refus d'accès, modifications, approbations, publications.
- Principe du moindre privilège pour tous les rôles IAM.
- **Fédération OIDC de GitHub vers AWS** pour les déploiements — pas de clés AWS statiques stockées dans GitHub Secrets.

## Workflow de publication (cycle complet)

1. Un **AGENT** authentifié crée un AO (état `brouillon`) et le soumet à révision.
2. Un **REVIEWER** révise, commente, et peut retourner l'AO à l'agent.
3. Un **ADMIN** approuve l'AO.
4. À intervalle planifié (EventBridge Scheduler), le batch de publication détecte la fenêtre de changements survenus depuis le dernier batch **terminé avec succès**.
5. **Aucun build n'est déclenché si aucun AO n'a été créé, modifié ou nouvellement expiré** — ceci élimine tout coût d'infrastructure inutile. Ne pas construire de logique qui déclenche un build inconditionnellement.

## Détection des changements

### Manifeste de publication

Le **Publication Coordinator** produit un manifeste versionné contenant :
- l'identifiant du batch (`batchId`)
- la fenêtre temporelle traitée
- les AO créés, modifiés ou expirés
- les pages de collections affectées
- les fichiers SEO à reconstruire

Le manifeste est stocké dans **S3** ; GitHub Actions ne reçoit que son identifiant — le déclencheur du build doit rester léger et auditable, jamais chargé du détail métier.

### Gestion du curseur

Le curseur de publication n'avance **qu'après le succès** du build, de l'upload S3 et de l'invalidation CloudFront. En cas d'échec, le même intervalle peut être repris sans perdre de changements. **La publication doit être conçue comme idempotente et rejouable** — c'est une contrainte de conception à respecter dans tout code touchant au batch.

### Table de décision changement → action

| Type de changement | Action | Éléments associés |
|---|---|---|
| Nouvel AO approuvé | Créer sa page statique | Listes, catégorie, pays, organisation, sitemap |
| AO modifié | Remplacer sa page | Listes et index affectés |
| AO nouvellement expiré | Reconstruire la page avec statut expiré | Liste active, archives, sitemap |
| Aucun changement | Ne pas lancer GitHub Actions | Aucun coût de build |

## Responsabilités des composants

| Composant | Responsabilité |
|---|---|
| Amazon Cognito | Authentification, MFA, groupes et émission de jetons |
| API Gateway | Validation JWT et exposition contrôlée des API |
| Lambda métier | Règles métier, autorisations fines, approbations et audit |
| Aurora DSQL | Données des AO, statuts, dates et historique |
| EventBridge Scheduler | Déclenchement planifié du batch |
| Publication Coordinator | Détection des changements et création du manifeste |
| GitHub Actions | Runner temporaire et orchestration du build |
| Next.js / générateur Node.js | Génération des pages statiques et des métadonnées SEO |
| Amazon S3 | Stockage des fichiers statiques |
| CloudFront | Cache, HTTPS et distribution mondiale |

## Deux workflows distincts à maintenir

**Ne jamais fusionner ces deux pipelines** :

1. **Publication incrémentale des données** — déclenchée par EventBridge Scheduler. Traite uniquement les AO nouveaux, modifiés ou nouvellement expirés, ainsi que les listes et fichiers SEO directement affectés.
2. **Déploiement complet du frontend** — déclenché par une modification du code Next.js fusionnée dans la branche de production. Exécute un build complet lorsque layouts, styles, composants partagés ou règles SEO changent.

## Gestion des erreurs et reprise

- Le batch possède quatre états : `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`.
- Une publication n'est déclarée réussie qu'**après validation de tous les artefacts**.
- Les fichiers S3 non concernés par un déploiement incrémental **ne doivent jamais être supprimés**.
- Les invalidations CloudFront doivent être **ciblées sur les URL réellement modifiées** (pas d'invalidation globale par défaut).
- Un build complet sert de mécanisme de réconciliation après incident majeur — c'est le filet de sécurité en cas de dérive entre l'état S3 et la base de données.

## Décisions finales actées (à ne pas remettre en cause sans discussion explicite)

- Le back-office utilise Cognito pour authentifier agents et administrateurs.
- Le portail public reste statique, optimisé SEO, sans serveur permanent.
- GitHub Actions remplace la Lambda de rendu HTML comme environnement de build.
- Les publications de contenu sont incrémentales et pilotées par manifeste.
- Les expirations entraînent une **reconstruction** de la page, pas une suppression immédiate.
- Le modèle peut évoluer vers davantage de parallélisme sans changer les fondations.

## Vue d'ensemble de l'architecture cible

```
Portail privé → Cognito → API Gateway (JWT Authorizer) → Lambda → Aurora DSQL

EventBridge Scheduler → Publication Coordinator → Manifeste (S3) → GitHub Actions
  → Génération ciblée (Next.js) → S3 → CloudFront
```

Deux chaînes indépendantes : identité et autorisation d'un côté, publication et diffusion de l'autre.

## Cadence de traitement

Le contenu n'a pas vocation à être mis à jour en temps réel. Ne pas construire d'architecture événementielle temps réel (flux d'événements, files d'attente à faible latence) sans besoin explicite documenté — le traitement par lot quotidien est un choix délibéré pour limiter la complexité et le coût. Les alertes abonnés suivent la même cadence quotidienne (synthèse groupée, pas de notification instantanée par AO).

## Référence au modèle de données

Le détail des champs d'une fiche AO (référence, titre, acheteur, secteur, type de marché/procédure, montant, zone, dates, critères d'éligibilité, pièces à fournir, documents joints, contact, source, statut, historique) est documenté dans `PRD.md §3.2` — s'y référer pour tout schéma Aurora DSQL ou toute validation de formulaire back-office.

Le schéma SQL de référence vit dans `infra/terraform/db/migrations/` — un fichier par instruction DDL (61 fichiers, exécutés dans l'ordre lexicographique de leur préfixe numéroté ; les 8 derniers ajoutent les champs PRD §3.2 encore absents à `tenders` et créent le rôle Postgres non-admin `tenders_api_role` consommé par la Lambda `tenders_api`), source de vérité unique appliquée par la Lambda `db-migrate` (`infra/terraform/lambda_migrate.tf`). C'est aussi la référence à lire pour comprendre le schéma dans son ensemble (16 tables : `users`, `countries`, `categories`, `organizations`, `diffusion_partnerships`, `subscribers`, `subscription_plans`, `subscriptions`, `payments`, `tenders`, `tender_categories`, `tender_documents`, `tender_status_history`, `audit_log`, `publication_batches`, `publication_batch_items`). Les statuts de `tenders` (`DRAFT → PENDING_REVIEW → REVISION_REQUESTED / APPROVED → QUEUED_FOR_PUBLICATION → PUBLISHED → EXPIRED / REJECTED / ARCHIVED`) implémentent le workflow AGENT/REVIEWER/ADMIN décrit plus haut ; `content_hash` sert à la détection de changements du Publication Coordinator, `publication_batches` + `publication_batch_items` tracent l'exécution du batch au niveau AO (reprise idempotente par item).

### Contraintes Aurora DSQL à respecter dans tout le code

- **Pas de FOREIGN KEY, TRIGGER, ni VIEW** — l'intégrité référentielle et `updated_at` sont gérés explicitement par la Lambda métier, jamais par la base.
- **1 seule instruction DDL par transaction**, jamais mélangée à du DML — toute migration passe par un runner en autocommit, pas de `BEGIN...COMMIT` global sur plusieurs DDL. En pratique, ce runner est la Lambda `db-migrate` (`infra/terraform/lambda_src/migrate/handler.py`), invoquée automatiquement par Terraform (`aws_lambda_invocation.run_migrations` dans `infra/terraform/lambda_migrate.tf`) à chaque changement du contenu de `infra/terraform/db/migrations/` — jamais de connexion DSQL admin directe depuis un poste de développeur.
- **Contrôle de concurrence optimiste (OCC)** : toute transaction peut échouer avec SQLSTATE `40001` (`OC000`/`OC001`) — comportement normal à gérer par retry/backoff dans le code applicatif, jamais traité comme une erreur fatale.
- `CREATE INDEX` (et `CREATE UNIQUE INDEX`) synchrone n'est **pas supporté du tout** par DSQL, peuplée ou non — toujours utiliser `CREATE INDEX ASYNC` / `CREATE UNIQUE INDEX ASYNC`, avec suivi via `sys.jobs` si besoin de savoir quand l'indexation est terminée (vérifié en pratique le 2026-08-06 via un déploiement réel : un `CREATE INDEX` classique échoue avec `FeatureNotSupported: unsupported mode. please use CREATE INDEX ASYNC.`, même sur une table vide).
- **Les contraintes `CHECK` ne sont possibles qu'à la création de la table** (`CREATE TABLE ... CHECK (...)`, qui fonctionne bien). `ALTER TABLE ADD COLUMN ... CHECK (...)` et `ALTER TABLE ADD CONSTRAINT ... CHECK (...)` échouent tous les deux avec `FeatureNotSupported` (vérifié en pratique le 2026-08-06). En conséquence, toute colonne ajoutée après coup avec une contrainte de type énuméré doit être validée **uniquement côté Lambda métier** (voir `backend/tenders_api/tenders.py::_validate_enum_fields` pour `procurement_type`/`procedure_type`, ajoutés par la migration 054 sans CHECK en base) — cohérent avec le principe déjà en place (pas de FK/trigger, intégrité gérée par la Lambda).
- Connexion en **IAM uniquement** (`DsqlSigner` / `generate-db-connect-admin-auth-token`) — pas d'identifiants statiques.
- DSQL est un service en évolution rapide (JSON/JSONB supporté seulement depuis mai/juin 2026) : revérifier les [release notes](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/release-notes.html) avant de s'appuyer sur une fonctionnalité non listée ici.
