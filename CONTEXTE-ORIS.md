# Oris — contexte du projet

*Document de reprise. À coller au début d'une nouvelle conversation pour qu'elle
sache de quoi il s'agit. Écrit le 21 septembre 2026.*

---

## 1. Ce qu'est Oris

**Oris est l'assistant de documentation clinique conçu pour les chirurgiens-dentistes.**
Le praticien lance l'écoute au début de la consultation et soigne. À la fin, Oris a
produit le compte rendu, le plan de traitement, le compte rendu opératoire s'il y a eu
un acte. Le praticien relit, corrige à la voix ou au clavier, valide.

**Slogan arrêté : « Vous soignez. Oris documente. »**

Le porteur du projet est **Franck Moyal, chirurgien-dentiste, pas développeur**. Il
pilote et tranche les choix métier et esthétiques ; le vocabulaire technique le perd.
Lui parler en français simple, expliquer ce que fait un terme technique quand on
l'emploie, dire franchement ce qui bloque, et **lancer les commandes soi-même** plutôt
que de les lui faire taper.

Dépôt : `drfranckmoyal-cloud/orisapp` (privé). Dossier local :
`~/Desktop/Claude-Projects/ORIS`. Tout est commité et poussé au fil de l'eau, messages
de commit en français.

---

## 2. Les dix interdits — le cœur du produit

Ce sont eux qui distinguent Oris d'une dictée ou d'un ChatGPT médical. Ils sont
tenus par du code et par des tests, pas par des intentions. **Ne jamais proposer de
les assouplir.**

1. **Oris n'invente jamais un fait clinique.** Chaque phrase d'un document doit
   pouvoir être rattachée à une parole réellement prononcée. Un validateur refuse les
   phrases sans appui.
2. **La négation est préservée.** « Pas de douleur nocturne » ne devient jamais
   « douleur nocturne ».
3. **L'incertitude est préservée.** « Peut-être une fissure » ne devient jamais
   « fissure ».
4. **La temporalité est préservée.** Un acte prévu n'est pas un acte réalisé.
5. **Patient-rapporté ≠ constaté par le praticien.** Un symptôme décrit par le patient
   ne devient jamais un constat clinique.
6. **Six statuts distincts** pour un acte : discuté, proposé, accepté, refusé,
   reporté, réalisé.
7. **Les numéros de dents sont à haut risque** et traités comme tels.
8. **Une perte d'audio génère une alerte explicite**, jamais un silence.
9. **Rien n'est validé automatiquement.** Un document reste brouillon jusqu'à
   validation ; un PDF non validé porte la mention « brouillon ».
10. **Une correction modifie d'abord le dossier structuré**, puis les documents sont
    réécrits. Corriger « c'était la 27, pas la 26 » corrige le compte rendu *et* le
    plan de traitement.

Deux règles voisines :
- **L'audio est éphémère** : supprimé dès que la transcription a abouti.
- **Ce qu'Oris apprend change sa façon d'écrire, jamais le contenu clinique.**
- **Aucune donnée de patient réel** tant que l'hébergement agréé santé n'est pas en
  place. Tout ce qui existe aujourd'hui est fictif.

---

## 3. Architecture

| Morceau | Technique | Où |
|---|---|---|
| API | Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic | `services/api` |
| Site | Next.js (App Router), TypeScript, CSS modules | `apps/web` |
| iPhone | Swift / SwiftUI — **en retard sur le reste** | `apps/ios` |
| Contrats | JSON Schema → types Python, TypeScript, Swift | `schemas/`, `scripts/generate_contracts.py` |
| Jetons visuels | `design/tokens.json` → CSS + Swift | `scripts/generate_tokens.py` |

**Objet clinique = source de vérité.** Les documents en sont des projections. Une
correction modifie l'objet, puis régénère les projections.

Fournisseurs : **Deepgram Nova-3** pour la transcription, **Claude (Anthropic)** pour
l'extraction clinique. Isolés derrière des interfaces ; remplaçables par configuration.
Les clés sont dans `services/api/.env`, **jamais dans le dépôt, jamais en conversation**.

Lancement : `lancer-oris.command` (site sur `:3000`, API sur `:8000`).

**Avant de commiter, tout doit passer** : `ruff check`, `ruff format --check`, `mypy`,
`pytest` (307 tests), `npm run lint`, `tsc --noEmit`, `npm test` (63 tests),
`npm run build`, et les contrats à jour.

---

## 4. Les écrans, onglet par onglet

La barre de gauche est un bloc vert plein. Le **logo est une plaque crème posée
dessus, cliquable, qui ramène à l'accueil**. Le praticien se choisit en bas, dans un
menu déroulant.

### Accueil (`/`)
Tableau de bord. Un **grand bouton vert « Commencer une consultation »** dont le logo
s'anime au survol — c'est le cœur de l'application. Recherche patient. La semaine en
barres. La « saisie évitée » en gros chiffre, **avec sa méthode de calcul affichée**.
Ce qui attend d'être relu. Ce qu'Oris a appris.

### Votre journée (`/journee`) — **chantier à venir**
Reprendra les rendez-vous du jour depuis **Doctolib** : créer les dossiers sans
ressaisie, démarrer l'écoute d'un geste. L'écran dit ce qu'il fera et ce qu'il faudra
régler avant (accès éditeur, cadre juridique, doublons).

### Patients (`/patients`)
Liste avec recherche insensible aux accents, création (prénom, nom, date de naissance,
identifiant externe, courriel). **Le nom de famille s'affiche en capitales** — usage
médical français ; la casse saisie reste intacte en base.

