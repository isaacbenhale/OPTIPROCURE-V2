# Module 06 — Pipeline de déploiement frontend (GitHub Actions)

## Objectif

Écrire les workflows `.github/workflows/*.yml` mentionnés comme manquants dans `infra/terraform/README.md`. CLAUDE.md est explicite : **deux pipelines distincts, jamais fusionnés** — publication incrémentale des données (déclenchée par le manifeste) vs déploiement complet du frontend (déclenché par un merge de code Next.js).

## Références

- CLAUDE.md §"Deux workflows distincts à maintenir", §"Gestion des erreurs et reprise" (invalidations CloudFront ciblées, jamais de suppression de fichiers non concernés)
- `infra/terraform/github_oidc.tf` : rôle `github_actions_deploy` déjà prêt (permissions : `s3:PutObject/DeleteObject/ListBucket` sur `public_site`, lecture sur `manifests`, `cloudfront:CreateInvalidation`) — federation OIDC déjà opérationnelle, aucune clé statique à créer.
- Module 04 pour la question ouverte du déclenchement (push vs poll) — **ce module ne peut pas être finalisé tant que cette décision n'est pas prise**.

## Dépendances

Module 05 (le générateur à invoquer). Bloqué sur la décision d'architecture du module 04 point 1.

## Périmètre

**Workflow 1 — Publication incrémentale (données) :**
- Déclenchement : selon la décision du module 04 (poll planifié recommandé, voir ce fichier).
- Étapes : lire le manifeste le plus récent depuis S3 (rôle `github_actions_deploy`), si rien de neuf → sortir sans rien construire (coût zéro, exigence CLAUDE.md) ; sinon lancer le générateur (module 05) en mode ciblé sur les pages listées, uploader uniquement les fichiers produits, invalider CloudFront uniquement sur les URL modifiées (jamais `/*`).
- Ne jamais supprimer de fichiers S3 non concernés par le déploiement incrémental (CLAUDE.md, contrainte explicite).

**Workflow 2 — Déploiement complet frontend :**
- Déclenchement : merge sur la branche de production touchant `frontend-public/` (layouts, composants partagés, règles SEO).
- Étapes : build complet Next.js, upload complet, invalidation ciblée (ou complète si nécessaire — sert aussi de mécanisme de réconciliation après incident, CLAUDE.md).

**Hors périmètre :**
- Le déploiement de `frontend-admin/` (module 03) — probablement un 3e workflow léger, à spécifier séparément une fois le module 03 défini (bucket/distribution distincts).

## Points à trancher avant de coder

Voir module 04, point 1 — c'est la dépendance bloquante de ce module. Ne pas commencer avant d'avoir tranché push vs poll.

## Définition de "terminé"

- Un `apply` du module 04 sans changement ne déclenche aucun run coûteux du Workflow 1 (ou le run se termine en quelques secondes sans build).
- Un nouveau batch (AO créé/modifié/expiré) produit un déploiement ciblé, vérifiable par le contenu de l'invalidation CloudFront (liste d'URL précise, jamais `/*`).
- Un merge sur `frontend-public/` sans rapport avec les AO déclenche bien le Workflow 2, jamais le Workflow 1.
- Aucune clé AWS statique dans les secrets GitHub (vérifier la config du workflow, uniquement `aws-actions/configure-aws-credentials` avec le rôle OIDC).
