# Oris — Projet maître

**Fichier de référence pour Franck.** Une page pour savoir où en est Oris, ce qui
fonctionne, ce qui bloque et ce qui est attendu de vous. Mis à jour à la fin de
chaque jalon.

Dernière mise à jour : 19 septembre 2026 (la chaîne complète micro → compte rendu est branchée).
Dépôt : `drfranckmoyal-cloud/orisapp` (privé) · Dossier : `~/Desktop/Claude-Projects/ORIS`

---

## 1. Ce qu'est Oris

Un assistant qui écoute la consultation et prépare le compte rendu, le plan de
traitement et les comptes rendus opératoires. Trois principes tiennent tout :

1. **Le dossier clinique est la source de vérité**, pas le texte. Les documents en
   sont une écriture ; une correction modifie d'abord le dossier, puis Oris réécrit.
2. **Rien n'est inventé.** Chaque phrase s'appuie sur un fait, qui s'appuie sur une
   parole. Ce qui n'a pas été dit n'est pas écrit.
3. **Le praticien valide.** Aucun document n'est validé automatiquement.

---

## 2. Où en est le projet

| Jalon | Contenu | État |
|---|---|---|
| M0 | Fondations : serveur, base de données, formats communs, coquilles web et iPhone | **Terminé** |
| M1 | Consultation fictive de bout en bout : faits, compte rendu, plan, corrections, validation | **Terminé** |
| M2 | Écoute au micro sur le site | **Terminé** |
| M3 | Écoute sur iPhone (appels, écouteurs, écran verrouillé) | **Terminé, non vu à l'écran** |
| M4 | Banc d'essai des services de transcription (Azure, Deepgram) | **Terminé** — Deepgram mesuré le 18 sept. sur 100 consultations |
| M5 | Extraction clinique par une vraie IA (Claude) | **Terminé** — mesuré sur le corpus |
| M6 | Écran de consultation : sortie des documents, plan en cartes | **Terminé** |
| M7 | Comptes rendus opératoires (sept modèles d'actes) | **Terminé** |
| M8 | Correction dictée (« remplace 26 par 27 ») | **Terminé** |
| M9 à M11 | Apprentissage, sécurisation, validation clinique | À faire |

Détail par jalon : `docs/CHANGELOG.md`. Décisions techniques : `docs/IMPLEMENTATION_LOG.md`.

---

## 3. Ce qui fonctionne aujourd'hui

**Sur le site (ordinateur)**
- Créer des patients fictifs, lancer une des 100 consultations fictives, obtenir
  compte rendu et plan de traitement.
- Cliquer une phrase pour voir d'où elle vient : les faits et la parole d'origine.
- **Corriger en dictant** : « remplace 26 par 27 », « le patient a accepté les
  composites », « retire la phrase sur la sensibilité ». Oris montre d'abord ce qu'il a
  compris ; rien n'est appliqué sans votre confirmation. S'il hésite entre deux éléments,
  il vous demande — il ne choisit pas à votre place. Une demande de forme (« fais plus
  court ») ne touche jamais au dossier clinique.
- Corriger une dent ou le statut d'un traitement : le dossier passe en version
  suivante, les documents sont réécrits, la correction est retenue pour l'apprentissage.
- Lire le plan de traitement **carte par carte** : pour chaque traitement, les dents, le
  statut, pourquoi il est proposé, les alternatives évoquées et ce qui doit être fait
  avant. Le statut se change là, sur la carte.
- Valider document par document, puis la consultation.
- **Exporter en PDF** (A4, avec cabinet, praticien, patient, date et mention de
  validation) et **copier pour le dossier** pour coller dans votre logiciel métier. Un
  document non validé part avec la mention « brouillon » écrite dessus.
- **Compte rendu de soins** : quand un acte a été fait, Oris le propose — il ne le crée
  jamais tout seul. Sept modèles (composite, esthétique direct, préparation de facettes,
  collage de facettes, usures, avulsion, chirurgie mineure). Chaque modèle est une liste
  d'emplacements : seuls ceux que vous avez dits sont écrits. Votre adhésif habituel n'est
  jamais inscrit « par défaut ». Si un champ important manque, Oris le signale, il ne le
  remplit pas.
- Chaque type de document a sa **mise en page** : compte rendu de consultation, plan de
  traitement, compte rendu de soins, courrier à un confrère (avec formule d'appel et
  signature), résumé patient (texte plus grand, mention de remise).
- Enregistrer au micro : pause, reprise, coupure réseau, page rechargée. Toute
  interruption devient une alerte rouge ; le son est supprimé après traitement.

**Sur l'iPhone**
- Liste des consultations et lecture d'une consultation (compte rendu, plan, à vérifier).
- Écoute d'une consultation : appel entrant, AirPods retirés, écran verrouillé,
  réseau coupé, app fermée — chaque cas est géré et signalé.

**Avec les vrais moteurs (depuis le 18 septembre)**
- Deepgram transcrit : sur 100 consultations lues par des voix de synthèse, 100 % des
  numéros de dent et des négations sont justes, 8,2 % d'erreur de mots.
- Claude lit le transcript et en tire les faits : dent concernée, négation, incertitude,
  prévu ou réalisé. Le résolveur refuse ce qui ne tient pas, et Claude a droit à trois
  essais, chacun accompagné de la raison du refus. Environ 3,6 centimes par consultation.
- Quand une consultation échoue malgré tout, elle est marquée en échec **avec la raison**,
  et aucun document n'est écrit : jamais de compte rendu approximatif.
- Ces deux moteurs restent **désactivés par défaut** : il faut une clé et un accord
  explicite dans le fichier de réglages privé.

**La chaîne complète (depuis le 19 septembre)**
- Une consultation enregistrée part chez Deepgram, puis le transcript chez Claude, puis
  le compte rendu est écrit : vérifié de bout en bout sur un vrai fichier audio, en 5
  secondes, sans aucun problème de validation.
- Une consultation fictive, elle, n'est jamais envoyée dehors.
- **Nouveau point de vigilance** : sur nos enregistrements, Deepgram ne sépare pas les
  voix (72 % reviennent d'une seule voix). Quand Oris ne sait pas qui parle, il le dit
  — alerte « vérifiez qui a dit quoi » — au lieu de faire semblant. Une phrase du
  patient ne peut plus devenir un constat du praticien par défaut.

**Ce qui n'existe pas encore**
- La dictée des corrections n'a pas encore été essayée avec un vrai micro (je n'en ai
  pas) : le circuit est vérifié par les tests, pas par la voix.
- Le PDF porte le logo Oris tant que vous ne m'avez pas donné celui du cabinet.
- Les courriers au confrère et les résumés patient ont leur mise en page, mais leur
  contenu n'est pas encore rédigé par Oris.
- Pas de compte utilisateur ni de mot de passe : usage local uniquement.

---

## 4. Ce que j'attends de vous

| Quoi | Pourquoi | Quand |
|---|---|---|
| **Logo et coordonnées du cabinet** (fichier image + adresse, téléphone, mention légale) | Ils s'impriment en tête de chaque document ; pour l'instant c'est le logo Oris | Quand vous voulez |
| **Compléter `docs/VOCABULAIRE.md`** | Oris n'écrit que ce qu'il sait nommer ; ce qu'il ignore est signalé « à rédiger » | Quand vous voulez, thème par thème |
| Clé Azure Speech (optionnel) | Comparer Deepgram à un fournisseur certifié HDS | Avant de choisir |
| Autoriser le **simulateur iPhone** (« Let Claude use it ») | Pour que je vérifie l'app à l'écran, pas seulement par les tests | Quand vous voulez |
| **Enregistrements de consultations jouées** par des praticiens | Les voix de synthèse ne suffisent pas pour choisir un fournisseur | Avant de choisir |
| **Tarifs et statut de conformité** des fournisseurs (`benchmarks/providers.json`) | Je n'invente aucun prix ni aucune conformité | Avant de choisir |
| Cadrage **HDS / RGPD** (hébergement agréé données de santé) | Aucune donnée de patient réel tant que ce n'est pas fait | Avant tout patient réel |

**Règle sur les clés** : vous les déposez vous-même dans `services/api/.env`, un fichier
privé qui ne part jamais sur GitHub. Jamais dans une conversation, jamais dans le code.

---

## 5. Ce qui est figé, ce qui reste ouvert

**Figé** (décisions produit, `docs/DECISIONS.md`) : nom Oris, iPhone natif + site web,
serveur commun, français d'abord, dossier clinique source de vérité, documents comme
écriture, validation obligatoire, audio éphémère, provenance consultable, esthétique et
usures en priorité, implantologie et endodontie hors V1, identité visuelle.

**Ouvert, à trancher plus tard** : quel service de transcription, quel moteur d'IA pour
l'extraction, quel hébergeur agréé, tarif de l'abonnement, identifiant de l'app iPhone.

---

## 6. Les limites à ne pas oublier

Liste complète : `docs/KNOWN_LIMITATIONS.md`. Les quatre plus importantes :

1. **Les scores viennent de consultations inventées**, lues par des voix de synthèse et
   écrites pour ce projet : ils ne disent rien du bruit d'un vrai cabinet.
2. **Rien n'est prêt pour un vrai patient** : ni hébergement agréé, ni authentification,
   ni chiffrement du son côté serveur.
3. **Les scores sont flatteurs** : ils sont mesurés sur des consultations inventées,
   lues par des voix de synthèse, écrites pour ce projet.
4. **L'app iPhone n'a jamais tourné devant quelqu'un** : elle est vérifiée par
   39 tests automatiques, pas à l'écran.

---

## 7. Lancer Oris sur le Mac

Je lance ces commandes moi-même quand vous me le demandez. Pour mémoire :

```bash
services/api/.venv/bin/python scripts/dev_postgres.py start   # base de données
cd services/api && .venv/bin/uvicorn oris_api.main:app --port 8000 --no-access-log
cd apps/web && npm run dev                                     # http://localhost:3000
open apps/ios/Oris.xcodeproj                                   # app iPhone
```

Détails, tests et banc d'essai : `docs/DEVELOPMENT.md` et `benchmarks/README.md`.

---

## 8. Où est quoi

| Fichier | Contenu |
|---|---|
| `PROJET-MAITRE.md` | **Ce fichier** : état du projet, en français simple |
| `ORIS_MASTER_SPEC_V1_2.md` | La spécification produit d'origine (source de vérité, non modifiée) |
| `CLAUDE.md` | Les règles permanentes que je dois suivre en codant |
| `docs/DECISIONS.md` | Décisions produit figées |
| `docs/IMPLEMENTATION_PLAN.md` | Les jalons M0 à M11 |
| `docs/IMPLEMENTATION_LOG.md` | Mon journal : ce que j'ai construit et pourquoi, jalon par jalon |
| `docs/CHANGELOG.md` | Ce qui a été livré à chaque jalon |
| `docs/VOCABULAIRE.md` | **Les 227 termes qu'Oris sait écrire, par thème — à compléter par vous** |
| `docs/KNOWN_LIMITATIONS.md` | Ce qui ne marche pas encore, et les pièges |
| `docs/DEVELOPMENT.md` | Comment lancer et vérifier le projet |
| `benchmarks/README.md` | Banc d'essai des services de transcription |
| `services/api` · `apps/web` · `apps/ios` | Le serveur, le site, l'app iPhone |

---

## 9. Journal des jalons

| Date | Jalon | Tests au vert |
|---|---|---|
| 16 sept. 2026 | Paquet de spécification reçu, dépôt créé (`product-spec-v1.2`) | — |
| 17 sept. 2026 | M0 — fondations | 45 serveur · 8 web · 9 iPhone |
| 17 sept. 2026 | M1 — consultation fictive complète, tests critiques A–J | 104 · 13 · 14 |
| 17 sept. 2026 | M2 — écoute au micro sur le site | 126 · 33 · 14 |
| 17 sept. 2026 | M3 — écoute sur iPhone | 129 · 33 · 39 |
| 17 sept. 2026 | M4 — banc d'essai transcription (code) | 174 · 33 · 39 |
| 18 sept. 2026 | M4 — premier banc réel : Deepgram Nova-3, 100 consultations lues | dents 100 %, négations 100 %, WER 8,2 %, voix 86,9 % |
| 18 sept. 2026 | M5 — extraction clinique par Claude, 100 consultations, 2 modèles | Sonnet : 94 % abouties, 0 % de rejet, négations 98,6 %, 3,2 c/consultation ; 186 tests serveur |
| 19 sept. 2026 | Vocabulaire : 269 termes classés par thème, dont vos 51 termes dictés | 196 tests serveur |
| 20 sept. 2026 | M8 — correction dictée : phrase → patch structuré, aperçu avant application | 239 serveur · 47 web |
| 19 sept. 2026 | M7 — comptes rendus opératoires : sept modèles d'actes, vérifiés sur quatre types en conditions réelles | 222 serveur · 43 web |
| 19 sept. 2026 | M6 — sortie des documents (PDF A4, copie pour le dossier) et plan de traitement en cartes | 202 serveur · 43 web |
| 19 sept. 2026 | Chaîne complète micro → Deepgram → Claude → compte rendu, vérifiée sur un vrai fichier audio | 190 tests serveur |
| 18 sept. 2026 | M5bis — les six consultations en échec comprises : variation du modèle, pas défaut de fond | les 6 aboutissent avec trois essais ; 188 tests serveur |

**Défauts trouvés et corrigés en cours de route** (le détail est dans le journal) :
faits affichés « vérifiés par le praticien » sans l'être ; refus d'une décision
légitime du praticien ; règle d'attribution des rôles qui prenait le patient pour le
praticien dans 10 consultations sur 100 ; panne du moteur d'extraction qui faisait
tomber la consultation en erreur technique au lieu d'un échec propre et expliqué.
