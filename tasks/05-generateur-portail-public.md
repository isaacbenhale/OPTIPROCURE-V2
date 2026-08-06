# Module 05 — Générateur du portail public (`frontend-public/`)

> Site Next.js statique (fiches AO, pages de collection, SEO) généré à partir du manifeste du module 04 — reconstruction ciblée, pas un rebuild complet à chaque changement.

## Objectif

Construire le site Next.js statique consommé par S3+CloudFront (CLAUDE.md : "Next.js / générateur Node.js — Génération des pages statiques et des métadonnées SEO"). Consomme le manifeste produit par le module 04 pour ne reconstruire que les pages réellement affectées ("génération ciblée", pas un rebuild complet à chaque changement).

## Références

- CLAUDE.md : table de décision changement → action (nouvel AO / AO modifié / AO expiré / aucun changement), section "Deux workflows distincts à maintenir"
- PRD §3.3 (fiche détail AO), §2.1 (profils Visiteur/Abonné — accès vitrine limité vs fiche complète)
- `infra/terraform/s3_cloudfront.tf` : bucket `public_site`, distribution CloudFront, OAC

## Dépendances

Module 04 (manifeste). Le module 07 (recherche) et le module 09 (abonnements, pour la logique "vitrine limitée vs fiche complète") viennent après ou en parallèle serré.

## Périmètre

**Dans le périmètre :**
- Génération de la fiche détail d'un AO (PRD §3.3) : affichage structuré, délai restant avant deadline, historique/addenda (lecture de `tender_status_history`), AO similaires (même secteur/acheteur).
- Génération des pages de liste/collection (par catégorie, pays, organisation) et de leur pagination statique.
- Génération du `sitemap.xml` et des métadonnées SEO (title/description/OG par page).
- Distinction visiteur non-inscrit (vitrine limitée : titre, secteur, dates) vs abonné (fiche complète) — **dépend du module 09** pour l'authentification abonné ; en attendant ce module, la fiche complète peut être générée mais l'accès aux champs sensibles gated côté build est un choix à trancher (voir ci-dessous).
- Consommation du manifeste : ne régénérer que les pages listées (AO créés/modifiés/expirés + collections affectées), pas un rebuild intégral.

**Hors périmètre :**
- Le pipeline GitHub Actions qui invoque ce générateur et déploie sur S3/CloudFront (module 06).
- La recherche/filtres interactifs (module 07 — question d'architecture propre, voir ce fichier).
- Le tableau de bord abonné (module 11).

## Points à trancher avant de coder

1. **Source de données au moment du build** : le générateur lit-il directement Aurora DSQL (nécessite alors une Lambda ou un accès IAM depuis le runner GitHub Actions — connexion DSQL n'est pas conçue pour être appelée depuis un runner externe sans identité IAM dédiée), ou consomme-t-il un export JSON déjà produit par le Publication Coordinator (module 04) et déposé dans S3 avec le manifeste ? La deuxième option est plus cohérente avec le découplage "identité/logique métier" vs "publication/diffusion" du CLAUDE.md (le runner GitHub Actions n'a jamais besoin de credentials DSQL) — à confirmer, ça change la portée du module 04 (qui devrait alors exporter les données, pas seulement la liste des changements).
2. **Fiche complète vs vitrine limitée sans le module 09 encore construit** : générer deux versions de chaque page dès maintenant (gated par un script client-side vérifiant un token abonné — cohérent avec un site 100% statique), ou différer cette distinction et publier des fiches complètes pour tout le monde en attendant le module 09 (plus rapide à livrer, mais fuite d'information vis-à-vis du modèle économique) ?

## Définition de "terminé"

- Un AO PUBLISHED génère une page statique valide (HTML + métadonnées SEO correctes, testable via un validateur SEO basique).
- Un AO EXPIRED reconstruit sa page avec le statut affiché, sans être supprimée.
- Le sitemap reflète l'ensemble des pages publiées.
- Un build ne régénère que les fichiers listés dans le manifeste (vérifiable par les timestamps de fichiers de sortie).
