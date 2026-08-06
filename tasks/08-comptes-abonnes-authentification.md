# Module 08 — Comptes abonnés et authentification publique

## Objectif

PRD §3.6 : "Création de compte en libre-service (inscription, vérification d'email, choix du plan) sans intervention de l'administrateur." Aucune identité publique n'existe actuellement — CLAUDE.md ne décrit que Cognito pour le **back-office**. Ce module pose l'identité du portail public, préalable à tout le reste (paiement, alertes, tableau de bord).

## Références

- CLAUDE.md : "Amazon Cognito est la source d'identité unique **du back-office**" — formulation qui, prise à la lettre, exclut le portail public d'un unique pool Cognito partagé. `infra/terraform/cognito.tf` porte un commentaire explicite en tête : "Le portail public n'a pas de User Pool ici : la création de compte abonné en libre-service (PRD §3.6) est un module applicatif séparé, à traiter avec sa propre logique métier."
- `infra/terraform/db/migrations/012_table_subscribers.sql` : table `subscribers` — **remarque importante : aucune colonne `cognito_sub` ni équivalent**, contrairement à `users` (back-office). Le mécanisme d'authentification abonné n'est donc pas encore reflété dans le schéma.
- PRD §2.1 (profils portail public), §3.6 (espace abonné), §5 (sécurité — RBAC Administrateur/Abonné/Visiteur côté public)

## Dépendances

Aucune dépendance dure sur les modules 01-07 — peut être développé en parallèle.

## Périmètre

**Dans le périmètre :**
- Choix et mise en place de l'identité publique (voir décision ci-dessous).
- Inscription (email + mot de passe ou identité fédérée), vérification d'email, connexion, déconnexion, réinitialisation de mot de passe.
- Profil abonné de base (secteurs d'intérêt, zones géographiques — PRD §3.6) : nécessite d'étendre `subscribers` (colonnes actuelles insuffisantes pour ces préférences) ou une nouvelle table `subscriber_preferences`.

**Hors périmètre :**
- Choix et paiement du plan (module 09).
- Tableau de bord complet (module 11).

## Points à trancher avant de coder

1. **Deuxième User Pool Cognito dédié aux abonnés, vs solution différente** (Auth0/Supabase Auth/roll-your-own) : un second User Pool Cognito est probablement le choix le plus cohérent avec l'infra existante (même provider, même patterns IAM déjà maîtrisés dans ce repo), mais **CLAUDE.md ne l'a jamais acté explicitement** — c'est une extension d'architecture, pas une évidence. À confirmer avant de toucher à `infra/terraform/cognito.tf` ou d'en créer un second fichier dédié (ex. `infra/terraform/cognito_public.tf`).
2. **Colonne `cognito_sub` manquante sur `subscribers`** : si l'option Cognito est retenue, une migration (062+) devra ajouter cette colonne (même pattern que `users.cognito_sub`), et la Lambda concernée devra faire le même provisioning JIT que `backend/tenders_api/auth.upsert_user` (référence directe à réutiliser).
3. **API publique associée** : ce module implique-t-il une nouvelle chaîne API Gateway + Lambda + DSQL dédiée au portail public (distincte de celle du back-office) ? Probablement oui, pour respecter le découplage identité/logique métier des deux domaines (CLAUDE.md, principe fondamental). À croiser avec la décision du module 07 (option 2, API de lecture publique) — les deux pourraient partager la même Lambda/API Gateway "publics" si les deux options convergent.
4. **Vérification d'email et réinitialisation de mot de passe** : gérées nativement par Cognito si l'option 1 est retenue (SES sous-jacent, `auto_verified_attributes`), à confirmer que ça ne nécessite pas de configuration SES supplémentaire (domaine expéditeur vérifié — lié au module 10 également, qui a de toute façon besoin de SES).

## Définition de "terminé"

- Un visiteur peut s'inscrire, vérifier son email, se connecter, réinitialiser son mot de passe — sans intervention d'un ADMIN.
- Le profil abonné (secteurs/zones d'intérêt) est modifiable après connexion.
- Aucune confusion possible entre l'identité back-office (Cognito `backoffice`) et l'identité abonné — deux domaines d'authentification strictement séparés, cohérent avec le principe de découplage du CLAUDE.md.
