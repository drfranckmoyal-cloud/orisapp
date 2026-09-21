# Installer Oris sur l'iPhone

*Écrit le 21 septembre 2026, après le premier essai complet de l'app sur simulateur.*

## Ce qui est prêt

- L'app compile et tourne (iPhone 17 Pro, iOS 26.5, simulateur). 41 tests passent.
- Parcours vérifié de bout en bout : choisir un patient (onglet « Patients » ou
  « Nouvelle consultation »), choisir **Consultation** ou **Acte**, voir le déroulé du
  compte rendu, écouter, terminer ; la consultation apparaît dans « Consultations » avec
  ses documents (compte rendu, plan, courrier) ou, sans parole, avec la raison.
- Défaut corrigé le 21/09 : sur un vrai appareil, **chaque segment audio était perdu**
  (le chemin « Application Support » contient un espace, relu encodé). Un test le garde.
- Paramètres : adresse du serveur et **jeton d'accès** (rangé dans le trousseau de
  l'iPhone). Parcours réseau vérifié : sans jeton le serveur refuse, avec jeton il répond.

## Ce que Franck doit faire (Claude ne peut pas le faire à sa place)

1. **Signer l'app avec son identifiant Apple.** Xcode › Réglages › Comptes › « + » ›
   identifiant Apple. Puis, dans le projet `apps/ios/Oris.xcodeproj`, cible *Oris* ›
   *Signing & Capabilities* › *Team* : choisir son nom. Un compte gratuit suffit pour
   essayer ; l'app expire alors au bout de 7 jours (il suffit de la réinstaller). Un
   compte développeur payant (99 €/an) lève cette limite et permet TestFlight.
2. **Brancher l'iPhone au Mac**, accepter « Faire confiance », activer le mode
   développeur (Réglages › Confidentialité et sécurité › Mode développeur).
3. Sur l'iPhone, la première fois : Réglages › Général › VPN et gestion de l'appareil ›
   faire confiance à son profil de développeur.

## Ce qui reste à décider

- **Ouvrir le serveur Oris au Wi-Fi du cabinet.** Aujourd'hui il n'écoute que le Mac
  lui-même (`127.0.0.1`) : l'iPhone ne peut pas le joindre. L'ouvrir (`--host 0.0.0.0`
  dans `lancer-oris.command`) est désormais sûr pour les données : hors du Mac, **tout
  appel sans jeton est refusé** (règle ajoutée le 21/09, testée). Mais c'est un choix :
  le serveur devient visible des autres appareils du réseau, même s'ils ne peuvent rien
  lire.
- **Créer le jeton de l'iPhone**, une fois le point précédent tranché :
  `services/api/.venv.nosync/bin/python scripts/issue_token.py --email praticien.demo@oris.local --label "iPhone de Franck"`
  puis le coller dans l'app (Paramètres › Connexion à Oris), avec l'adresse du Mac sur
  le Wi-Fi (Réglages Système › Wi-Fi › Détails).
- **Données réelles** : une consultation enregistrée sur l'iPhone part sur le Mac, comme
  depuis le site. Même règle qu'ailleurs : développement local seulement jusqu'à
  l'hébergement agréé HDS.
