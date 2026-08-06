# PRD — OptiProcure
### Plateforme sécurisée de publication des appels d'offres et marchés
Document de référence produit — synthèse des spécifications v1.0 (juillet 2026) et du workflow de publication stratégique v2.0 (août 2026). Pour la vision et le positionnement stratégique, voir `VISION.md`. Pour les conventions techniques et l'architecture détaillée destinées au développement, voir `CLAUDE.md`.

---

## 1. Objectifs de la plateforme

- Centraliser la publication des appels d'offres et marchés dans un format structuré et complet.
- Garantir la fiabilité du contenu grâce à une publication exclusivement assurée par l'équipe éditoriale (pas d'agrégation automatisée non modérée).
- Sécuriser l'accès aux données sensibles ou à forte valeur via un système d'abonnement.
- Offrir des alertes personnalisées pour que chaque abonné reçoive uniquement les opportunités pertinentes pour son secteur.
- Poser les bases techniques d'une plateforme évolutive (import automatisé, API, application mobile à terme).

## 2. Portails et utilisateurs

Deux portails distincts, même backend, interfaces et accès séparés :

- **Portail public** : consultation des AO, recherche et filtres, création de compte en libre-service, gestion de l'abonnement, espace personnel abonné.
- **Portail privé (back-office)** : accessible uniquement à l'équipe éditoriale via authentification renforcée (Cognito + MFA), dédié à la saisie, la révision, la publication et la gestion de la plateforme. Aucune fonctionnalité de gestion n'est exposée côté public.

### 2.1 Profils côté portail public

| Rôle | Accès et permissions | Objectif |
|---|---|---|
| Administrateur | Création, édition, publication, clôture et archivage des AO ; gestion des abonnés et des paiements ; statistiques et modération | Garantir l'exactitude et la fiabilité du contenu publié |
| Abonné (Standard/Premium) | Consultation des fiches complètes, alertes personnalisées, téléchargement des documents, tableau de bord | Recevoir l'information pertinente selon son secteur |
| Visiteur non-inscrit | Consultation vitrine limitée (titres, secteurs, dates), incitation à l'abonnement | Découverte de la plateforme |

### 2.2 Rôles côté back-office (workflow éditorial)

Le rôle « Administrateur » ci-dessus se décompose, côté flux de travail interne, en trois rôles Cognito distincts :

| Rôle | Droits principaux | Restrictions |
|---|---|---|
| AGENT | Créer et modifier ses brouillons ; soumettre à révision | Ne peut ni approuver ni publier |
| REVIEWER | Réviser, commenter et retourner un AO | Ne gère pas les utilisateurs |
| ADMIN | Approuver, superviser les batches et traiter les exceptions | MFA obligatoire |

## 3. Fonctionnalités détaillées

### 3.1 Publication des appels d'offres (back-office)

Formulaire de saisie structuré couvrant l'ensemble des champs nécessaires à la compréhension et à la réponse à un marché (voir table des champs ci-dessous).

**Cycle de statut d'une fiche** : `brouillon → publié → clôturé (ou annulé) → archivé`. Toute modification postérieure à la publication (report de délai, rectificatif, addenda) est tracée dans un historique visible par les abonnés concernés.

**Workflow éditorial détaillé** menant à l'état « publié » : un AGENT crée/modifie un brouillon et le soumet à révision → un REVIEWER révise, commente et peut retourner l'AO à l'agent → un ADMIN approuve → l'AO approuvé entre dans le batch de publication planifié suivant (voir §9, Workflow de publication).

### 3.2 Champs d'une fiche appel d'offres

| Champ | Description |
|---|---|
| Référence | Identifiant unique généré par la plateforme |
| Titre de l'appel d'offres | Intitulé complet et explicite |
| Acheteur public / privé | Nom de l'entité qui lance le marché |
| Secteur d'activité | BTP, informatique, santé, énergie, transport, etc. |
| Type de marché | Travaux, fournitures, services, prestations intellectuelles |
| Type de procédure | Appel d'offres ouvert, restreint, gré à gré, consultation, concours |
| Montant estimé | Fourchette budgétaire ou montant indicatif si disponible |
| Zone géographique / lieu d'exécution | Région, ville ou pays concerné |
| Date de publication | Date de mise en ligne sur OptiProcure |
| Date limite de dépôt | Date et heure limites de soumission des offres |
| Critères d'éligibilité | Qualifications, agréments, chiffre d'affaires minimal, etc. |
| Pièces à fournir | Liste des documents administratifs et techniques exigés |
| Documents joints | Dossier d'appel d'offres (DAO), cahier des charges, annexes |
| Contact / point focal | Nom, fonction, email, téléphone du responsable du dossier |
| Source officielle | Lien vers le journal officiel ou le site de l'acheteur |
| Statut | Brouillon, publié, en cours, clôturé, annulé, archivé |
| Historique / addenda | Modifications, reports de délai, rectificatifs |

