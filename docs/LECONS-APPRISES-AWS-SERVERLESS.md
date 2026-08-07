# Leçons apprises — AWS serverless (Lambda, Cognito, API Gateway, Aurora DSQL, Terraform)

> Document généraliste, pensé pour être réutilisé tel quel dans d'autres projets AWS serverless — pas spécifique à OptiProcure. Chaque entrée suit le même format : **Symptôme → Cause réelle → Correctif → Règle générale à appliquer d'emblée**, pour éviter de reperdre du temps à rediagnostiquer le même problème.

## Sommaire

1. [Build Lambda sur Apple Silicon → binaire incompatible](#1-build-lambda-sur-apple-silicon--binaire-incompatible)
2. [`sslrootcert="system"` échoue en runtime Lambda zip](#2-sslrootcertsystem-échoue-en-runtime-lambda-zip)
3. [Aurora DSQL : `CREATE INDEX` synchrone non supporté](#3-aurora-dsql--create-index-synchrone-non-supporté)
4. [Aurora DSQL : `CHECK` impossible après création de table](#4-aurora-dsql--check-impossible-après-création-de-table)
5. [Runner de migration non idempotent](#5-runner-de-migration-non-idempotent)
6. [Collisions de modules pytest entre répertoires de test](#6-collisions-de-modules-pytest-entre-répertoires-de-test)
7. [CORS API Gateway : origine vs URL de callback](#7-cors-api-gateway--origine-vs-url-de-callback)
8. [IAM requis même pour un appel « authentifié par le token utilisateur »](#8-iam-requis-même-pour-un-appel--authentifié-par-le-token-utilisateur-)
9. [Claims multi-valeurs (`cognito:groups`) mal formatés par API Gateway](#9-claims-multi-valeurs-cognitogroups-mal-formatés-par-api-gateway)
10. [Boucle de redirection auth invisible côté SPA](#10-boucle-de-redirection-auth-invisible-côté-spa)
11. [Scope OAuth manquant pour les appels Cognito self-service](#11-scope-oauth-manquant-pour-les-appels-cognito-self-service)
12. [Cognito Hosted UI rejette certaines combinaisons de scopes](#12-cognito-hosted-ui-rejette-certaines-combinaisons-de-scopes)
13. [GRANT Postgres incomplet sur un rôle dédié par Lambda](#13-grant-postgres-incomplet-sur-un-rôle-dédié-par-lambda)
14. [Course entre déconnexion et redirection automatique côté SPA](#14-course-entre-déconnexion-et-redirection-automatique-côté-spa)
15. [Verrou anti-boucle jamais réinitialisé après un succès](#15-verrou-anti-boucle-jamais-réinitialisé-après-un-succès)

---

## 1. Build Lambda sur Apple Silicon → binaire incompatible

**Symptôme** : la Lambda plante au runtime (`Runtime.ImportModuleError` ou erreur `psycopg2`/toute dépendance avec extension native), alors que le build local et les tests passent.

**Cause réelle** : `pip install` sur un Mac Apple Silicon produit des wheels `arm64`. Les Lambda x86_64 (le défaut le plus courant) ne peuvent pas les charger. Docker sans `--platform` explicite hérite de l'architecture de l'hôte.

**Correctif** : forcer `--platform linux/amd64` sur la commande `docker run` qui installe les dépendances dans l'image `public.ecr.aws/sam/build-python3.12` (ou équivalent), **indépendamment** de l'architecture de la machine qui lance le build.

**Règle générale** : sur tout projet avec des devs Apple Silicon et des Lambdas x86_64, épingler `--platform linux/amd64` dans le Makefile/script de build dès le premier jour — ne pas attendre l'échec en prod pour le découvrir. (Alternative valable : passer les Lambdas en `arm64` — mais c'est un choix d'archi à trancher explicitement, pas un contournement silencieux.)

---

## 2. `sslrootcert="system"` échoue en runtime Lambda zip

**Symptôme** : connexion Postgres/Aurora échoue uniquement en Lambda (jamais en local), avec une erreur liée au magasin de certificats CA.

**Cause réelle** : `sslrootcert="system"` suppose un magasin de certificats OS à un emplacement standard (`/etc/ssl/certs/...`). Un runtime Lambda zip n'a pas cette arborescence.

**Correctif** : vendoriser `certifi` dans le package Lambda et pointer `sslrootcert=certifi.where()` explicitement.

**Règle générale** : pour toute connexion TLS sortante (DB, API tierce) depuis une Lambda packagée en zip (pas de layer géré par AWS), ne jamais compter sur un magasin de certificats système — toujours vendoriser `certifi` par défaut.

---

## 3. Aurora DSQL : `CREATE INDEX` synchrone non supporté

**Symptôme** : `FeatureNotSupported: unsupported mode. please use CREATE INDEX ASYNC.` — y compris sur une table vide.

**Cause réelle** : Aurora DSQL ne supporte **aucune** forme de `CREATE INDEX`/`CREATE UNIQUE INDEX` synchrone, quelle que soit la taille de la table.

**Correctif** : toujours `CREATE INDEX ASYNC` / `CREATE UNIQUE INDEX ASYNC`. Suivre l'avancement via `sys.jobs` si besoin de savoir quand l'indexation est terminée avant de s'appuyer dessus (ex. avant d'activer une contrainte d'unicité applicative qui en dépend).

**Règle générale** : sur tout nouveau projet Aurora DSQL, grep le schéma pour tout `CREATE (UNIQUE )?INDEX` sans `ASYNC` avant même de lancer la première migration — c'est systématique, pas un cas limite.

---

## 4. Aurora DSQL : `CHECK` impossible après création de table

**Symptôme** : `ALTER TABLE ... ADD COLUMN ... CHECK (...)` et `ALTER TABLE ... ADD CONSTRAINT ... CHECK (...)` échouent tous les deux avec `FeatureNotSupported`, alors que `CREATE TABLE ... CHECK (...)` fonctionne très bien.

**Cause réelle** : DSQL ne supporte les contraintes `CHECK` qu'au moment de la création de la table — jamais en `ALTER TABLE`, quelle que soit la forme.

**Correctif** : toute colonne à valeurs énumérées ajoutée après coup (migration tardive) doit être validée **côté application** (Lambda métier), jamais en base — cohérent de toute façon avec l'absence de FK/TRIGGER/VIEW sur DSQL (voir principe général ci-dessous).

**Règle générale** : sur DSQL, si une contrainte `CHECK` est nécessaire sur une colonne ajoutée après la création de la table, ne même pas essayer l'`ALTER TABLE` — écrire directement la validation dans le code applicatif.

**Principe DSQL plus large à garder en tête sur tout projet** : pas de FK, pas de TRIGGER, pas de VIEW, 1 seule instruction DDL par transaction (jamais mélangée à du DML), contrôle de concurrence optimiste (retry sur SQLSTATE `40001`), connexion IAM uniquement (`DsqlSigner`, pas d'identifiants statiques). Revérifier les release notes DSQL avant de s'appuyer sur une fonctionnalité non testée explicitement — service jeune et évolutif.

---

## 5. Runner de migration non idempotent

**Symptôme** : après un échec partiel (ex. coupure réseau en plein lot de migrations), relancer le runner échoue avec `DuplicateTable`/`DuplicateObject` sur les migrations déjà appliquées.

**Cause réelle** : le runner exécutait toutes les migrations du dossier à chaque invocation, sans mémoriser ce qui avait déjà été appliqué avec succès.

**Correctif** : table `schema_migrations` (clé = nom de fichier), le runner ne rejoue que les fichiers absents de cette table. Pour la reprise après un état déjà partiellement appliqué (ex. bootstrap), traiter les erreurs « objet existe déjà » (`DuplicateTable`, `DuplicateObject`, etc. — lister les SQLSTATE concernés) comme un succès idempotent plutôt qu'une erreur fatale.

**Règle générale** : tout runner de migration doit être conçu idempotent et rejouable dès la première version — ne pas attendre le premier échec en prod pour l'ajouter. C'est un aller simple : personne ne revient en arrière une fois que la table de suivi existe.

---

## 6. Collisions de modules pytest entre répertoires de test

**Symptôme** : `pytest` échoue à la collecte avec une erreur d'import ambiguë quand plusieurs services (plusieurs Lambdas dans un même repo) ont des fichiers de test au même nom (`conftest.py`, `test_db_retry.py`, etc.) sans `__init__.py`.

**Cause réelle** : le mode d'import par défaut de pytest (`prepend`) enregistre les modules par nom de fichier seul dans `sys.modules` — deux `conftest.py` dans des dossiers différents entrent en collision.

**Correctif** : `addopts = --import-mode=importlib` dans `pytest.ini`, plus s'assurer que chaque `conftest.py` ajoute son propre répertoire à `sys.path` si des fichiers de test font `from conftest import X` (le mode importlib ne le fait plus implicitement).

**Règle générale** : dès qu'un repo a plus d'un service Python testé avec pytest (mono-repo multi-Lambda), mettre `--import-mode=importlib` dans le `pytest.ini` racine avant même que la collision arrive — c'est mécanique, pas dépendant du code.

---

## 7. CORS API Gateway : origine vs URL de callback

**Symptôme** : le navigateur bloque les requêtes vers l'API avec une erreur CORS, alors que la configuration `cors_configuration` de l'API Gateway existe bel et bien et semble correcte à première lecture.

**Cause réelle** : `allow_origins` avait été rempli avec les URLs de callback OAuth complètes (`https://exemple.com/callback`), pas les origines seules (`https://exemple.com`). CORS ne fonctionne que sur l'origine — schéma + host + port, jamais avec un chemin.

**Correctif** : dériver une liste d'origines à partir des callback URLs via une regex (`^[a-zA-Z]+://[^/]+`) plutôt que de dupliquer une liste séparée à maintenir à la main.

**Règle générale** : ne jamais réutiliser directement une liste d'URLs de callback OAuth comme `allow_origins` CORS — toujours en extraire l'origine. Vérifier avec `curl -X OPTIONS` en simulant l'`Origin` réel avant de blâmer autre chose (JWT, IAM...).

---

## 8. IAM requis même pour un appel « authentifié par le token utilisateur »

**Symptôme** : un appel `cognito-idp:GetUser` (ou toute action `cognito-idp:*` self-service) échoue par déni d'accès depuis une Lambda, alors que l'access token utilisateur passé en paramètre est valide et que le rôle IAM de la Lambda ne semble a priori pas concerné (« c'est le token qui authentifie, pas IAM »).

**Cause réelle** — erreur de raisonnement fréquente à éviter : **boto3 signe toujours la requête en SigV4 avec les identifiants IAM du contexte d'exécution**, même quand l'action elle-même prend un jeton utilisateur en paramètre (`AccessToken=...`). IAM évalue donc systématiquement l'action pour le rôle appelant, en plus de la validité du token. Ce n'est pas comparable à un appel direct depuis un navigateur (non signé, authentifié par le seul token).

**Correctif** : ajouter explicitement la permission IAM sur le rôle Lambda (`cognito-idp:GetUser`, scopée à l'ARN du User Pool concerné — pas de wildcard).

**Règle générale** : pour **tout** appel boto3 fait depuis une Lambda vers un service AWS — même une API "self-service" qui prend un jeton utilisateur en paramètre — supposer par défaut qu'IAM doit autoriser l'action sur le rôle d'exécution. Ne jamais partir du principe qu'un paramètre de type token dispense de la permission IAM ; vérifier la doc du service ou tester directement plutôt que de le supposer.

---

## 9. Claims multi-valeurs (`cognito:groups`) mal formatés par API Gateway

**Symptôme** : un utilisateur appartenant clairement au bon groupe Cognito (visible dans le payload JWT brut décodé) se voit refuser l'accès côté Lambda avec une erreur du type « utilisateur sans groupe/rôle reconnu ».

**Cause réelle** : le JWT Authorizer HTTP API d'API Gateway transmet les claims de type liste (`cognito:groups`) dans `event.requestContext.authorizer.jwt.claims` sous forme de **chaîne texte entourée de crochets** (`"[ADMIN]"`, ou `"[AGENT, ADMIN]"` pour plusieurs groupes) — pas en JSON natif, pas en CSV nu. Un parsing qui suppose un simple `.split(",")` sur la chaîne brute rate silencieusement ce format et traite l'utilisateur comme n'ayant aucun groupe.

**Correctif** :
```python
def resolve_role_from_groups(claims: dict) -> str | None:
    groups_raw = claims.get("cognito:groups", "")
    stripped = groups_raw.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    groups = {g.strip() for g in stripped.split(",") if g.strip()}
    for role in ROLE_PRECEDENCE:
        if role in groups:
            return role
    return None
```

**Règle générale** : ne jamais supposer le format d'un claim multi-valeurs forwardé par un JWT Authorizer API Gateway sans le vérifier empiriquement (log de diagnostic sur une vraie requête, ou test d'intégration avec un vrai token). Le format « array JSON natif dans le JWT lui-même » ≠ « format transmis par API Gateway dans `event` » — API Gateway le re-sérialise en texte, et ce format n'est pas garanti stable/documenté de façon fiable dans le temps.

---

## 10. Boucle de redirection auth invisible côté SPA

**Symptôme** : une SPA avec auth OAuth (Cognito Hosted UI, Auth0, etc.) oscille indéfiniment entre l'écran de login et le callback, sans jamais atterrir sur un état connecté ni afficher une vraie erreur à l'écran.

**Cause réelle** — un anti-pattern à repérer systématiquement dans tout code d'auth SPA :
1. Une fonction de chargement du profil utilisateur (`loadCurrentUser`) avale silencieusement ses erreurs (`try { ... } catch { setUser(null) }`) — conçu pour un usage précis (chargement initial silencieux au montage de l'app), mais réutilisé tel quel dans le chemin du callback OAuth, où une erreur DOIT être visible.
2. La page de callback navigue vers la zone protégée **même en cas d'échec**, parce que la fonction ci-dessus ne relance jamais l'erreur.
3. Le garde de route protégée (`RequireAuth`) redirige alors vers `/login`.
4. La page de login relance la redirection OAuth **inconditionnellement à chaque montage**, sans jamais vérifier si on vient déjà d'échouer.

Résultat : n'importe quelle erreur — même transitoire, même un vrai bug de config qui devrait être visible immédiatement — déclenche une boucle silencieuse et invisible, indiscernable d'un simple problème réseau pour qui debug de l'extérieur.

**Correctif** :
- Dans le chemin du callback, ne **pas** réutiliser la fonction « silencieuse » du montage initial — appeler l'API directement et laisser l'erreur remonter jusqu'au composant de callback, qui l'affiche.
- Sur la page de login, détecter la boucle (ex. horodatage en `sessionStorage`, fenêtre de quelques secondes) : si on revient sur `/login` juste après une tentative, **arrêter** la redirection automatique et afficher un message d'erreur réel + un bouton d'action manuelle, plutôt que de reboucler.

**Règle générale** : sur toute SPA avec redirection OAuth automatique, ne jamais avoir de `useEffect` qui redirige inconditionnellement sans casse-boucle. Traiter « avaler une erreur silencieusement » comme un choix à justifier explicitement à chaque endroit où on le fait, jamais comme le comportement par défaut d'un chemin d'auth.

---

## 11. Scope OAuth manquant pour les appels Cognito self-service

**Symptôme** : un access token obtenu via le flux Hosted UI (Authorization Code + PKCE) échoue sur un appel `cognito-idp:GetUser` avec `NotAuthorizedException: Access Token does not have required scopes` — alors que le **même utilisateur**, authentifié directement via `USER_SRP_AUTH` (sans passer par le flux OAuth), obtient un token qui fonctionne parfaitement pour le même appel.

**Cause réelle** : les tokens émis via le flux OAuth Hosted UI sont scopés par le paramètre `scope` de la requête `/oauth2/authorize`. Le scope réservé `aws.cognito.signin.user.admin` doit être explicitement demandé (et autorisé sur le client d'app Cognito) pour que le token résultant puisse s'auto-interroger via les API self-service du User Pool (`GetUser`, `GetUserAttributeVerificationCode`, etc.). Un token issu de `USER_SRP_AUTH`/`ADMIN_USER_PASSWORD_AUTH` n'est **pas** soumis à cette restriction de scope OAuth — ce qui rend un test rapide via ces flows **faussement rassurant** si le vrai parcours utilisateur passe par le Hosted UI.

**Correctif** : ajouter `aws.cognito.signin.user.admin` à la fois dans `allowed_oauth_scopes` du client d'app Cognito **et** dans le paramètre `scope` envoyé par le frontend à `/oauth2/authorize`.

**Règle générale** : pour toute Lambda qui appelle une API `cognito-idp:*` self-service avec un token utilisateur obtenu via un flux OAuth Hosted UI, vérifier dès la conception que `aws.cognito.signin.user.admin` fait partie des scopes demandés — et **valider avec le vrai flux OAuth du navigateur**, pas seulement un token obtenu par un raccourci CLI (SRP direct), qui peut masquer ce genre de restriction.

---

## 12. Cognito Hosted UI rejette certaines combinaisons de scopes

**Symptôme** : `/oauth2/authorize` redirige vers `redirect_uri?error=invalid_request&error_description=invalid_scope`, alors que **chacun** des scopes demandés est individuellement présent dans `allowed_oauth_scopes` du client, et que des sous-ensembles de 3 scopes parmi les 4 fonctionnent très bien.

**Cause réelle constatée empiriquement** (non documentée de façon évidente côté AWS au moment du diagnostic) : demander simultanément `openid` + `email` + `profile` + `aws.cognito.signin.user.admin` (4 scopes) dans la même requête `/oauth2/authorize` était rejeté, alors que n'importe quel sous-ensemble de 3 de ces 4 scopes passait. Isolé par test binaire systématique (retirer un scope à la fois via `curl` direct sur `/oauth2/authorize`, observer le `Location` de la redirection).

**Correctif** : ne demander que les scopes réellement consommés par l'application. Ici, le frontend ne lisait jamais les claims `email`/`profile` de l'ID token (le backend récupère déjà ces informations via `GetUser`), donc ces deux scopes n'apportaient rien — réduit à `openid` (requis par le flux OIDC) + `aws.cognito.signin.user.admin` (requis pour `GetUser`).

**Règle générale** :
- Ne jamais demander un scope OAuth « au cas où » — n'en demander que ce que le code consomme réellement (claims lus côté frontend, ou permissions API réellement utilisées côté backend). Moins de scopes = moins de surface à ce genre de comportement inattendu, et principe du moindre privilège de toute façon.
- Si un `invalid_scope` apparaît avec des scopes individuellement valides, tester chaque sous-combinaison via `curl` direct sur `/oauth2/authorize` (pas besoin de navigateur ni de vrai login) avant de chercher ailleurs — la redirection d'erreur elle-même donne la réponse en quelques requêtes.

---

## 13. GRANT Postgres incomplet sur un rôle dédié par Lambda

**Symptôme** : une route API qui n'avait jamais été exercée jusque-là (ex. le tout premier `POST` d'écriture d'un nouveau module) échoue en `500 INTERNAL_ERROR`, alors que les routes de lecture du même module fonctionnent parfaitement depuis son déploiement.

**Cause réelle** : `psycopg2.errors.InsufficientPrivilege: permission denied for table X`. Chaque Lambda a un rôle Postgres dédié, non-admin, avec un `GRANT` explicite limité aux tables dont on pense qu'elle a besoin (bon principe de moindre privilège) — mais le `GRANT` initial a été écrit en pensant aux tables "métier" évidentes du module, en oubliant une table transversale utilisée incidemment par une fonction générique (typiquement `audit_log`, écrite par une fonction d'audit systématique, ou une table de jonction ajoutée dans un module ultérieur). Le bug est **silencieux jusqu'au premier appel réel de ce chemin de code** — ce n'est repéré ni en lecture, ni en test unitaire mocké, ni tant que personne n'exerce cette route précise en environnement réel. Constaté deux fois dans le même projet, sur deux rôles différents (`tenders_api_role` oubliant `tender_documents`, `reference_data_api_role` oubliant `audit_log`) : ce n'est pas un accident isolé, c'est un point faible structurel de l'approche "un rôle, un GRANT à la main".

**Correctif** : migration additive `GRANT SELECT, INSERT [, UPDATE] ON <table_oubliée> TO <role>;` — idempotente et rejouable comme toute migration DSQL (voir §5).

**Règle générale** :
- Au moment d'écrire le `GRANT` initial d'un nouveau rôle par Lambda, lister explicitement **toutes** les tables touchées par le code, pas seulement les tables "métier" évidentes du module — grep le code pour tout `INSERT INTO`/`UPDATE`/`SELECT` avant d'écrire la migration de GRANT, plutôt que de le déduire de mémoire.
- Ne pas se fier à des tests qui passent : un test unitaire avec curseur mocké ne détecte jamais un `GRANT` manquant — c'est une classe de bug invisible à toute la pyramide de tests sauf un vrai test d'intégration contre la base réelle, exerçant chaque route en écriture au moins une fois après déploiement.
- Après le déploiement d'un nouveau rôle/module, exercer manuellement (ou via script) **chaque route d'écriture** au moins une fois contre l'environnement réel avant de considérer le module "terminé" — pas seulement les routes de lecture, qui masquent ce bug.

---

## 14. Course entre déconnexion et redirection automatique côté SPA

**Symptôme** : le clic sur "Déconnexion" ne déconnecte pas réellement l'utilisateur — l'URL transite brièvement par `/callback?code=...&state=...` puis revient sur une route protégée, toujours authentifié. Comportement non déterministe : parfois l'utilisateur est reconnecté silencieusement, parfois un écran d'erreur générique apparaît à la place — jamais le même symptôme deux fois de suite en apparence, ce qui égare le diagnostic.

**Cause réelle** — trouvée uniquement via une trace de navigation en navigateur réel (Playwright headless), impossible à voir avec de simples logs serveur puisque tout se joue côté client : le handler de déconnexion faisait `setUser(null)` (état React) **avant** d'appeler la vraie navigation plein-page vers l'endpoint `/logout` de l'IdP. `setUser(null)` déclenche un re-render synchrone du garde de route protégée, qui — puisque la navigation plein-page n'a pas encore eu le temps de partir (elle prend un temps réel non nul : DNS/TLS/HTTP) — monte la page de login **avant** que le vrai logout n'ait eu lieu. Cette page de login lance alors sa propre redirection vers l'IdP, en concurrence directe avec la vraie déconnexion. Selon laquelle des deux navigations "gagne" la course, soit la session IdP n'est jamais réellement invalidée (SSO silencieux → reconnexion automatique), soit un état intermédiaire est pollué (voir §15).

**Correctif** : ne modifier **aucun état React qui pourrait déclencher un re-render/redirection** juste avant un `window.location.assign()` de déconnexion — la page va de toute façon être détruite dans l'instant qui suit, un `setState` juste avant est non seulement inutile mais activement dangereux. Faire uniquement : effacer le storage (tokens), puis naviguer.

**Règle générale** : dans tout flux d'auth SPA, se méfier de **toute** mise à jour d'état React placée juste avant une navigation plein-page (`window.location.assign`/`href`) — la navigation n'est jamais instantanée du point de vue du moteur JS, et le re-render qu'elle est censée rendre obsolète a le temps de s'exécuter et de produire des effets de bord (dont, ironiquement, une AUTRE tentative de navigation concurrente) avant que le navigateur ne quitte réellement la page. Un bug de ce type ne se voit **jamais** dans les logs serveur (tout se passe avant que la moindre requête réseau parte) — seule une trace de navigation en navigateur réel (Playwright/Puppeteer avec `page.on("framenavigated", ...)`) le révèle de façon fiable ; le reproduire avec de simples appels `curl`/API ne suffit pas puisque la race dépend du timing réel du moteur de rendu et du réseau.

---

## 15. Verrou anti-boucle jamais réinitialisé après un succès

**Symptôme** : un cycle utilisateur parfaitement légitime et rapide (connexion → déconnexion → reconnexion, le tout en moins de quelques secondes) déclenche un écran d'erreur générique ("la connexion échoue de façon répétée") au lieu de fonctionner normalement — alors qu'aucune vraie boucle d'échec n'a eu lieu.

**Cause réelle** : un mécanisme anti-boucle ajouté pour casser une *vraie* boucle de redirection invisible (voir §10) mémorise un horodatage à chaque tentative et refuse de re-rediriger si la dernière tentative remonte à moins de N secondes. Ce timestamp n'était mis à jour qu'au **début** de chaque tentative, jamais effacé après un **succès** — donc deux tentatives de connexion entièrement indépendantes et légitimes (séparées par une session active entre les deux) tombaient dans la même fenêtre de temps et la seconde était prise à tort pour la continuation d'une boucle d'échec.

**Correctif** : effacer explicitement le verrou dès qu'une authentification réussit (pas seulement le laisser expirer par timeout) — le verrou doit refléter "depuis quand la DERNIÈRE TENTATIVE EN ÉCHEC a eu lieu", jamais "depuis quand une tentative a eu lieu", succès inclus.

**Règle générale** : tout mécanisme de type "cooldown"/"anti-boucle" basé sur un simple horodatage + fenêtre de temps doit distinguer explicitement échec et succès — un timestamp qui n'est mis à jour qu'en début de tentative, sans jamais être nettoyé sur succès, finira toujours par confondre "ça boucle" et "l'utilisateur est juste rapide". Tester ce genre de mécanisme non seulement sur le scénario d'échec qu'il est censé attraper, mais aussi sur le cycle légitime le plus rapide plausible (ici : logout immédiatement suivi d'un nouveau login) — un test qui ne couvre que le cas d'échec laisse ce genre de faux positif invisible jusqu'à ce qu'un vrai utilisateur le déclenche.

---

## Méthode de diagnostic transversale (le vrai enseignement)

Le fil conducteur de toutes les entrées ci-dessus : **chaque bug a été résolu en obtenant une preuve empirique directe (log CloudWatch réel, `curl` avec le vrai en-tête/token, simulation du parcours exact du protocole), jamais en corrigeant sur hypothèse.** Deux pièges récurrents à éviter explicitement :

1. **Un correctif qui « devrait » marcher n'est pas un correctif vérifié.** Après chaque changement dans une chaîne d'auth/réseau multi-couches (CORS → IAM → parsing de claims → scopes OAuth), il y a eu plusieurs fois une couche suivante non encore testée qui faisait échouer la même symptomatologie apparente pour une raison totalement différente. Ne jamais annoncer un problème résolu sans avoir revérifié le symptôme original avec une preuve fraîche.
2. **Un raccourci de test peut contourner exactement le bug qu'on cherche à reproduire.** Utiliser `ADMIN_USER_PASSWORD_AUTH`/`USER_SRP_AUTH` pour obtenir rapidement un token de test a occulté deux bugs réels (claims/scopes) qui n'existent que dans le vrai flux OAuth Hosted UI. Quand un raccourci de test existe, se demander explicitement : « ce raccourci emprunte-t-il exactement le même chemin de code que l'utilisateur réel ? » — sinon, il faut aussi valider avec le chemin réel avant de clore le sujet.
3. **Certains bugs ne laissent aucune trace côté serveur — seul un vrai navigateur les révèle.** Les bugs §14/§15 (course de navigation, verrou anti-boucle) ne produisent ni erreur HTTP, ni log CloudWatch, ni entrée réseau anormale : tout se joue dans le timing du moteur de rendu et du routeur client, avant qu'une requête ne parte. `curl`/`requests` avec un cookie jar (très efficace pour les bugs §7-§13, qui vivent au niveau protocole HTTP) est structurellement aveugle à cette classe de bug. Un navigateur headless piloté (Playwright/Puppeteer, `page.on("framenavigated", ...)` pour tracer chaque navigation, `page.on("dialog", ...)` pour intercepter les popups natifs) est l'outil à sortir dès qu'un symptôme implique un **ordre d'événements** côté client (redirections, état React, écrans qui s'enchaînent) plutôt qu'une simple réponse HTTP incorrecte — et il faut le faire tourner plusieurs fois de suite avant de conclure qu'un correctif tient, car ce type de bug est par nature intermittent (dépendant du timing réseau réel).
