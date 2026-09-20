# Changelog

## M11 — 2026-09-20 — mise en situation clinique
- **mode ombre** : Oris travaille en parallèle du praticien pour être comparé ; ses
  documents ne peuvent être ni validés ni exportés, la règle est appliquée côté serveur ;
- **porte d'entrée en bêta exécutable** (`scripts/beta_gate.py`) : elle refuse tant que
  les fournisseurs ne sont pas revus, que les flux de données ne sont pas documentés, que
  des séances jouées par des praticiens manquent, ou que l'hébergement agréé n'est pas là ;
- **inventaire des flux fournisseurs** (`docs/VENDORS.md`) : finalité, données envoyées,
  région, conservation, entraînement, sous-traitants, DPA — et ce qui ne sort jamais ;
- **contrôle des jeux d'enregistrements** (`scripts/check_dataset.py`) : format,
  consentement documenté et référencé, rôles présents ;
- correction d'interface : un `hidden` était écrasé par un `display` de classe ;
- tests : API 266, web 47.

## M10 — 2026-09-20 — sécurisation
- **jetons d'accès** par praticien (`Authorization: Bearer`), empreinte scrypt salée,
  révocation immédiate ; `scripts/issue_token.py` pour créer, lister, révoquer ;
- **aucune route métier sans jeton** hors développement : il n'existe pas de mode ouvert ;
- **journal d'audit lisible** (`GET /audit`) : identifiants, actions, statuts et versions,
  jamais une phrase clinique — un test échoue si un mot clinique y entre ;
- défaut corrigé : les actions du système (génération, purge) étaient enregistrées sans
  organisation et n'apparaissaient donc pas dans le journal ;
- **purge du son rejouable et observable** (`POST /maintenance/audio-purge`) : une panne
  de stockage n'interrompt pas la passe et ressort dans le rapport ;
- `docs/SECURITY.md` distingue désormais ce qui est fait de ce qui relève de
  l'hébergement (MFA, chiffrement au repos, sauvegardes, HDS, tests de charge) ;
- migration 0005 ; tests : API 255.

## M9 — 2026-09-20 — personnalisation
- **dictionnaire du praticien** (`learning.glossary_terms`, migration 0004) : marques,
  produits et termes propres au cabinet, soufflés à la transcription **et** à
  l'extraction — ils ne l'étaient pas ;
- **préférences de rédaction** : mot préféré par concept (« avulsion » pour
  « extraction ») et compte rendu concis (les préfixes qui répètent le titre de section
  disparaissent, jamais une nuance clinique) ;
- **suggestions** : après deux corrections dans le même sens, Oris propose une règle —
  et ne l'applique jamais de lui-même ;
- **tout est réversible** : désactiver un terme, retirer un mot préféré, revenir au
  format standard ;
- écran « Oris apprend de vous » sur le site ;
- `material_name_correction` : corriger un nom de produit alimente les suggestions ;
- tests : API 245.

## M8 — 2026-09-20 — correction dictée
- une phrase du praticien devient un **patch structuré** de l'objet clinique, jamais une
  retouche du texte : remplacement de dent, ajout de dent, retrait d'un élément,
  changement de statut d'un traitement ;
- **aperçu d'abord** : Oris montre ce qu'il a compris et l'impact ; appliquer demande une
  confirmation explicite et la version d'objet attendue ;
- ce qui est ambigu n'est pas deviné : la commande revient avec la raison et les éléments
  possibles, écrits en français ;
- une préférence de rédaction (« plus court ») est distinguée d'une correction clinique :
  elle est retenue pour l'apprentissage et ne touche pas au dossier (§46) ;
- `POST /encounters/{id}/corrections/voice` : l'audio est transcrit dans la requête puis
  oublié, il n'entre jamais dans le stockage de la consultation ;
- sur le site : dicter au micro ou écrire, relire le patch, appliquer ;
- tests : API 239, web 47.

