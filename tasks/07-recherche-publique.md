# Module 07 — Recherche et filtres publics

> Recherche/filtres combinables sur le portail public — soulève une vraie tension d'architecture non résolue (site statique vs recherche dynamique), à trancher avant de coder.

## Objectif

PRD §3.4 : recherche par mots-clés, filtres combinables (secteur, région, montant, type de procédure, date limite, statut), tri, sauvegarde de recherches (transformables en alertes — module 10). Ce module mérite un fichier séparé du générateur (module 05) parce qu'il soulève une vraie tension d'architecture non résolue par CLAUDE.md.

## Références

- CLAUDE.md : choix explicite d'Aurora DSQL motivé par "sa capacité à traiter nativement les recherches multi-critères combinables... sans service de recherche additionnel" — mais l'architecture cible décrite (Cognito+API Gateway+Lambda+DSQL) ne couvre que le **back-office authentifié**, pas un accès public en lecture.
- PRD §3.4 (détail des filtres), §2.1 (Visiteur non-inscrit : "consultation vitrine limitée")

## Dépendances

Module 05 (portail statique de base).

## Périmètre

**Dans le périmètre :** l'expérience de recherche/filtres sur le portail public, quelle que soit l'option retenue ci-dessous.

**Hors périmètre :** la sauvegarde de recherches types en alertes personnalisées (module 10, mais dépend du modèle de données défini ici).

## Points à trancher avant de coder (bloquant — ce module ne peut pas commencer sans réponse)

La justification du choix de DSQL dans CLAUDE.md ("recherches multi-critères combinables... sans service de recherche additionnel") suggère une recherche **dynamique côté serveur contre DSQL**, mais le reste de l'architecture insiste sur "portail public statique, sans serveur permanent". Trois options réellement différentes :

1. **Index de recherche statique côté client** (ex. Pagefind/Lunr, généré au build par le module 05, chargé en JS par le navigateur). 100% cohérent avec "aucun serveur" ; limité en volume (des dizaines de milliers d'AO commencent à être lourds pour un index client) et ne permet pas de filtrer par des critères non indexés au build sans reconstruire l'index.
2. **API de lecture publique serverless** (API Gateway + Lambda + DSQL, **sans authentification Cognito** puisque c'est un accès public, avec rate-limiting/anti-scraping — voir PRD §5 "Protection contre l'extraction automatisée non autorisée"). Reste "sans serveur permanent" au sens de CLAUDE.md (Lambda éphémère), mais introduit une deuxième chaîne applicative distincte de celle du back-office, avec ses propres considérations de sécurité (accès anonyme à DSQL, quotas).
3. **Pages de collection pré-générées pour les combinaisons de filtres les plus fréquentes** (ex. `/secteur/btp/pays/togo`) + recherche texte simple côté client. Ne couvre pas les filtres réellement combinables à la volée (contredit la justification DSQL du CLAUDE.md), mais reste le plus simple et le plus proche de l'esprit "statique" du reste de l'architecture.

**Cette décision doit être posée explicitement à l'utilisateur avant de coder quoi que ce soit ici** — elle a un impact direct sur le coût (Lambda vs CDN pur), la sécurité (accès public à DSQL ou non) et la cohérence avec le principe "pas de serveur permanent" du CLAUDE.md. Recommandation à formuler au moment venu : l'option 2 est probablement celle qui honore le mieux l'intention du CLAUDE.md (qui justifie explicitement le choix de DSQL par ce besoin), à condition de bien la présenter comme une chaîne "lecture publique" strictement séparée de la chaîne "back-office" (nouveau rôle Lambda dédié, nouvelles IAM policies, jamais de mélange avec `lambda_tenders_api`).

## À construire (une fois l'option tranchée)

- Selon l'option retenue : générateur d'index (1), nouvelle Lambda + API Gateway publique + rôle IAM dédié (2), ou nouvelles pages de collection dans le module 05 (3).
- UI de filtres côté `frontend-public/` (secteur, région, montant, procédure, deadline, statut), tri (pertinence/date de publication/date limite).
- Mécanisme de "sauvegarde de recherche" côté abonné (nécessite le module 08 pour l'identité) — au moins la modélisation des critères sauvegardés, même si l'alerte elle-même est module 10.

## Définition de "terminé"

- Un visiteur peut combiner au moins secteur + région + statut et obtenir des résultats corrects.
- Le comportement anti-scraping (PRD §5) est en place si l'option 2 est retenue (rate limiting a minima).
- Un abonné connecté peut sauvegarder une recherche (persistée, même si l'alerte n'est pas encore branchée).
