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
- **Typographie** : Manrope pour l'interface, Fraunces (à empattements) pour le nom.

## Le texte de présentation retenu

**Oris est l'assistant de documentation clinique conçu pour les chirurgiens-dentistes.**
Il écoute la consultation et prépare automatiquement vos comptes rendus, plans de
traitement et courriers, pendant que vous restez concentré sur votre patient.

Oris s'appuie sur des modèles d'intelligence artificielle adaptatifs de dernière
génération pour apprendre progressivement votre façon de travailler, votre vocabulaire
et vos habitudes de rédaction. L'objectif : une expérience réellement personnalisée,
des documents toujours plus proches de votre pratique et des corrections réduites au
minimum.

Utilisé à l'échelle de votre structure, Oris permet à toute l'équipe de gagner du
temps, d'harmoniser la documentation clinique et de réduire la charge administrative
au quotidien.

À la fin de la consultation, votre documentation est déjà prête, structurée et adaptée
à votre pratique.

*(Précision technique, pour que personne ne sur-promette : « adaptatif » veut dire que
le dictionnaire, les mots préférés et le style du praticien sont transmis à chaque
traitement, et que ce qu'il corrige reste dans son propre profil.)*

---

## Ce sur quoi je veux votre avis

*(Gardez ce qui vous intéresse, supprimez le reste.)*

### A. Le slogan

Retenu : **« Vous soignez. Oris documente. »**

Il dit la répartition des rôles et met le praticien en premier. L'autre finaliste,
« Votre temps reste au soin », a été écarté parce qu'il ne dit pas ce que fait Oris.

Questions : est-ce qu'il tient en couverture de plaquette **et** dans l'application ?
Est-ce qu'un confrère le répète à un autre confrère ? Y a-t-il une promesse qu'on ne
devrait pas faire ?

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
