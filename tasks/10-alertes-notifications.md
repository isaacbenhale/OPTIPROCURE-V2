# Module 10 — Alertes et notifications

> Synthèse quotidienne/hebdomadaire par email (puis SMS) sur les recherches sauvegardées d'un abonné — aucune table de données ne couvre encore ce besoin, à créer.

## Objectif

PRD §3.5 : alertes email (SMS pour les plans supérieurs) déclenchées par des critères sauvegardés, fréquence configurable (synthèse quotidienne ou hebdomadaire), notification de modification d'un AO suivi, notification de fin d'abonnement. CLAUDE.md : "Les alertes abonnés suivent la même cadence quotidienne (synthèse groupée, pas de notification instantanée par AO)."

## Références

- CLAUDE.md §"Cadence de traitement" (pas de temps réel, synthèse groupée)
- PRD §3.5, §4 (nombre d'alertes par plan — 1/5/illimité, fréquence hebdo/quotidienne/quotidienne)
- `infra/terraform/README.md` : "Service d'envoi d'alertes email/SMS (SES/SNS)" listé comme non couvert
- **Remarque importante** : aucune table `saved_searches`/`alerts`/`tracked_tenders` n'existe dans le schéma actuel (16 tables listées en CLAUDE.md, aucune ne couvre ce besoin) — ce module démarre par une extension de schéma, pas seulement du code applicatif.

## Dépendances

Module 07 (modèle de critères de recherche sauvegardée, PRD : "Sauvegarde de recherches types, transformables en alertes personnalisées" — le modèle de données des critères devrait être défini une fois pour les deux). Module 08/09 (identité abonné + plan pour appliquer les quotas).

## Périmètre

**Dans le périmètre :**
- Nouvelles migrations : table `saved_searches` (subscriber_id, critères JSONB, fréquence, is_active) et `tracked_tenders` (subscriber_id, tender_id — "AO suivis", PRD §3.6) si pas déjà couvert par le module 11.
- Génération de synthèse quotidienne/hebdomadaire par abonné (batch, même cadence qu'EventBridge — pourrait être déclenché juste après ou par le même Publication Coordinator, à trancher).
- Envoi email via SES (nécessite domaine expéditeur vérifié — coordination avec le module 08 qui a le même besoin pour la vérification d'email).
- Envoi SMS via SNS pour les plans supérieurs (Premium — dépend de l'application des quotas du module 09).
- Notification de modification d'un AO suivi (report de délai, annulation, addenda — lecture de `tender_status_history`).
- Notification de fin d'abonnement à venir / renouvellement (lecture de `subscriptions.expires_at`).

**Hors périmètre :**
- L'UI de gestion des alertes actives côté abonné (module 11).

## Points à trancher avant de coder

1. **Déclencheur du batch d'alertes** : nouvelle règle EventBridge Scheduler dédiée (indépendante du Publication Coordinator), ou étape supplémentaire à la fin du Publication Coordinator (module 04) une fois la publication du jour terminée (garantit que les alertes portent sur des données déjà publiées, pas en cours de traitement) ? La deuxième option semble plus sûre (évite d'alerter sur un AO dont le batch de publication a échoué) mais couple deux responsabilités dans une même Lambda — **à trancher**, cohérent avec CLAUDE.md qui insiste sur le découplage des chaînes mais parle spécifiquement de découpler *identité* et *publication*, pas nécessairement *publication* et *alertes* (les deux étant côté diffusion).
2. **Vérification de domaine SES** : sortir d'un environnement sandbox SES (limité en volume/destinataires) nécessite une demande de production access AWS — à anticiper, pas instantané.
3. **Fournisseur SMS local (Togo)** : SNS AWS a un support SMS variable selon les pays — vérifier la couverture Togo/UEMOA avant de s'y engager, sinon prévoir un fournisseur SMS régional en alternative.

## Définition de "terminé"

- Un abonné avec une recherche sauvegardée et une fréquence quotidienne reçoit un email de synthèse le jour suivant un nouvel AO correspondant.
- Aucun email n'est envoyé s'il n'y a aucune correspondance nouvelle depuis la dernière synthèse (cohérent avec la philosophie "pas de bruit inutile" de CLAUDE.md).
- Un abonné suivant un AO reçoit une notification lors d'un report de délai/annulation.
- Le quota d'alertes par plan (1/5/illimité) est appliqué (test avec un abonné Découverte qui ne peut pas créer une 2e alerte).
