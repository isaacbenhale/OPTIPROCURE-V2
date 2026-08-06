# Module 03 — Frontend back-office (`frontend-admin/`)

> Interface SPA pour que les AGENT/REVIEWER/ADMIN utilisent réellement le workflow des AO — sans elle, l'API ne s'utilise qu'au clavier via curl/Postman.

## Objectif

Le dossier `frontend-admin/` est vide. Sans lui, le module 3 (API `tenders_api`) n'est utilisable qu'au clavier via `curl`/Postman — aucun AGENT/REVIEWER/ADMIN réel ne peut travailler. C'est l'interface qui rend le workflow éditorial (PRD §3.1, §2.2) concrètement utilisable.

## Références

- `infra/terraform/cognito.tf` : User Pool back-office, client SPA `backoffice_spa` (PKCE, `generate_secret=false`), `cognito_callback_urls`/`cognito_logout_urls` (actuellement `http://localhost:3000/callback`)
- `backend/tenders_api/` : toutes les routes disponibles (voir `handler.py` pour la liste exacte), format de réponse JSON, codes d'erreur (`error.code` : VALIDATION_ERROR/UNAUTHORIZED/FORBIDDEN/NOT_FOUND/CONFLICT)
- PRD §2.2 (rôles), §3.1 (cycle de statut), §3.7 (back-office admin — une partie dépend du module 12)

## Dépendances

Module 3 (API), module 01 (référentiels — nécessaire pour les formulaires de création), module 02 (upload de documents, peut être branché après coup sans bloquer le reste de l'UI).

## Périmètre

**Dans le périmètre :**
- Authentification Cognito (Authorization Code + PKCE), stockage de l'access token (utilisé pour tous les appels API — voir `backend/tenders_api/auth.py`, qui exige l'access token et non l'ID token), refresh token, déconnexion.
- Vues par rôle : liste des AO (filtrée par `GET /tenders`), formulaire de création/édition (AGENT), file de révision (REVIEWER), file d'approbation (ADMIN).
- Actions de workflow : soumettre, retourner (avec motif), endosser, approuver (avec confirmation MFA visible), rejeter (avec motif), archiver.
- Affichage de l'historique de statut (`GET /tenders/{id}/history`) et des erreurs de validation renvoyées par l'API (`error.fields`).

**Hors périmètre :**
- Statistiques et audit (module 12).
- Gestion des utilisateurs Cognito (création de comptes AGENT/REVIEWER/ADMIN) — actuellement `admin_create_user_config.allow_admin_create_user_only = true`, donc géré via AWS Console/CLI tant que ce module n'existe pas ; à réévaluer si le volume d'agents le justifie.

## À construire

- Choix de stack **à trancher** (voir ci-dessous), squelette d'app dans `frontend-admin/`.
- Client API typé (wrapper fetch avec injection automatique du token, gestion 401 → redirection login).
- Écrans : login, liste des AO (avec filtres), détail/édition d'un AO, actions de workflow contextuelles selon rôle + statut (réutiliser la même logique de matrice que `backend/tenders_api/transitions.py` côté UI pour ne proposer que les actions valides — dupliquer la matrice ou l'exposer via un endpoint `GET /tenders/{id}` enrichi d'un champ `available_actions` calculé côté Lambda, **à trancher**).
- Gestion des erreurs uniforme (toasts/bannières sur `error.code`/`error.fields`).

## Points à trancher avant de coder

1. **Stack frontend** : React (Vite) en SPA pure, ou Next.js en mode client-side uniquement (cohérence d'outillage avec `frontend-public/` qui sera Next.js, mais le back-office n'a aucune contrainte SEO/statique) ? Une SPA Vite plus légère est probablement suffisante et plus simple à déployer (S3+CloudFront distinct ou même compte, hors périmètre CI de `frontend-public/`).
2. **Calcul des actions disponibles** : dupliquer `transitions.py` en TypeScript côté front (risque de désynchronisation avec le backend) vs. exposer `available_actions` calculé par la Lambda dans la réponse de `GET /tenders/{id}` (une seule source de vérité, léger surcoût de calcul serveur) — la deuxième option est recommandée mais implique une petite extension de `tenders.get_tender`.
3. **Hébergement** : S3+CloudFront séparé du portail public (deux buckets/distributions distincts, cohérent avec "deux portails distincts" du PRD §2) — confirmer que ce n'est pas couvert par `infra/terraform/s3_cloudfront.tf` actuel (qui ne gère que `public_site`) et qu'il faut un nouveau fichier Terraform dédié.

## Définition de "terminé"

- Un AGENT peut se connecter, créer un AO complet, le soumettre.
- Un REVIEWER peut le voir dans sa file, le retourner avec un motif.
- Un ADMIN peut l'approuver (MFA visible dans le flux) ou le rejeter.
- Toutes les erreurs métier (permission refusée, champs manquants, conflit) s'affichent de façon compréhensible, pas de JSON brut à l'écran.