## M7 — 2026-09-19 — comptes rendus opératoires
- les sept modèles de la spécification (composite, esthétique direct, facettes
  préparation, facettes collage, usures additives, avulsion, chirurgie mineure) : des
  **emplacements de preuve ordonnés**, jamais des paragraphes préremplis ;
- un emplacement se renseigne s'il a été dicté dans l'acte, ou par un fait dit pendant
  l'intervention (la phrase cite alors ce fait) ; rien d'autre ne le remplit ;
- un emplacement important resté vide **alerte** (« champ important non dicté ») et n'est
  jamais complété ; un acte seulement prévu n'est pas interrogé sur ses matériaux ;
- le compte rendu de soins n'est jamais produit d'office : le site propose « un acte a
  été détecté », le praticien décide (§81) ; une fois demandé, il suit les corrections ;
- invite d'extraction `extraction-fr-5` : le modèle connaît les emplacements de chaque
  type d'acte et vise les bonnes clés ;
- vérifié de bout en bout sur quatre types d'acte, transcription et extraction réelles ;
- tests : API 222.

## Habillage des documents — 2026-09-19
- un modèle d'impression par type : compte rendu de consultation, plan de traitement,
  **compte rendu de soins**, **courrier d'adressage** (formule d'appel, politesse,
  signature), **résumé patient** (texte plus grand, mention de remise) ;
- en-tête habillé : logo, nom et coordonnées du cabinet, praticien, patient, date, rappel
  de validation ; couleurs du système de design ;
- identité du cabinet configurable dans `services/api/config/cabinet.json` ; sans ce
  fichier, l'en-tête reste sobre et le document sort quand même ;
- dépendance `pillow` (logo) ;
- tests : API 208.

## M6 (2/2) — 2026-09-19 — plan de traitement en cartes
- chaque élément du plan devient une carte : dents, intitulé, statut, motif, faits
  d'appui cliquables, alternatives, préalables, incertitudes ; le statut se change sur
  la carte, et c'est toujours le dossier clinique qui est modifié ;
- l'historique dit ce qu'une correction a changé (« proposé → accepté ») ;
- logique de correction mutualisée (`useCorrection`) entre les écrans qui corrigent ;
- tests : web 43.

## M6 (1/2) — 2026-09-19 — sortie des documents
- `GET /documents/{id}/export?format=pdf|text|structured` : PDF A4 (identité du cabinet
  et du praticien, patient, date, type, mention de validation, pagination), texte brut,
  texte structuré ;
- sur le site : **Copier pour le dossier** et **Exporter en PDF**, avec repli sur une
  zone de texte sélectionnable si le navigateur refuse le presse-papiers ;
- un brouillon peut sortir mais porte la mention « non validé », et son statut ne change
  pas ; seul un document validé passe à `exported`, et la consultation passe à
  `exported` quand tous ses documents en sont sortis ;
- le nom du fichier ne porte pas le nom du patient ;
- dépendance `reportlab` ;
- tests : API 202, web 35.

## Vocabulaire (2) — 2026-09-19 — termes dictés par le praticien
- 42 termes intégrés depuis la dictée du 19/09 : **269 termes**, 16 thèmes (nouveau
  thème « Matériaux, produits et instruments ») ;
- cinq noms propres et sigles ajoutés au glossaire envoyé à la transcription (Astéria,
  SmileCloud, peroxyde de carbamide, zircone, DVO) : ce glossaire est plafonné à 50
  termes, contrairement au vocabulaire de rédaction qui n'a pas de limite ;
- « adressage à un confrère » devient « adressage à un confrère ou une consœur ».

## Vocabulaire — 2026-09-19
- vocabulaire clinique porté de 50 à **227 termes**, classés en 15 thèmes (motif,
  symptômes, examen dentaire, usures et esthétique, parodonte et occlusion, examens
  complémentaires, diagnostics, options, projet esthétique, actes directs, prothèse,
  chirurgie, informations au patient, antécédents, suivi) ;
