# Oris en ligne

*Installé le 8 octobre 2026 sur un serveur dédié, à la demande de Franck : se servir de
l'app iPhone sans que le Mac soit allumé.*

## L'adresse

**https://51-159-130-158.nip.io** — le site, fermé par mot de passe.

Identifiant et mot de passe : fichier `acces-en-ligne.txt` dans
`~/Library/Application Support/Oris/` sur le Mac (hors iCloud, lisible de vous seul).
Le même fichier porte l'adresse et le jeton de l'app iPhone.

## La machine

| | |
|---|---|
| Hébergeur | Scaleway, projet **Oris** (séparé du projet DFM) |
| Type | PLAY2-NANO — 2 processeurs, 3,8 Go de mémoire, 36 Go de disque |
| Emplacement | Paris 2 (France) |
| Système | Ubuntu 24.04 LTS |
| Adresse | 51.159.130.158 |
| Coût | ≈ 0,038 €/h, soit ≈ 28 €/mois |

Accès : `ssh root@51.159.130.158` depuis le Mac (clé SSH « Mac de Franck »).

## Ce qui tourne

| Service | Rôle |
|---|---|
| `postgresql` | la base de données (`oris`) |
| `oris-api` | le serveur clinique, sur 127.0.0.1:8000 |
| `oris-web` | le site, sur 127.0.0.1:3000 |
| `nginx` | la façade : https, mot de passe, aiguillage |

Le code vit dans `/home/oris/app`, les réglages dans
`/home/oris/app/services/api/.env` (clés Deepgram et Anthropic ; **jamais dans le dépôt**),
les pièces jointes et journées dans `/home/oris/donnees/`.

## Les trois entrées, et pourquoi

Le serveur tourne en **mode production** : contrairement au Mac, il n'accorde aucune
confiance à la machine locale, donc **tout appel exige un jeton**. D'où trois portes :

| Chemin | Qui passe | Comment il prouve qui il est |
|---|---|---|
| `/` | le navigateur | mot de passe personnel (un compte par praticien) |
| `/api/` | le navigateur (appels du site) | même mot de passe ; **nginx ajoute le jeton de ce praticien-là**, choisi par une carte `map $remote_user`, que le navigateur ne voit jamais |
| `/mobile/` | l'app iPhone | **son propre jeton**, vérifié par le serveur |

### Les praticiens du cabinet

| Compte du site | Praticien | Accès remis dans |
|---|---|---|
| `franck` | Franck Moyal | `~/Library/Application Support/Oris/acces-en-ligne.txt` |
| `charlotte` | Dr Charlotte Lee | `~/Library/Application Support/Oris/acces-charlotte.txt` |

Chacun a **son** mot de passe de site et **son** jeton d'app : une action faite par l'un
porte son nom dans le journal d'audit, jamais celui de l'autre. Ajouter un praticien :
créer l'utilisateur en base, lui délivrer ses deux jetons (`scripts/issue_token.py`),
l'ajouter au fichier `.oris-htpasswd` et à la carte `map` de nginx.

C'est un montage d'essai, pas une authentification de produit : il n'y a qu'un seul
compte et un mot de passe partagé. La vraie connexion (compte, mot de passe, second
facteur, e-CPS) reste l'étape 1 de `docs/FEUILLE_DE_ROUTE_COMMERCIALISATION.md`.

## Mettre à jour

Depuis le Mac, dans le dossier du projet :

```
./deployer-en-ligne.command
```

Il envoie le code, refait l'environnement Python, applique les migrations, refabrique le
site et relance les deux services. Comptez deux à trois minutes. Les réglages (`.env`) et
les données du serveur ne sont jamais écrasés.

## Les sauvegardes

Chaque nuit à 2 h 30, le serveur sauvegarde la base et les pièces jointes dans
`/var/backups/oris`, et garde 30 jours. C'est un minuteur systemd
(`oris-sauvegarde.timer`) ; une sauvegarde anormalement petite est signalée au journal
(`journalctl -t oris-sauvegarde`).

**Une sauvegarde qui ne vit que sur la machine qu'elle protège ne protège de rien** :
`rapatrier-sauvegarde.command`, double-cliqué depuis le Mac, déclenche une sauvegarde
fraîche et la descend dans `~/Library/Application Support/Oris/sauvegardes` (les douze
dernières sont gardées). À faire avant toute opération risquée.

**Restauration essayée le 08/10/2026** sur une base jetable : 37 tables retrouvées. Une
sauvegarde non essayée ne compte pas.

## Ce qui n'est pas en place

- **Pas de contrat HDS** avec Scaleway, alors que le serveur porte désormais de vraies
  consultations : décision explicite de Franck du 08/10/2026 (D029), à régulariser.
- **Pas de surveillance** : si un service tombe, personne n'est prévenu (systemd le
  relance tout seul, mais sans le dire).
- Le certificat https se renouvelle seul (certbot), échéance visible avec
  `certbot certificates`.

## Ce qu'il y a dedans

Les données du Mac y ont été transportées le 08/10/2026 : 49 patients, 4 consultations,
6 documents, 401 passages de transcription, et les pièces jointes (12 Mo de photos). Le
Mac garde sa copie — les deux bases vivent désormais leur vie séparément.

## Et l'iPhone

L'app pointe vers `https://51-159-130-158.nip.io/mobile`, avec son jeton — adresse et
jeton dans le fichier d'accès du Mac, à recopier dans Paramètres › Connexion à Oris.

Pour que le téléphone soit vraiment autonome, il reste à passer par **TestFlight**
(compte développeur Apple de Franck) : l'app s'installe alors sans câble et sans Mac, et
n'expire plus.
