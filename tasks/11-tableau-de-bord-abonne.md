# Module 11 — Tableau de bord abonné

> Espace personnel de l'abonné : AO suivis/favoris, historique de consultation, alertes actives, factures et historique de paiement.

## Objectif

PRD §3.6 : "Tableau de bord personnel : AO suivis, favoris, alertes actives, historique de consultation" + "Gestion de l'abonnement et de la facturation (factures téléchargeables, moyen de paiement, historique des transactions)".

## Références

- PRD §3.6, §4 (export Excel/PDF selon plan — Non/Limité/Illimité)
- Modules 08 (identité), 09 (abonnement/paiement), 10 (alertes — table `saved_searches`/`tracked_tenders` définie là ou ici, à ne pas dupliquer)

## Dépendances

Module 08, 09. Idéalement après 10 (réutilise son modèle de données de recherches/AO suivis) mais peut être développé en parallèle si le modèle de données est convenu à l'avance entre les deux modules.

## Périmètre

**Dans le périmètre :**
- Vue "AO suivis" et "favoris" (probablement la même notion, `tracked_tenders` — à clarifier : PRD distingue "AO suivis" et "favoris" comme deux items séparés dans la liste du tableau de bord, donc potentiellement deux tables ou un champ de distinction, **à trancher**).
- Historique de consultation (nouvelle table à définir — aucune trace de vues actuellement, à concevoir sobrement : pas de temps réel, un enregistrement simple suffit).
- Liste des alertes actives avec activation/désactivation (lecture/écriture sur `saved_searches` du module 10).
- Historique des transactions et factures téléchargeables (lecture `payments`/`subscriptions` — génération de facture PDF à la volée ou stockage S3 au moment du paiement, **à trancher**).
- Export de données (Excel/PDF) selon plan — quota à vérifier via `subscription_plans.features`.

## Points à trancher avant de coder

1. **"AO suivis" vs "favoris"** : une seule table avec un type (`FOLLOWED`/`FAVORITE`), ou deux tables distinctes ? Impacte le modèle de données du module 10 également.
2. **Génération de facture** : PDF généré à la demande (Lambda, à partir des données `payments`) vs stocké définitivement à S3 au moment du paiement (immuable, plus proche d'une exigence comptable réelle) — la deuxième option est probablement plus sûre si des obligations légales de facturation s'appliquent (à vérifier, hors compétence technique).
3. **Historique de consultation** : quel niveau de détail (juste "AO vu" avec timestamp, ou trace plus riche) ? Rester minimal par défaut (pas de sur-ingénierie) sauf besoin produit explicite.

## Définition de "terminé"

- Un abonné voit ses AO suivis/favoris, son historique de consultation récent, ses alertes actives (avec toggle), son historique de paiement.
- Un export PDF/Excel respecte le quota de son plan (refus clair si non autorisé, pas un simple bouton désactivé sans explication).
