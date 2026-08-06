# Module 04 — Publication Coordinator

## Objectif

Remplacer `infra/terraform/lambda_src/publication_coordinator_stub/handler.py` (no-op actuel) par la vraie détection de changements et génération de manifeste décrites dans CLAUDE.md §"Détection des changements". C'est le pivot entre le back-office (module 3) et le portail public (modules 05/06) — et le seul endroit qui a le droit de faire progresser un AO au-delà d'APPROVED (`tenders_api` refuse explicitement QUEUED_FOR_PUBLICATION/PUBLISHED/EXPIRED, voir `backend/tenders_api/transitions.py`).

## Références

- CLAUDE.md : sections "Workflow de publication", "Détection des changements" (manifeste, gestion du curseur, table de décision), "Gestion des erreurs et reprise" (états PENDING/RUNNING/SUCCEEDED/FAILED, idempotence)
- `infra/terraform/db/migrations/047_table_publication_batches.sql`, `050_table_publication_batch_items.sql`
- `infra/terraform/eventbridge.tf` (déclenchement quotidien), `infra/terraform/iam.tf` (rôle `lambda_publication_coordinator`, déjà `dsql:DbConnect` + accès au bucket `manifests`)
- `tenders.content_hash` (module 3) — sert justement à cette détection de changements

## Dépendances

Module 3 (statuts APPROVED existants à faire progresser).

## Périmètre

**Dans le périmètre :**
- Faire progresser les AO APPROVED → QUEUED_FOR_PUBLICATION → PUBLISHED (avec `publication_date`), en écrivant `tender_status_history` (`actor_type='PIPELINE'`, valeur déjà prévue par le CHECK constraint).
- Détecter les AO PUBLISHED dont `submission_deadline` est dépassée → transition vers EXPIRED (reconstruction de page, pas suppression — CLAUDE.md).
- Calculer la fenêtre de changements depuis le dernier batch **SUCCEEDED** (requête sur `publication_batches`, pas de curseur stocké ailleurs).
- Construire et écrire le manifeste dans S3 (bucket `manifests`), avec : `batchId`, fenêtre temporelle, AO créés/modifiés/expirés, pages de collection affectées (par catégorie/pays/organisation), fichiers SEO à reconstruire (sitemap).
- Tracer l'exécution : une ligne `publication_batches` (statut PENDING→RUNNING→SUCCEEDED/FAILED/PARTIALLY_SUCCEEDED), une ligne `publication_batch_items` par AO traité (action CREATE/UPDATE/EXPIRE/DELETE, reprise idempotente au niveau item si un item échoue).
- Ne rien écrire/déclencher si aucun changement (CLAUDE.md : "aucun build n'est déclenché si aucun AO n'a été créé, modifié ou nouvellement expiré").

**Hors périmètre :**
- Le build Next.js lui-même et l'upload S3/invalidation CloudFront (modules 05/06 — cette Lambda ne fait que produire le manifeste).

## Points à trancher avant de coder

1. **Comment GitHub Actions apprend-il qu'un nouveau manifeste existe ?** C'est la question ouverte la plus importante de tout ce module. Deux directions possibles, à trancher avec l'utilisateur avant de coder :
   - **(a) Push AWS → GitHub** : la Lambda appelle l'API GitHub (`repository_dispatch` ou déclenchement de workflow) avec le `batchId`. Nécessite un identifiant GitHub côté AWS (PAT ou GitHub App), donc un secret à gérer (Secrets Manager) — direction opposée à la fédération OIDC déjà en place (qui ne permet que GitHub → AWS, jamais l'inverse).
   - **(b) Poll GitHub → AWS** : le workflow GitHub Actions est lui-même planifié (cron), tourne peu après l'horaire EventBridge, lit le bucket `manifests` (via le rôle OIDC déjà provisionné `github_actions_deploy`, qui a déjà `s3:GetObject`/`ListBucket` sur ce bucket — voir `infra/terraform/github_oidc.tf`) et compare au dernier `batchId` déjà traité (stocké où ? à définir — fichier dans le bucket public_site, ou tag Git, ou fichier committé). S'il n'y a rien de nouveau, le workflow s'arrête sans rien construire.
   
   L'option (b) ne demande aucun nouveau secret et exploite une permission déjà posée dans l'infra existante — c'est l'option la plus cohérente avec "pas de clés AWS statiques" et le principe du moindre privilège déjà appliqué partout ailleurs. À confirmer explicitement avant de coder, ça détermine la moitié du module 06.
2. **QUEUED_FOR_PUBLICATION est-il un état transitoire dans la même exécution, ou un état qui persiste entre deux runs du Coordinator ?** (ex. si le build/déploiement échoue après le passage en QUEUED_FOR_PUBLICATION, l'AO doit-il repasser par cet état au prochain run, ou repartir direct en PUBLISHED une fois le déploiement confirmé a posteriori ?) — impacte la conception de l'idempotence par item.

## Définition de "terminé"

- Un AO APPROVED sans changement depuis la veille ne génère aucun batch.
- Un AO APPROVED se retrouve PUBLISHED après un run, avec manifeste correspondant en S3.
- Un AO PUBLISHED dont la deadline est dépassée passe à EXPIRED au run suivant, avec manifeste incluant sa reconstruction.
- Un run interrompu en cours de traitement (simuler un échec sur un item) peut être rejoué sans dupliquer les transitions déjà appliquées (test d'idempotence explicite).
- `publication_batches.status` reflète fidèlement l'issue (jamais SUCCEEDED si un item a échoué).
