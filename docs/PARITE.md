# Parité site ↔ app iPhone

*Règle figée le 21/09/2026 (D028) : ce qui est corrigé ou ajouté d'un côté l'est de
l'autre, dans le même lot. Ce fichier dit où en est l'égalité.*

## À rattraper dans l'app iPhone (existe sur le site)

- Transcription brute d'une consultation (l'iPhone montre les paroles d'une phrase,
  pas encore la transcription entière).
- Correction du dossier clinique (à la voix et au clavier : « remplace 26 par 27 »).
- Plan de traitement visuel (schéma dentaire, étapes colorées, chronologie).
- Compte rendu de soins à la demande quand un acte a été dit ; suppression d'un
  courrier d'adressage ou d'un compte rendu de soins demandé par erreur.
- Pièces jointes non photo du dossier patient (PDF, radios) : liste et ouverture.
- Votre journée (Doctolib) ; ajouter un mot au dictionnaire (l'iPhone le lit seulement).
- Paramètres : spécialités des correspondants, praticiens du cabinet, export des
  apprentissages (le reste est sur les deux).

## À rattraper sur le site (existe dans l'app iPhone)

- Boutons Appeler / Écrire sur la fiche d'un correspondant (lien `tel:` / `mailto:`).
- Supprimer une consultation depuis la liste du **dossier patient** (sur le site : depuis
  la liste Consultations et depuis la consultation).

## Acquis des deux côtés

- **« D'où vient cette phrase ? »** (26/09/2026) : sur le site, la phrase s'ouvre dans le
  rail de révision ; sur l'iPhone, dans une feuille. Les deux appellent la même route
  `GET /documents/{id}/preuve`, qui fait la jointure phrase → faits → paroles côté
  serveur. Nuance : le site lit le dossier clinique **courant**, l'iPhone celui de la
  version qui a servi à écrire le document — à aligner sur le site quand on y touchera.

## Écarts voulus (imposés par l'appareil)

- Envois : page « Envois » sur le site (envoyer depuis la liste) ; sur l'iPhone, le
  filtre « À envoyer » des Consultations, l'envoi se faisant depuis la consultation.

- Reconnecter Doctolib / SmileCloud : bouton dans la colonne de gauche du site (il ouvre
  Chrome sur le Mac) ; l'iPhone montre l'état seulement. Autoriser un nouvel appareil :
  depuis le Mac seulement.


- iPhone : appareil photo, écoute écran verrouillé et pendant un appel, son gardé chiffré
  hors connexion ; **écran d'ouverture** (logo et slogan, 1,5 s) et **Face ID** à
  l'ouverture et au retour après deux minutes — un navigateur a sa propre session.
- Accueil : le même grand bouton rond qui respire, au centre, sur les deux. Le site
  l'entoure de quatre tuiles (À relire, Votre journée, Cette semaine, Saisie évitée) ;
  l'iPhone garde un écran dépouillé avec « À relire » en tiroir — un téléphone n'a pas
  la place d'un tableau de bord.
- Supprimer une ligne : glisser vers la gauche sur l'iPhone, corbeille en bout de ligne
  sur le site.
- Site : téléversement par glisser-déposer, copie du texte pour le logiciel du cabinet.
