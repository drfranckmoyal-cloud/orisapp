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

## Serveur ouvert au Wi-Fi du cabinet — fait le 21/09/2026

Décision de Franck : `lancer-oris.command` démarre désormais le serveur sur le réseau
(`--host 0.0.0.0`). Vérifié : depuis le Mac, tout répond ; depuis le Wi-Fi, sans jeton,
refus `AUTHENTICATION_REQUIRED` ; le dépôt de la journée (extension Chrome) reste réservé
au Mac.

Adresse à saisir dans l'app (Paramètres › Connexion à Oris) : **`MacBook-Pro-3.local:8000`**
— le nom du Mac ne change pas, contrairement à son adresse IP (10.0.0.7 le 21/09).
Au premier lancement, macOS peut demander d'autoriser Python à accepter les connexions
entrantes : répondre « Autoriser ».

## Reste à faire, le jour de l'installation sur l'iPhone

1. Franck signe l'app dans Xcode avec son identifiant Apple (voir plus haut).
2. Claude crée le jeton « iPhone de Franck » (`scripts/issue_token.py`) et l'ouvre dans
   un fichier sur le Mac ; Franck le copie, le colle dans l'app (Paramètres › Connexion
   à Oris) — le presse-papiers passe du Mac à l'iPhone s'ils partagent le même compte
   Apple — puis le fichier est supprimé.
3. Données réelles : même règle qu'ailleurs, développement local seulement jusqu'à
   l'hébergement agréé HDS.

## Installée et connectée — 21/09/2026

Oris tourne sur « iPhone de Franck New » et joint le serveur du Mac par le Wi-Fi
(adresse `10.0.0.7:8000`, jeton « iPhone de Franck »).

Ce qui a bloqué, pour la prochaine fois :

- **iOS refusait le réseau local sans poser la question** (erreur « pas d'accès au
  réseau local »). Une simple requête ne déclenche pas toujours la question ; l'app
  lance donc au démarrage une courte recherche Bonjour (`ReseauLocal.swift`,
  `NSBonjourServices` = `_oris._tcp`), qui la fait apparaître à coup sûr.
- **Rien à recopier sur l'iPhone** : l'adresse et le jeton se posent depuis le Mac,
  câble branché, au lancement de l'app :

  ```
  xcrun devicectl device process launch --device <id> --terminate-existing \
    --environment-variables '{"ORIS_REGLER_SERVEUR":"10.0.0.7:8000","ORIS_REGLER_JETON":"oris_…"}' fr.oris.app
  ```

- En cas d'échec, l'écran Paramètres dit l'adresse essayée et la cause en clair.
- Si l'adresse du Mac change (autre Wi-Fi), relancer la commande avec la nouvelle.

## Adresse du Mac : son nom, pas son adresse chiffrée — 22/09/2026

Le Mac a changé de Wi-Fi (10.0.0.7 → 192.168.100.13) et l'iPhone, réglé sur l'ancienne
adresse chiffrée, ne le trouvait plus. L'iPhone désigne désormais le Mac par son nom sur
le réseau local, **`MacBook-Pro-3.local:8000`**, qui ne change pas d'un Wi-Fi à l'autre
(vérifié : l'iPhone joint le Mac par ce nom). Pour le reposer depuis le Mac :

```
xcrun devicectl device process launch --device <id> --terminate-existing \
  --environment-variables '{"ORIS_REGLER_SERVEUR":"MacBook-Pro-3.local:8000"}' fr.oris.app
```
