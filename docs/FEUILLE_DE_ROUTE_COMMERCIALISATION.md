# Feuille de route — Oris commercialisable

*Écrite le 21 septembre 2026, à la demande de Franck : « rendre l'app commercialisable,
les clients passent du téléphone à l'ordinateur sans souci, avec les mêmes données ».*

## Le choix d'architecture (décision D027)

**Un seul serveur Oris, hébergé chez un hébergeur agréé données de santé (HDS).** Le site
et l'app iPhone en sont deux fenêtres, par Internet ; aucune ne dépend de l'autre, et les
données sont les mêmes des deux côtés parce qu'il n'en existe qu'une copie.

Écarté : chaque appareil garde sa copie et se synchronise (« local-first »). Deux versions
d'un même compte rendu à réconcilier seraient un risque clinique, et la transcription
comme la rédaction ne tiennent pas dans un téléphone.

Ce qui reste local à l'iPhone : le son d'une écoute en cours, chiffré, jusqu'à ce qu'il
soit reçu par le serveur (déjà en place).

## Ce qui existe déjà

- Plusieurs cabinets dans une même base : chaque dossier est rangé au nom de son cabinet,
  chaque praticien est membre d'un cabinet ; un cabinet ne voit jamais les données d'un
  autre.
- Journal d'audit, purge du son, accès par jeton, validation obligatoire des documents.
- Site et app iPhone au même niveau de fonctions pour le quotidien.

## Les étapes

### Étape 1 — Comptes et connexion *(Claude, peut commencer tout de suite)*

Aujourd'hui l'accès se fait par jeton collé à la main. Un produit vendu a besoin de :
- création d'un cabinet, invitation d'un confrère ou d'une assistante, rôles ;
- connexion par mail + mot de passe + **code à usage unique** (application
  d'authentification), mot de passe oublié ;
- **Pro Santé Connect** (connexion avec la carte e-CPS des professionnels de santé) à
  prévoir : c'est ce que les praticiens connaissent et ce que l'État recommande ;
- sur l'iPhone : un écran de connexion à la place du jeton ; déconnexion à distance d'un
  appareil perdu.

### Étape 2 — Oris prêt à être installé chez un hébergeur *(Claude)*

- Serveur et site emballés pour s'installer tels quels (conteneurs), réglages par
  l'environnement, adresse en https ;
- sauvegardes chiffrées et restauration **essayée**, supervision, journaux sans donnée
  patient ;
- deux environnements : essai (données fictives) et production ;
- l'app iPhone pointe vers une adresse fixe (fini l'adresse du Mac).

### Étape 3 — Décisions et démarches *(Franck — Claude prépare les dossiers)*

| Sujet | Pourquoi c'est bloquant |
|---|---|
| **Hébergeur HDS** (OVHcloud, Scaleway, Outscale, Azure, AWS…) | Obligatoire pour héberger des données de santé pour le compte de tiers |
| **Certification HDS d'Oris lui-même** | L'éditeur qui *exploite* le logiciel pour ses clients peut devoir être certifié en plus de l'hébergeur, selon ce que l'hébergeur prend en charge (infogérance). **À faire trancher par un spécialiste** |
| **Fournisseurs d'IA hébergés en Europe** | Deepgram et Anthropic en direct traitent aux États-Unis. Pour des clients : transcription et Claude servis depuis l'Europe (ex. Claude via AWS Bedrock ou Google Vertex en région UE, transcription Azure France), contrats de sous-traitance signés |
| **Qualification réglementaire** | Vérifier qu'Oris n'est pas un dispositif médical (il documente, il ne diagnostique pas) : avis écrit à obtenir |
| **Structure juridique, assurance** | Pour facturer, signer avec les hébergeurs et les clients |
| **Contrats clients** | CGU/CGV, accord de sous-traitance RGPD (Oris traite les données *pour le compte* du cabinet), information des patients |
| **Compte développeur Apple « organisation »** | Publier l'app au nom de la société (numéro D-U-N-S) |

### Étape 4 — Mise en ligne d'essai *(ensemble)*

Serveur installé chez l'hébergeur choisi, **avec des données fictives** ; Franck travaille
sur l'iPhone et l'ordinateur sans le Mac du cabinet. Test de coupure, de restauration,
d'appareil perdu.

### Étape 5 — Pilote

Franck puis quelques confrères, patients réels **seulement une fois l'étape 3 bouclée**.
App distribuée par TestFlight (la bêta d'Apple).

### Étape 6 — Commercialisation

App Store, abonnement et facturation, page d'inscription, support, audit de sécurité
(test d'intrusion) avant l'ouverture.

## Ordre conseillé

Les étapes 1 et 2 ne dépendent d'aucune décision : elles avancent pendant que l'étape 3
se règle. L'étape 3 est la plus longue : c'est elle qui fixe la date de lancement.