- `docs/VOCABULAIRE.md` : la liste lisible par le praticien, produite depuis le code par
  `scripts/vocabulaire.py`, avec un tableau « à ajouter » par thème ; un test échoue si
  la liste dérive du code ;
- effet mesuré sur la consultation de démonstration : « À rédiger : élément « crowns »
  non reconnu » devient « Option écartée : couronnes », et les deux documents passent de
  1 à 0 problème de validation ;
- tests : API 196.

## M5ter — 2026-09-19 — la chaîne complète micro → compte rendu
- une consultation enregistrée part désormais chez Deepgram puis chez Claude :
  vérifié de bout en bout sur un vrai fichier audio poussé comme le fait le micro du
  site (4 segments de 2 s) → transcription, audio purgé, faits extraits, compte rendu
  rendu en 5 s, zéro problème de validation, négation conservée ;
- une consultation fictive ne part plus chez un fournisseur réel : son « enregistrement »
  est une étiquette que seul le fournisseur factice sait lire (`synthetic_speech_to_text`) ;
- nouvelle alerte `SPEAKER_ROLES_UNKNOWN` (à vérifier, non bloquante) quand un segment
  reste sans rôle : sans voix séparées, rien ne garantit qu'une parole du patient n'a pas
  été écrite comme un constat du praticien (invariant 5) ;
- banc d'essai STT : nouvelle mesure `single_voice_rate`. Le score « locuteurs bien
  séparés » récompensait un fournisseur qui met tout le monde dans la même voix —
  mesuré : **72 % des enregistrements reviennent d'une seule voix** ;
- une voix unique n'est plus traitée comme « une seule personne » : chaque passage est
  jugé sur ses propres mots, et reste sans rôle s'il n'a rien de décisif ;
- Deepgram reprend deux fois une panne passagère (réseau, 429, 5xx, 408) : le banc du
  19/09 perdait 5 consultations sur 30 pour des incidents de quelques secondes ;
- le site affiche les alertes « à vérifier » (jusqu'ici seules les alertes critiques
  étaient visibles : la nouvelle alertes sur les voix serait passée inaperçue) ;
- imports différés des adaptateurs STT dans la fabrique (dépendance circulaire) ;
- tests : API 191, web 33.

## M5bis — 2026-09-18 — les six échecs compris et corrigés
- diagnostic : les six consultations refusées par Sonnet ne l'étaient pas de façon
  systématique — rejouées, elles aboutissent. Le modèle varie d'un appel à l'autre, et
  deux d'entre elles n'aboutissent qu'au **troisième** essai ;
- nombre d'essais expliqués porté de deux à trois ; une coupure réseau, un quota (429)
  ou une erreur serveur repasse le même appel deux fois (1 s puis 4 s) au lieu de perdre
  la consultation ;
- un échec dit désormais **ce qui** a été refusé : `ExtractionUnavailable` porte des
  `details`, dont `rule_codes()` n'extrait que les noms de règles (aucun contenu clinique) ;
- défaut corrigé : une panne du fournisseur d'extraction remontait en erreur 500 au lieu
  de classer la consultation en `generation_failed` ; le pipeline l'attrape et affiche
  les règles refusées ;
- vérifié : les six consultations aboutissent (2 au 1er essai, 2 au 2e, 2 au 3e) ;
  tests API 188.

## M5 — 2026-09-18 — Clinical extraction
- extraction clinique réelle par Claude derrière `ClinicalExtractionProvider` : sortie
  imposée par un outil dont le schéma vient des contrats d'Oris, provenance posée par
  Oris, consignes versionnées (`extraction-fr-4`) ;