### 3.3 Fiche détail d'un appel d'offres

- Affichage structuré de toutes les informations ci-dessus, avec mise en avant du délai restant avant la date limite de dépôt.
- Téléchargement des documents joints réservé aux abonnés selon leur plan.
- Historique des modifications et addenda affiché de façon chronologique.
- Fil d'ariane et navigation vers les appels d'offres similaires (même secteur ou même acheteur).

### 3.4 Moteur de recherche et filtres

- Recherche par mots-clés (titre, référence, acheteur).
- Filtres combinables : secteur d'activité, région, montant, type de procédure, date limite, statut.
- Sauvegarde de recherches types, transformables en alertes personnalisées.
- Tri des résultats par pertinence, date de publication ou date limite de dépôt.

### 3.5 Alertes et notifications

- Alertes par email (et SMS pour les plans supérieurs) déclenchées par les critères sauvegardés par l'abonné.
- Fréquence configurable : synthèse quotidienne (après le cycle de publication journalier) ou résumé hebdomadaire.
- Notification automatique en cas de modification d'un AO suivi (report de délai, annulation, addenda).
- Notification de fin d'abonnement à venir et de renouvellement.

### 3.6 Espace abonné

- Création de compte en libre-service (inscription, vérification d'email, choix du plan) sans intervention de l'administrateur.
- Tableau de bord personnel : AO suivis, favoris, alertes actives, historique de consultation.
- Gestion du profil (secteurs d'intérêt, zones géographiques) pour affiner les recommandations.
- Gestion de l'abonnement et de la facturation (factures téléchargeables, moyen de paiement, historique des transactions).

### 3.7 Back-office administrateur

- Gestion complète du cycle de vie des AO (création, édition, publication, clôture, archivage).
- Supervision des abonnés : comptes créés en libre-service, suivi des abonnements, gestion des impayés, suspension/réactivation, support client.
- Statistiques de consultation, taux de conversion visiteur → abonné, AO les plus consultés.
- Journal d'audit des actions administratives (traçabilité).

## 4. Abonnements et modèle économique

Trois formules pour couvrir différents profils, du visiteur découvrant la plateforme à l'entreprise structurée. Tarifs indicatifs, à valider par étude de marché.

| | Découverte (Gratuit) | Standard | Premium / Entreprise |
|---|---|---|---|
| Accès aux fiches d'AO | Résumé limité (titre, secteur, date limite) | Fiche complète | Fiche complète + historique/addenda |
| Nombre d'alertes personnalisées | 1 alerte, fréquence hebdomadaire | 5 alertes, fréquence quotidienne | Alertes illimitées, synthèse quotidienne |
| Filtres avancés | Filtres de base | Tous les filtres | Tous les filtres + export |
| Téléchargement des documents | Non | Oui | Oui, illimité |
| Utilisateurs par compte | 1 | 1 | Jusqu'à 5 (multi-utilisateurs) |
| Support client | Email (standard) | Email prioritaire | Dédié + accompagnement |
| Export des données (Excel/PDF) | Non | Limité | Illimité |
| Tarif indicatif (à valider) | 0 F CFA | à définir / mois | à définir / mois ou sur devis |

Le paiement en ligne (carte bancaire, mobile money selon la zone géographique) permet un renouvellement automatique et une gestion simplifiée du cycle de vie de l'abonnement (essai gratuit, relance avant expiration, suspension, réactivation).

## 5. Sécurité (exigences produit)

- Authentification renforcée pour les comptes administrateur (MFA obligatoire pour ADMIN, recommandé pour AGENT/REVIEWER).
- Chiffrement des données en transit (HTTPS/TLS) et au repos pour les données sensibles.
- Contrôle d'accès basé sur les rôles (RBAC) : AGENT / REVIEWER / ADMIN côté back-office, Administrateur / Abonné / Visiteur côté portail public.
- Journalisation des accès et des actions sensibles : connexions, refus d'accès, modifications, approbations, publications.
- Sauvegardes régulières et plan de reprise après incident.
- Protection contre l'extraction automatisée non autorisée du contenu (anti-scraping) et surveillance des tentatives de fraude sur les paiements.
- Conformité aux exigences applicables en matière de protection des données personnelles.

*(Le détail technique de l'implémentation — Cognito, JWT, IAM, fédération OIDC — est spécifié dans `CLAUDE.md`.)*

## 6. Cycle de publication

Le contenu n'est pas mis à jour en temps réel : les nouveaux AO et modifications sont saisis au fil de la journée, puis consolidés et publiés selon un **cycle quotidien unique**. Aucun build/publication n'est déclenché si aucun AO n'a été créé, modifié ou nouvellement expiré. Ce choix simplifie l'architecture et réduit les coûts, sans nuire à l'utilité du service — la plupart des AO laissant plusieurs jours à semaines de délai de dépôt. Cette cadence pourra être révisée si un besoin de réactivité plus fine apparaît (ex. alerte immédiate sur un marché à très court délai).

## 7. Feuille de route et phases de déploiement

| Phase | Contenu | Objectif |
|---|---|---|
| Phase 1 — MVP | Publication manuelle des AO, fiche détaillée, recherche/filtres de base, inscription et abonnement Standard, alertes email | Valider le besoin et générer les premiers abonnés |
| Phase 2 — Consolidation | Paiement en ligne automatisé, alertes multi-canal (email + SMS), tableau de bord abonné, back-office admin complet | Fiabiliser le modèle économique et l'expérience utilisateur |
| Phase 3 — Extension | Application mobile, API pour partenaires, import automatisé depuis sources officielles, export de données avancé, statistiques sectorielles | Étendre la portée et la valeur ajoutée de la plateforme |

## 8. Indicateurs de succès (KPI)

- Nombre d'appels d'offres publiés par mois et par secteur.
- Nombre d'inscriptions et taux de conversion visiteur → abonné payant.
- Taux de rétention et de renouvellement des abonnements.
- Taux d'ouverture et de clic des alertes envoyées.
- Délai moyen entre la publication d'un marché source et sa mise en ligne sur OptiProcure.

## 9. Positionnement face à la concurrence

Des acteurs comme WuriPay ou les agrégateurs internationaux (J360, dgMarket) couvrent déjà la veille des marchés publics en Afrique de l'Ouest, y compris au Togo. Leur modèle d'agrégation automatisée de sources publiques ouvertes limite structurellement leur capacité à couvrir les AO privés. OptiProcure élargit délibérément son périmètre aux AO privés via un réseau professionnel direct, transformé progressivement en circuits de diffusion formalisés avec des entreprises partenaires (point focal, convention de diffusion, canal de transmission dédié, contrepartie de valeur, élargissement du portefeuille). Voir `VISION.md` pour le détail stratégique.

## 10. Sources de veille disponibles au Togo

| Source | Type | Lien / accès | Fréquence de veille recommandée |
|---|---|---|---|
| ARCOP (ex-ARMP) | Régulateur national | arcop.tg | Hebdomadaire |
| DNCCP (ex-DNCMP) | Contrôle des marchés publics | Via ARCOP / communiqués officiels | Hebdomadaire |
| Journal Officiel de la République Togolaise | Textes réglementaires | jo.gouv.tg | Mensuelle |
| Portail des services publics togolais | Démarches liées aux marchés publics | service-public.gouv.tg | Mensuelle |
| e-SIGMAP / stratégie e-GP (déploiement en cours) | Système intégré de gestion électronique des marchés | Statut évolutif, appuyé par la Banque mondiale | À surveiller (veille de statut) |
| Sites des autorités contractantes | Publication directe des avis d'AO | Ex. Office Togolais des Recettes (otr.tg) | Quotidienne à hebdomadaire |
| Presse locale et journal officiel imprimé | Publication légale des avis | Togo First, République Togolaise, Togo-Presse | Hebdomadaire |
| Bailleurs de fonds internationaux | Marchés financés par des projets de développement | Portails propres (Banque mondiale, BAD, AFD, PNUD, UEMOA) | Hebdomadaire |
| Agrégateurs privés spécialisés Afrique francophone | Veille consolidée multi-pays | Ex. j360.info | Quotidienne |

Point d'attention : le Togo a engagé depuis fin 2025 la digitalisation de la passation des marchés publics (stratégie e-GP), avec l'appui de la Banque mondiale, et fait partie des pays de l'UEMOA où l'e-SIGMAP est déployé. Si ce portail devient pleinement public et régulièrement mis à jour, il pourra constituer une source structurée exploitable via import automatisé ou API en Phase 3. En attendant, la publication directe par chaque autorité contractante et la presse économique locale restent les canaux les plus fiables au jour le jour.

## 11. Glossaire

- **Appel d'offres (AO)** : procédure par laquelle un acheteur public ou privé sollicite des offres pour la réalisation de travaux, fournitures ou services.
- **Gré à gré** : procédure de passation sans mise en concurrence formelle, encadrée par des seuils réglementaires.
- **DAO** : dossier d'appel d'offres, regroupant l'ensemble des documents nécessaires à la soumission d'une offre.
- **Addenda** : document rectificatif modifiant ou complétant un AO déjà publié.

## 12. Prochaines étapes suggérées

- Valider la grille tarifaire des abonnements avec une étude de positionnement concurrentiel.
- Prioriser le périmètre du MVP (Phase 1) en fonction des ressources disponibles.
- Définir la charte graphique et l'expérience utilisateur détaillée (maquettes).
- Choisir les technologies précises et le prestataire d'hébergement.
