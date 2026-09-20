# Oris — dossier à transmettre pour avis

*Document autonome. À coller tel quel à un autre assistant, un designer ou un
confrère. Tout ce qu'il faut savoir est dedans ; aucun accès au code n'est
nécessaire.*

---

## Ce qu'est Oris

Oris est un **assistant de documentation clinique pour chirurgiens-dentistes**.

Le praticien lance l'écoute au début de la consultation, pose son téléphone ou laisse
l'ordinateur écouter, et soigne. À la fin, Oris a produit : le **compte rendu de
consultation**, le **plan de traitement**, le **compte rendu opératoire** quand un acte
a été réalisé, et le **courrier au confrère** si besoin. Le praticien relit, corrige à
la voix ou au clavier, valide. Le dossier est prêt avant que le patient ait quitté le
fauteuil.

Le porteur du projet est **chirurgien-dentiste**, pas développeur. Le produit vise
d'abord son propre cabinet, puis d'autres cabinets français.

État : le moteur fonctionne de bout en bout sur des consultations fictives
(transcription, extraction clinique, rédaction, corrections, export PDF). L'interface
web existe. Rien n'est encore utilisé sur de vrais patients — l'hébergement agréé
données de santé n'est pas en place.

---

## Ce qui distingue Oris d'une dictée ou d'un ChatGPT médical

C'est le cœur du sujet, et c'est ce qui a été construit en premier.

1. **Oris n'invente jamais un fait clinique.** Chaque phrase du compte rendu doit
   pouvoir être rattachée à une parole réellement prononcée pendant la consultation.
   Une phrase sans appui est refusée par un validateur automatique, pas par le modèle
   qui l'a écrite.
2. **La négation, l'incertitude et la temporalité sont préservées.** « Pas de douleur
   nocturne » ne devient jamais « douleur nocturne ». « Peut-être une fissure » ne
   devient jamais « fissure ».
3. **Ce que dit le patient reste ce que dit le patient.** Un symptôme rapporté ne
   devient jamais un constat du praticien.
4. **Un acte discuté n'est pas un acte accepté, ni un acte réalisé.** Six statuts
   distincts sont suivis : discuté, proposé, accepté, refusé, reporté, réalisé.
5. **Les numéros de dents sont traités comme des données à haut risque.**
6. **Rien n'est validé automatiquement.** Un document reste un brouillon jusqu'à ce
   que le praticien le valide ; un PDF non validé porte la mention « brouillon ».
7. **L'audio est éphémère** : supprimé dès que la transcription a abouti.
8. **Une correction modifie d'abord le dossier structuré**, puis les documents sont
   réécrits — jamais l'inverse. Corriger « ce n'était pas la 26 mais la 27 » corrige le
   compte rendu *et* le plan de traitement.

---

## L'identité visuelle actuelle

- **Nom** : Oris.
- **Logo** : une **ligne de son dont les montées et descentes composent le profil
  d'une molaire** — deux cuspides séparées d'un sillon en haut, deux racines en bas.
  Vu de loin : un niveau sonore. Vu de près : une dent. Jamais de dent dessinée
  littéralement. Pendant l'écoute, les barres du logo deviennent le niveau réel du
  micro.
- **Palette** : neutres chauds (crème, sable) et **vert profond** `#14533B` —
  délibérément pas le bleu technologique habituel. Argile `#A8540A` pour ce qui
  demande vérification, rouge brique pour les alertes.
- **Registre visé** : cabinet médical établi, calme, premium, lisible debout à un
  mètre. Surtout pas « chatbot » ni « start-up tech ».

---

## Ce sur quoi je veux votre avis

*(Gardez ce qui vous intéresse, supprimez le reste.)*

### A. Le slogan

Voici les pistes. Dites-moi laquelle porte le mieux le produit, et proposez les
vôtres.

**Sur la non-invention** — l'invariant technique transformé en promesse :
« Rien que ce qui a été dit. » · « Ce qui est écrit a été dit. » · « Aucune phrase sans
preuve. » · « Chaque phrase remonte à une parole. »

**Sur le partage des rôles** :
« Vous soignez. Oris écrit. » · « À vous le soin, à Oris le dossier. » · « Gardez les
yeux sur le patient. »

**Sur le temps rendu** :
« Vos soirées vous appartiennent. » · « La consultation finie, le dossier aussi. » ·
« Plus de comptes rendus le soir. »

**Sur le mécanisme** :
« La parole devient dossier. » · « Écouter. Comprendre. Documenter. »

Questions : lequel tient en couverture de plaquette *et* sous le logo dans
l'application ? Lequel un confrère répéterait-il à un autre confrère ? Y a-t-il une
promesse qu'on ne devrait pas faire ?

### B. Le nom et la marque

« Oris » (du latin *os, oris* : la bouche, et aussi la parole). Est-ce que ça tient en
France auprès de chirurgiens-dentistes ? Risque de confusion ? Faut-il travailler le
nom autrement — typographie à empattements pour l'autorité, sans-serif pour la
modernité ?

### C. Le parti pris visuel

Vert profond et neutres chauds plutôt que le bleu médical. Est-ce un bon écart, ou
une faute de registre dans un univers où le bleu signale l'hygiène et le sérieux ?

### D. Ce qui manque

À la lecture de ce document, qu'est-ce qui vous paraît absent, faible, ou
dangereux ?

---

## Ce qu'il ne faut pas me proposer

- De faire écrire à Oris des choses qui n'ont pas été dites, sous prétexte de
  « rendre le compte rendu plus complet ». C'est l'interdit fondateur.
- De supprimer la validation par le praticien.
- Un registre visuel de chatbot, ou un pictogramme de dent souriante.
