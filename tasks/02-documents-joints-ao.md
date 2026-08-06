# Module 02 — Documents joints des AO

> Upload/téléchargement des pièces jointes d'un AO (DAO, cahier des charges, annexes) via URL S3 présignées — périmètre différé lors du module 3.

## Objectif

Périmètre explicitement différé lors du module 3 (voir `tasks/README.md` et l'historique de conversation) : permettre l'upload/téléchargement des pièces jointes d'un AO (DAO, cahier des charges, annexes). PRD §3.2/§3.3 : "Documents joints... Téléchargement des documents joints réservé aux abonnés selon leur plan."

## Références

- `infra/terraform/db/migrations/037_table_tender_documents.sql`
- `infra/terraform/iam.tf` — le rôle `lambda_tenders_api` a déjà `s3:GetObject`/`s3:PutObject` sur `aws_s3_bucket.documents` (provisionné par anticipation, jamais utilisé jusqu'ici)
- CLAUDE.md : bucket documents non public, accès via URL présignée uniquement (voir commentaire dans `infra/terraform/s3_cloudfront.tf`)
- PRD §4 (tableau des plans) : le téléchargement de documents dépend du plan de l'abonné (Non / Oui / Oui illimité) — dépend du module 09 pour être appliqué correctement côté portail public.

## Dépendances

Module 3 (`backend/tenders_api/`, dont ce module étend directement le périmètre).

## Périmètre

**Dans le périmètre :**
- Upload : génération d'URL présignée S3 (PUT) par la Lambda `tenders_api`, enregistrement des métadonnées dans `tender_documents` après upload confirmé.
- Liste des documents d'un AO (`GET /tenders/{id}/documents`).
- Suppression (soft-delete `deleted_at`) par le créateur de l'AO tant qu'il est en DRAFT/REVISION_REQUESTED (mêmes règles que `update_tender`).
- Téléchargement : génération d'URL présignée S3 (GET), à durée de vie courte.

**Hors périmètre (pour l'instant) :**
- Contrôle d'accès par plan d'abonnement (dépend du module 09 — l'API back-office elle-même n'a pas cette notion, c'est le portail public qui l'appliquera).
- Antivirus/scan des fichiers uploadés — à évaluer séparément si le volume le justifie.

## À construire

- Nouveaux fichiers dans `backend/tenders_api/` : `documents.py` (logique), routes `POST /tenders/{id}/documents` (retourne une URL présignée PUT + document_id), `POST /tenders/{id}/documents/{doc_id}/confirm` (marque l'upload terminé après confirmation client), `GET /tenders/{id}/documents`, `DELETE /tenders/{id}/documents/{doc_id}`.
- Réutiliser `auth.require_role`/`require_active`, les mêmes règles de propriété que `update_tender` (§4 du plan module 3).
- Limiter la taille/le type de fichier accepté dans la génération de l'URL présignée (Content-Type, Content-Length-Range).
- Recalcul de `tenders.content_hash` : **décision à prendre** — un ajout/suppression de document doit-il invalidé le hash de contenu (donc déclencher une republication) ? Probablement oui si les documents sont affichés sur la fiche publique.

## Points à trancher avant de coder

1. Confirmer que le flux est bien "upload direct navigateur → S3 via URL présignée" (pas d'upload transitant par la Lambda, qui a des limites de payload) — cohérent avec les permissions IAM déjà posées, mais à valider explicitement avant de coder le frontend (module 03) en parallèle.
2. Le hash de contenu (`content_hash.py`, module 3) n'inclut actuellement pas les documents — décider s'il faut l'étendre pour inclure la liste des `document_id`/noms de fichiers.

## Définition de "terminé"

- Un AGENT peut uploader un document sur son brouillon, le voir listé, le supprimer.
- URL de téléchargement présignée fonctionnelle et à expiration courte (ex. 5 minutes).
- Tests : refus d'upload sur un AO qui n'est pas DRAFT/REVISION_REQUESTED ; refus pour un non-propriétaire ; URL présignée jamais générée sans passer par la vérification de permission.