### Fiche patient (`/patients/[id]`)
- Flèche de sortie « ← Tous les patients ».
- Titre : **nom en graisse 800, âge entre parenthèses**.
- **Cadre d'informations : une information par ligne**, intitulé à gauche, valeur à
  droite. Nom, courriel, date de naissance, correspondants, voyant **SmileCloud**
  (vert connecté / orange non connecté), et la **note administrative** — qui se dicte
  au micro, le son n'étant jamais conservé.
- **Onglet Historique** : une ligne par consultation, cliquable, avec la **vignette du
  praticien** (initiales, nom complet au survol) et un accès minuscule à la
  **transcription brute**.
- **Onglet Pièces jointes** : import par **glisser-déposer** ou bouton. JPEG, PNG,
  HEIC/HEIF, WEBP, TIFF, DICOM, STL, PLY, OBJ, PDF — 80 Mo par fichier. Un clic ouvre
  un **aperçu** : images et PDF affichés, **empreintes STL tournées en 3D** (lecteur et
  rendu WebGL écrits à la main, sans bibliothèque). **Oris ne lit pas ces pièces** :
  aucun fait clinique n'en sort.

### Correspondants (`/correspondants`) — **chantier à venir**
Carnet des confrères, rattachement d'un patient à plusieurs correspondants, courrier
pré-adressé.

### Consultations (`/consultations`)
Liste groupée par jour, filtres (à relire, terminées, à reprendre), recherche patient.

### Nouvelle consultation (`/consultations/nouvelle`)
Choisir le patient ou le créer, puis **Commencer**. Permet aussi de rejouer une
consultation fictive du corpus, sans micro.

### Écoute en cours (`/consultations/[id]/ecoute`)
Le symbole d'Oris dans un disque qui respire, **ses barres au niveau réel du micro**.
Chronomètre. État micro et réseau. Pause, **Marquer un point**, Terminer. Panneau
« Ce qu'Oris entend » replié — la transcription en direct, derrière un drapeau.

### Révision (`/consultations/[id]`) — **l'écran décisif**
- À gauche : le document, par onglets selon ce qui a été produit. Éditer, Raccourcir,
  Copier, Exporter en PDF, Valider.
- À droite : le rail — **À vérifier** (alertes et phrases sans appui), **Données
  cliniques** (chaque fait avec sa graduation *fiable* / *à vérifier* et la raison au
  survol), **Points marqués**, **Historique des versions**. La source d'une phrase se
  glisse par-dessus le rail.
- **Corriger** : dicter ou écrire « remplace 26 par 27 » ; Oris montre ce qu'il a
  compris **avant** d'appliquer.
- **Pièces jointes** sous la main ; une pièce déposée là est rattachée à cette
  consultation.

### Transcription brute (`/consultations/[id]/transcription`)
Le texte tel qu'il est sorti de la machine, avec l'avertissement que **le compte rendu
n'en vient pas**.

### Documents (`/documents`)
Tous les documents produits, filtre par type, recherche par patient.

### Oris apprend (`/apprentissage`)
Les sept sections du cadrage : ce qu'Oris a remarqué (suggestions à adopter), ce qu'il
a appris (en clair), préférences de rédaction, dictionnaire, matériaux reconnus,
**corrections fréquentes** (comptées, traduites en français), **réinitialiser** (un
champ ou tout), **exporter**.

### Paramètres (`/parametres`)
Praticiens du cabinet et création d'un profil (**grisée, en attente**). Connecteurs
SmileCloud et Doctolib (**en attente**). Identité du cabinet imprimée en tête des
documents. Moteurs — **ce qui a réellement tourné**, modèle et version de consigne.
Écoute. Sécurité, y compris ce qui manque.

---

## 5. Identité visuelle

- **Logo** : une **ligne de son dont les montées et descentes composent le profil d'une
  molaire** — deux cuspides séparées d'un sillon en haut, deux racines en bas. De loin
  un niveau sonore, de près une dent. Jamais de dent dessinée littéralement. Pendant
  l'écoute, les barres deviennent le niveau du micro.
- **Polices** : **Manrope** pour l'interface, **Fraunces** (600) pour le nom « Oris »,
  vectorisé — plus aucun fichier de marque ne dépend d'une police installée.
- **Palette** : neutres chauds et **vert profond `#14533B`**, délibérément pas le bleu
  technologique. Argile `#A8540A` pour « à vérifier », rouge brique pour les alertes.
- **Relief** : toute surface posée porte **trois couches d'ombre plus un filet de
  lumière**. Une ombre plate inventée sur place est un écart au système.
- Fichiers : `design/marque/` (SVG + 50 PNG + planche), `docs/DESIGN_SYSTEM.md`.

---

## 6. Ce qui existe, ce qui manque

**Fait** : la chaîne complète sur consultations fictives (écoute, transcription,
extraction, rédaction, corrections dictées, export PDF), les treize écrans, les tables
d'apprentissage exigées dès la fondation, la traçabilité de ce qui a tourné, la
sécurité par jeton, le journal d'audit sans contenu clinique.

**Manque** :
- l'**hébergement agréé santé** — bloque tout usage sur patient réel ;
- l'**authentification à deux facteurs** ;
- les générateurs de **courrier confrère** et de **résumé patient** (les modèles
  d'impression existent, rien ne les produit) ;
- les connecteurs **Doctolib** et **SmileCloud** ;
- l'**écran Correspondants** ;
- l'**application iPhone**, en retard sur le site ;
- la transcription en direct **de la commande vocale** pendant qu'on la dicte.

Documents de référence dans le dépôt : `ORIS_MASTER_SPEC_V1_2.md` (le cadrage),
`docs/ETAT_REEL.md` (l'écart entre le cadrage et le produit, section par section),
`docs/POSITIONNEMENT.md`, `docs/DESIGN_SYSTEM.md`, `docs/CHANGELOG.md`,
`docs/KNOWN_LIMITATIONS.md`.
