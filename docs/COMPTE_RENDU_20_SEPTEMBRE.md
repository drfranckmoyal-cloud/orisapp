# Compte rendu — session du 20 septembre 2026

*Travail mené en autonomie après votre départ. Palette bleue retenue, praticien
« Dr Franck Moyal », site en priorité, patient de test générique.*

---

## 1. Ce qui a changé, en une phrase

Oris est passé d'un moteur clinique habillé d'un banc d'essai à une **application** :
tableau de bord, fiche patient, parcours de consultation complet avec écran d'attente,
écran de révision conforme au cahier, documents, paramètres.

---

## 2. Les fondations, d'abord

Ce qui rendait chaque écran bancal, et qui est corrigé :

- **la police Inter n'était pas chargée** — elle était déclarée dans la feuille de style
  mais jamais téléchargée. Oris s'affichait en police système depuis le premier jour ;
- **il n'existait aucun système de composants** : chaque écran était dessiné à la main.
  Il y a désormais une bibliothèque (bouton, carte, en-tête, pastille, onglets, état
  vide, squelette de chargement, étapes, barre d'outils, zone de texte) et **aucun écran
  ne dessine plus** ;
- **les couleurs sont sémantiques** (`--fond`, `--surface`, `--encre`, `--accent`,
  `--alerte`…). Aucun écran ne connaît un code couleur : la palette se change en un seul
  endroit.

---

## 3. Écran par écran

### Accueil — un vrai tableau de bord
Date du jour, « Bonjour Docteur Moyal », **une seule action**, puis quatre cartes :
à relire, aujourd'hui, terminées, à reprendre. Chacune a son état vide, qui dit quoi
faire au lieu de laisser un blanc.

### Patients — la continuité qui manquait
Recherche insensible aux accents, création complète (prénom, nom, date de naissance,
identifiant du cabinet), et surtout **la fiche patient** : historique des consultations,
documents produits, plan de traitement en cours. Une consultation n'est plus un fichier
isolé — c'était le reproche principal.

### Démarrer une consultation
Patient suivi choisi dans la liste, ou créé à la volée. Un écran avant l'écoute, comme
le cahier l'exige.

### Écoute
Inchangée dans son principe (elle était correcte) : cercle, minuteur, niveau, état micro
et réseau, pause, terminer.

### Attente — l'écran qui n'existait pas
Après « Terminer », la page se figeait puis basculait. Il y a maintenant un écran
« Oris prépare le dossier… » avec **trois étapes réelles** : finalisation de la
transcription, structuration clinique, préparation des documents. Chaque étape n'est
cochée que si elle est **vraie en base** — aucune barre de progression inventée. Le
serveur publie son avancement au fur et à mesure pour que ce soit possible.

### Révision — le cœur
- rail à onglets conforme au cahier : **À vérifier / Données cliniques / Historique** ;
- la source d'une phrase se glisse **par-dessus** le rail, on ne perd pas le contexte ;
- les faits s'affichent **en français** : plus de `cold_sensitivity` sous les yeux d'un
  praticien ;
- barre d'outils du document : **éditer le texte**, **raccourcir**, copier pour le
  dossier, exporter en PDF.

### Édition manuelle (§48)
Vous pouvez réécrire le texte. Oris enregistre une nouvelle version signée « écrit par le
praticien », **ne prétend plus à aucune provenance** sur ce texte, et dit clairement que
le dossier clinique n'a pas changé. Si une donnée clinique est fausse, il vous renvoie
vers la correction, qui elle modifie le dossier.

### Plan de traitement (§34)
Ajouter un traitement, le retirer, le monter, le descendre. Quand vous décidez l'ordre,
il devient une **séquence explicite** — conformément à la règle « pas de numérotation
sans ordre énoncé ». Un traitement que vous ajoutez à la main est appuyé par votre
décision, enregistrée comme un fait manuel : l'invariant « toute phrase s'appuie sur un
fait » n'est pas contourné.

### Documents et Paramètres
Deux écrans qui n'existaient pas. Documents : tout ce qui a été produit, filtrable par
type, avec recherche par patient. Paramètres : praticien, cabinet, moteurs réellement
actifs, réglages d'écoute, et **état de sécurité — y compris ce qui manque**.

---

## 4. Ce qui reste à faire, sans enrobage

| Manque | Pourquoi ce n'est pas fait |
|---|---|
| Transcription **en direct** pendant la consultation (§14.1) | l'adaptateur temps réel existe, il n'est branché à aucun écran |
| Bouton « marquer un point » pendant l'écoute (§11) | facultatif dans le cahier, écarté de cette passe |
| Alerte avant la durée maximale de session (§12) | à faire |
| Catégories « fiable / à vérifier / conflit » sur chaque fait (§31) | les alertes existent, cette graduation non |
| Pièces jointes (§55) | explicitement reportable après le MVP |
| Tables `PromptVersion`, `ModelVersion`, `DatasetVersion`, `EvaluationRun`, `PractitionerLearningProfile`, `templates`, `attachments` (§202, §205) | exigées « dès la fondation », toujours absentes |
| iPhone | vous avez dit « bien après » |
| MFA, hébergement agréé | décisions et contrats, pas du code |

---

## 5. Pour essayer

1. Double-cliquez **`lancer-oris.command`**.
2. Le navigateur s'ouvre sur l'accueil.
3. **Démarrer une consultation** → choisissez Marie Dupont → **Démarrer l'écoute** →
   cochez l'information du patient → **Commencer l'écoute**.
4. Parlez deux minutes comme en consultation (le dialogue d'essai est dans
   `docs/UTILISER_ORIS.md`, avec les pièges à glisser dedans).
5. **Terminer** → l'écran d'attente → le compte rendu.
6. Essayez : cliquer une phrase pour voir sa source, dicter « remplace 26 par 27 »,
   ajouter un traitement au plan, éditer le texte, exporter en PDF.

Pour arrêter : **`arreter-oris.command`**.

---

## 6. État des vérifications

- 278 tests serveur, 47 tests web, types et style stricts : tout au vert ;
- parcours complet rejoué dans le navigateur : accueil → patient → consultation →
  révision → correction → plan → documents ;
- la porte d'entrée en bêta refuse toujours l'usage sur un patient réel, et c'est
  volontaire.

---

## 7. Les décisions que j'ai prises seul

1. **Raccourcir** est traité comme une préférence de rédaction durable (réversible dans
   « Oris apprend »), pas comme une retouche ponctuelle : c'est ce que dit le cahier.
2. **Un traitement ajouté à la main crée un fait manuel** qui le justifie, plutôt que
   d'affaiblir la règle « toute phrase s'appuie sur un fait ».
3. **L'écran d'attente lit la base** plutôt que d'animer une barre : trois étapes vraies
   valent mieux qu'une progression rassurante et fausse.
4. **Le texte réécrit à la main perd sa provenance**, et Oris le dit, au lieu de laisser
   croire que chaque phrase reste traçable.
