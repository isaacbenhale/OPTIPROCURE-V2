-- Rôle Postgres non-admin dédié à la Lambda tenders_api (module 3).
-- Connexion IAM (dsql:DbConnect, pas DbConnectAdmin) — voir 059 pour la
-- liaison au rôle IAM, et CLAUDE.md pour la contrainte "connexion IAM
-- uniquement". Syntaxe à revérifier contre la doc AWS DSQL au moment du
-- déploiement (service en évolution rapide) — validée par un spike de
-- connexion isolé avant d'écrire le reste du module.
CREATE ROLE tenders_api_role WITH LOGIN;
