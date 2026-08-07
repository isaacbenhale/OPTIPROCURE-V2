# assets/ — source des visuels du projet (logo, icônes, images)

Dossier unique pour les fichiers source (SVG/PNG haute résolution) des
visuels partagés par l'ensemble du projet — back-office (`frontend-admin/`)
et portail public (`frontend-public/`, module 05, pas encore construit).

- `logos/` — logo OptiProcure (marque complète, marque-icône seule, variantes clair/sombre).
- `icons/` — favicon source et toute icône de marque hors du set d'icônes UI (voir `frontend-admin/src/components/Icons.tsx` pour les icônes d'interface, qui restent des composants SVG inline, pas des fichiers ici).
- `images/` — images génériques (illustrations, visuels marketing du portail public).

## Convention

Ce dossier n'est **pas** servi directement par une application — Vite
(`frontend-admin`) et Next.js (`frontend-public`) servent chacun leur propre
dossier `public/` local. `assets/` est la source de vérité : quand un
visuel change ici, copier (ou exporter, pour les formats dérivés) la
version nécessaire dans le `public/` de chaque app qui l'utilise.

Actuellement aucun fichier logo réel n'existe : `frontend-admin` utilise un
placeholder texte ("OP" dans un carré coloré, voir
`frontend-admin/src/components/Logo.tsx`) en attendant un vrai logo ici.