- une sortie invalide ou contraire aux règles cliniques donne droit à des essais
  expliqués par le résolveur (deux à l'origine, trois depuis M5bis), puis elle est
  rejetée — jamais corrigée ;
- garde-fou `ALLOW_EXTERNAL_LLM` + clé locale ; tests forcés en mode factice ;
- banc d'essai extraction (100 consultations du corpus, 2 modèles comparés) :
  Sonnet 5 → 94 % d'extractions abouties, 0 % de rejet par le résolveur, négations
  98,6 %, temporalité 98,3 %, prévu/réalisé 94,2 %, 3,2 centimes par consultation ;
  Haiku 4.5 → 69 % d'extractions abouties, 1,5 centime ;
- règle corrigée : un emplacement d'acte est valide s'il a été **prononcé** dans les
  segments cités ;
- démonstration dans l'application : consultation fictive traitée par le vrai modèle,
  compte rendu « Suspicion de fissure (16), non confirmée », zéro problème de validation ;
- tests : API 186, web 33, iOS 39.

## M4bis — 2026-09-18 — premier banc d'essai réel
- Deepgram Nova-3 mesuré sur les 100 consultations synthétiques (35 min d'audio) :
  numéros de dent 100 % (243 mentions, 0 inventé), négations 100 %, WER 8,2 %,
  termes dentaires 81 % (dont +13,4 points apportés par le glossaire), séparation
  des voix 86,9 %, rôles 83,7 %, délai médian 1,7 s, 100 % de requêtes abouties ;
- conformité non évaluée → aucun fournisseur retenu (gate).

## M4 — 2026-09-17 — STT benchmark adapter
- adaptateurs Azure AI Speech (transcription rapide `2025-10-15` + SDK temps réel
  `ConversationTranscriber`) et Deepgram Nova-3 (fichier + WebSocket) derrière
  `SpeechToTextProvider` / `StreamingSpeechToTextProvider` ;
- diarisation : étiquettes brutes séparées, rôles praticien/patient attribués par
  heuristique prudente (`unknown` si doute) ;
- glossaire dentaire (≤ 50 termes) poussé en phrase list / keyterms ;
- temps réel Deepgram : reconnexion avec renvoi de l'audio non confirmé ;
- garde-fou : STT externe seulement avec `ALLOW_EXTERNAL_STT=true` et clés locales ;
- panne du fournisseur : `STT_UNAVAILABLE`, audio conservé, bouton « Relancer le
  traitement » sur le web ;
- numéros de dent dits en lettres → chiffres FDI (`domain/dental_numbers.py`) ;
- banc d'essai : jeu synthétique (100 consultations, voix macOS), métriques de la note
  technique, score pondéré, conformité en préalable, `EvaluationRun` + rapport français,
  contrôle hors ligne `check` ;
- tests : API 171, web 33, iOS 39.

## M3 — 2026-09-17 — iOS audio capture
- écoute iPhone : AVAudioSession (parole, micro AirPods) + AVAudioEngine, même
  contrat audio que le web (PCM 16 kHz mono, segments de 2 s, SHA-256) ;
- tampon local chiffré AES-GCM (clé dans le trousseau de l'appareil, fichiers
  protégés, hors sauvegardes), segments effacés dès l'accusé de réception ;
- appel / Siri : écoute suspendue sans reprise automatique, durée signalée comme trou ;
- AirPods retirés ou nouvelle entrée : capture relancée, trou signalé au-delà d'1 s ;
- écran verrouillé : écoute poursuivie (mode audio en arrière-plan) ;
- coupure réseau : capture continue, renvoi dans l'ordre, relance immédiate au retour
  du réseau ; « Terminer malgré tout » ;
- app fermée : segments chiffrés renvoyés à la réouverture, trou `app_terminated`,
  reprise ou fin proposées ;
- micro refusé : explication et accès aux Réglages ;
- écrans : nouvelle consultation (patient), pré-écran, écoute plein écran ;
- serveur : motifs de trou `audio_interruption`, `route_change`, `app_terminated` ;
- tests : API 129, web 33, iOS 39.

## M2 — 2026-09-17 — Web audio capture
- capture micro dans le navigateur (AudioWorklet), PCM 16 kHz mono en segments de 2 s
  horodatés à l'échantillon ;
- envoi ordonné et idempotent (numéro de séquence, SHA-256), nouvelles tentatives
  illimitées pendant une coupure réseau, suppression locale après accusé de réception ;
- pause / reprise (micro libéré pendant la pause), durée maximale 90 min avec alerte à 80 ;
- micro perdu, page rechargée, segments non envoyés : trous déclarés → alerte critique
  `AUDIO_GAP` ; fin d'écoute refusée tant que des segments manquent, sauf « Terminer
  malgré tout » explicite ;
- pré-écran : patient, autorisation micro, réseau, information patient paramétrable
  (`PATIENT_INFORMATION_MODE`) ;
- audio éphémère purgé après traitement, métadonnées de réception conservées ;
- source de son de test sans micro (local uniquement) ;
- migration 0003 : `audio_sessions`, `audio_chunks` ;
- tests : API 126, web 33 (dont capture sans navigateur), iOS 14.

## M1 — 2026-09-17 — Synthetic vertical slice
- parcours complet sur consultation fictive : patient → consultation → transcript →
  faits → objet clinique versionné → compte rendu + plan → validation explicite ;
- résolveur déterministe : sortie d'extraction rejetée (jamais corrigée) si preuve
  inventée, acte futur « réalisé », impression du patient promue en constat ou
  diagnostic, incertitude perdue, option acceptée sans décision, matériau non
  prononcé, ou fait prétendument validé par le praticien ;
- rédaction française par gabarits depuis l'objet seul ; chaque phrase cite ses faits ;
- validateur factuel (phrase sans appui, dent non portée, « Réalisé » sans acte réalisé,
  fait non restitué, concept inconnu) ;
- coupure audio : alerte critique, document déclaré non exhaustif, validation
  conditionnée à une reconnaissance explicite ;
- corrections structurées (dent, fait, statut du plan, ajout, retrait) : nouvelle
  version de l'objet → documents périmés → régénération ; historique append-only ;
- LearningEvents dans le schéma `learning` (corrections, alerte reconnue, validation
  sans modification) ;
- web : écrans patients, consultations, nouvelle consultation fictive, révision
  (source de chaque phrase, faits, corrections, historique, validation) ;
- iPhone : liste des consultations et consultation en lecture (Compte rendu | Plan |
  À vérifier) ;
- contrats : OpenAPI exporté, types web générés, réponses réelles figées pour les
  tests iOS ;
- migration 0002 : `encounter_object_versions`, phrases et problèmes des documents ;
- tests : API 104, web 13, iOS 14.

## M0 — 2026-09-17 — Repository & contracts
- monorepo : `services/api` (FastAPI), `apps/web` (Next.js), `apps/ios` (SwiftUI) ;
- types Python/TypeScript/Swift générés depuis `schemas/` (`scripts/generate_contracts.py`, vérifié en CI) ;
- tokens visuels web/iOS générés depuis `design/tokens.json` ;
- PostgreSQL + migration Alembic initiale : dossier clinique et learning store (schéma `learning` séparé) ;
- valeurs d'enum des contrats imposées par contraintes CHECK en base ;
- interfaces des 4 fournisseurs IA + implémentations mock ; tout fournisseur non-mock refusé ;
- journalisation JSON en liste blanche (aucun nom, transcript, message d'exception, query string) ;
- `GET /health`, `GET /health/ready` ;
- coquilles web et iPhone en français affichant l'état du serveur ;
- CI GitHub Actions : contrats, API (PostgreSQL), web ; iOS sur changement ;
- tests : API 45, web 8, iOS 9.

## v1.2 — 2026-09-16
- final audit;
- Oris naming frozen;
- visual identity frozen for V1;
- machine-readable schemas added;
- Claude Code starter instructions added;
- synthetic 100-case corpus added;
- technical provider benchmark added;
- learning architecture clarified vs MVP scope.
