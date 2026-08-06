# Module 09 — Abonnements et paiement

## Objectif

PRD §4 (modèle économique, 3 formules), §3.6 (gestion de l'abonnement et de la facturation). Active le modèle économique de la plateforme — sans lui, aucun abonné payant, aucun accès aux fiches complètes/documents/alertes selon plan.

## Références

- `infra/terraform/db/migrations/014_table_subscription_plans.sql`, `016_table_subscriptions.sql`, `021_table_payments.sql`
- PRD §4 (tableau des 3 formules Découverte/Standard/Premium, tarifs à définir), VISION.md (le plan Standard doit rester "volontairement fixé à un tarif bas" — filtre qualitatif, pas barrière financière)
- `infra/terraform/README.md` : "Passerelle de paiement (mobile money / carte bancaire)" listée comme non couverte

## Dépendances

Module 08 (identité abonné).

## Périmètre

**Dans le périmètre :**
- CRUD `subscription_plans` côté admin (catalogue commercial — probablement à rattacher au module 01 ou 12, ADMIN uniquement).
- Souscription : création `subscriptions` (statut PENDING_PAYMENT → ACTIVE après paiement confirmé), avec `price_paid`/`currency` figés au moment de la souscription (indépendants d'une évolution ultérieure du tarif catalogue).
- Intégration paiement (mobile money prioritaire vu le marché cible togolais — PRD §9/§10 ; carte bancaire en complément), écriture `payments` avec `provider_reference` unique pour l'idempotence (déjà prévu par le schéma).
- Cycle de vie : essai gratuit (plan Découverte, gratuit par défaut), relance avant expiration, suspension (paiement échoué), réactivation, annulation.
- Renouvellement automatique.

**Hors périmètre :**
- Le tableau de bord de facturation abonné (factures téléchargeables — module 11).
- Application effective des quotas du plan (nombre d'alertes, export, multi-utilisateurs) dans les autres modules — chaque module concerné (10, 11, 05 pour les documents) doit lire `subscriptions`/`subscription_plans.features` (JSONB) pour appliquer sa propre restriction ; ce module ne fait que gérer le cycle de vie de l'abonnement lui-même.

## Points à trancher avant de coder

1. **Fournisseur mobile money** : PRD mentionne "carte bancaire, mobile money selon la zone géographique" sans nommer de provider. Au Togo/UEMOA, les options courantes sont des agrégateurs locaux (ex. PayGate, CinetPay, Flutterwave, ou intégration directe Moov/Togocom) — ce choix a un impact fort sur l'intégration (webhooks, formats de callback) et doit être posé à l'utilisateur avant de coder l'intégration, ce n'est pas une décision technique neutre.
2. **Webhooks de paiement et sécurité** : nécessite un nouvel endpoint API Gateway **public** (non authentifié Cognito, authentifié par signature du provider) — nouvelle chaîne à ajouter à l'inventaire IAM/API Gateway, à concevoir avec le même souci de moindre privilège que le reste (rôle Lambda dédié, jamais partagé avec `lambda_tenders_api`).
3. **Gestion des échecs de paiement récurrents** (renouvellement automatique qui échoue) : politique de rétries/relances à définir avec l'utilisateur (nombre de tentatives, délai avant suspension) — impacte le contenu du module 10 (email de relance).

## Définition de "terminé"

- Un abonné peut souscrire au plan Standard, payer via mobile money, et voir son abonnement passer ACTIVE.
- Un paiement dupliqué (même `provider_reference`) ne crée pas une deuxième transaction (test d'idempotence).
- Un abonnement arrivé à `expires_at` passe EXPIRED et les accès associés (autres modules) se dégradent correctement.
- Le webhook de paiement est protégé contre les requêtes forgées (vérification de signature, pas de confiance aveugle au payload).
