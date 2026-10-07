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
| `/` | le navigateur | mot de passe du site |
| `/api/` | le navigateur (appels du site) | mot de passe du site ; **nginx ajoute le jeton du praticien**, que le navigateur ne voit jamais |
| `/mobile/` | l'app iPhone | **son propre jeton**, vérifié par le serveur |

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

## Ce qui n'est pas en place

- **Aucune sauvegarde.** À faire avant d'y mettre quoi que ce soit d'important.
- **Pas de contrat HDS** avec Scaleway : tant qu'il n'est pas signé, ce serveur ne doit
  porter que des consultations fictives (voir `docs/CONTRAINTES_COMMERCIALISATION.md`).
- **Pas de surveillance** : si un service tombe, personne n'est prévenu (systemd le
  relance tout seul, mais sans le dire).
- Le certificat https se renouvelle seul (certbot), échéance visible avec
  `certbot certificates`.

## Et l'iPhone

L'app pointe vers `https://51-159-130-158.nip.io/mobile`, avec son jeton — adresse et
jeton dans le fichier d'accès du Mac, à recopier dans Paramètres › Connexion à Oris.

Pour que le téléphone soit vraiment autonome, il reste à passer par **TestFlight**
(compte développeur Apple de Franck) : l'app s'installe alors sans câble et sans Mac, et
n'expire plus.
