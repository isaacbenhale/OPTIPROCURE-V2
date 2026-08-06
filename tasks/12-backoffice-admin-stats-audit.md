# Module 12 — Back-office admin : statistiques, gestion des abonnés, audit

> Complète le back-office ADMIN au-delà du seul workflow des AO : journal d'audit visible, supervision des abonnés, statistiques (AO publiés, conversion, consultation).

## Objectif

PRD §3.7 : "Supervision des abonnés... Statistiques de consultation, taux de conversion visiteur → abonné, AO les plus consultés. Journal d'audit des actions administratives (traçabilité)." Complète le back-office (module 03) avec les vues réservées à l'ADMIN au-delà du seul workflow des AO.

## Références

- PRD §3.7, §8 (KPI : AO publiés par mois/secteur, inscriptions, taux de conversion, rétention, taux d'ouverture des alertes, délai moyen de mise en ligne)
- `infra/terraform/db/migrations/042_table_audit_log.sql` (déjà alimenté par `backend/tenders_api/`, ce module en expose la lecture)
- CLAUDE.md : "Journalisation systématique : connexions, refus d'accès, modifications, approbations, publications" — ce module rend cette journalisation *visible*, il ne la produit pas (déjà fait par les modules précédents)

## Dépendances

Module 03 (UI back-office à étendre), module 09 (données d'abonnement pour la supervision), idéalement module 11 en place pour le suivi de consultation (sinon les KPI de conversion manqueront de données).

## Périmètre

**Dans le périmètre :**
- Vue journal d'audit (lecture `audit_log`, filtrable par acteur/action/entité/date — déjà indexé pour ça, voir migrations 043-046).
- Supervision des abonnés : liste, suspension/réactivation (`subscribers.is_active`, `subscriptions.status`), gestion des impayés (croise module 09).
- Statistiques : AO publiés par mois/secteur (agrégat sur `tenders`), taux de conversion visiteur→abonné (nécessite une notion de "visiteur" trackée quelque part — **à définir**, potentiellement hors périmètre technique si aucun tracking analytics n'est en place), AO les plus consultés (dépend du tracking de consultation du module 11).
- Support client — PRD le mentionne (§3.7 "support client") mais reste vague : probablement juste un lien mailto/contact à ce stade, pas un système de ticketing à construire.

## Points à trancher avant de coder

1. **Tracking des visiteurs anonymes** : le taux de conversion visiteur→abonné (PRD §8) suppose un minimum d'analytics sur le portail public statique. Introduire un outil d'analytics (Plausible/Umami self-hosted, ou service tiers) est une décision produit/vie privée à part entière — à ne pas improviser dans ce module, à poser explicitement à l'utilisateur (impact RGPD/données personnelles, cf. PRD §5 "conformité aux exigences applicables en matière de protection des données personnelles").
2. **Fraîcheur des statistiques** : calcul à la volée (requêtes DSQL directes, simple mais potentiellement coûteux si les agrégats deviennent lourds) vs table de stats pré-calculées par un job batch (plus scalable, plus de complexité) — commencer par le calcul à la volée (pas de sur-ingénierie tant que le volume ne le justifie pas), documenté comme un choix révisable.

## Définition de "terminé"

- Un ADMIN peut consulter le journal d'audit filtré par période/acteur/action.
- Un ADMIN peut suspendre/réactiver un abonné et voir l'effet immédiat sur ses accès.
- Les statistiques de base (AO publiés par mois/secteur, abonnés actifs) sont visibles et correctes par recoupement manuel avec les données brutes.
