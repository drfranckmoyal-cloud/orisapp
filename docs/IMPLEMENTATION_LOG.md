# Implementation Log — Oris

Journal des choix d'implémentation. Chaque milestone commence ici : périmètre,
fichiers touchés, écarts éventuels avec la spec.

Hiérarchie des sources : `ORIS_MASTER_SPEC_V1_2.md` > `docs/DECISIONS.md` >
`schemas/*.schema.json` > ce journal. En cas de conflit, la source la plus haute
l'emporte et le conflit est consigné ici.

---

## M0 — Repository & contracts (2026-09-16)

### Architecture retenue

Monorepo, monolithe modulaire (spec §60–61) :

```text
ORIS/
  apps/
    web/                 Next.js (App Router) + TypeScript strict
    ios/                 SwiftUI, projet Xcode (Oris.xcodeproj)
  services/
    api/                 FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL
  schemas/               JSON Schemas 2020-12 — contrats normatifs (inchangés)
  corpus/, evals/        fixtures synthétiques (inchangées)
  design/tokens.json     tokens visuels (source des couleurs web/iOS)
  infra/docker/          docker-compose PostgreSQL (pour les postes avec Docker)
  scripts/               génération des contrats, base locale
  .github/workflows/     CI : api, web, contrats, iOS
```

Écart assumé avec §61 : les schémas restent dans `schemas/` à la racine au lieu
de `packages/schemas/`. Raison : le corpus (`corpus/synthetic_case.schema.json`)
les référence en `../schemas/`, et le paquet v1.2 est tagué tel quel
(`product-spec-v1.2`). Déplacer casserait ces références sans bénéfice.
`services/worker/` n'est pas créé en M0 : aucun traitement asynchrone n'existe
encore (prévu quand STT/extraction réels arrivent).

### Contrats : une seule définition

`schemas/*.schema.json` est la seule définition des objets cliniques.
`scripts/generate_contracts.py` en dérive :

- `services/api/src/oris_api/contracts/generated.py` (Pydantic v2) ;
- `apps/web/src/contracts/generated.ts` (types TypeScript) ;
- `apps/ios/Oris/Contracts/Generated.swift` (Codable Swift).

Les fichiers générés sont commités et la CI vérifie qu'ils sont à jour
(`--check`). Personne ne les édite à la main.

### Backend (services/api)

- `config.py` : réglages par variables d'environnement (`.env.example`).
  Les fournisseurs IA valent `mock` ; toute autre valeur est refusée en M0.
- `observability.py` : journalisation PHI-safe — format JSON, liste blanche de champs
  (identifiants stables, durées, codes), jamais de corps de requête.
- `providers/` : interfaces `SpeechToTextProvider`, `ClinicalExtractionProvider`,
  `DocumentGenerationProvider`, `ClinicalValidationProvider` (Protocol) +
  implémentations `Mock*` + fabrique selon la configuration.
- `db/models.py` : tables §56 nécessaires au vertical slice M1 : organizations,
  users, organization_members, patients, encounters, transcript_segments,
  clinical_facts, fact_evidence_links, treatment_plans, treatment_plan_items,
  procedures, documents, document_versions, audit_events ; et learning_events
  dans un schéma PostgreSQL séparé `learning` (store logiquement séparé du
  dossier patient, ACCEPTANCE_CRITERIA §Learning).
- `alembic/` : migration initiale.
- `GET /health` (processus) et `GET /health/ready` (base joignable).
- Tests : validation des schémas, du corpus (100 cas) et des cas critiques,
  cohérence contrats générés, fournisseurs mock, santé API, migrations
  aller-retour sur PostgreSQL.
- Qualité : ruff (lint + format), mypy strict, pytest.

### Base locale

Le Mac de développement n'a ni Docker ni Homebrew. `scripts/dev_postgres.py`
lance un PostgreSQL embarqué (paquet PyPI `pixeltable-pgserver`, binaires
officiels PostgreSQL) sur `localhost:5432`, données hors iCloud dans
`~/Library/Application Support/Oris/postgres`. Les postes avec Docker utilisent
`infra/docker/docker-compose.yml`. Même `DATABASE_URL` dans les deux cas.

### Web (apps/web)

Coquille Next.js en français : page d'accueil Oris qui interroge `/health` de
l'API et affiche l'état. Tokens de `design/tokens.json` en variables CSS.
Contrôles : eslint, `tsc --noEmit`, vitest, `next build`.

### iOS (apps/ios)

Coquille SwiftUI (iOS 18+) : écran d'accueil Oris qui interroge `/health`.
Client API typé async/await, modèles générés. Tests unitaires XCTest du
décodage des contrats. Build + tests via `xcodebuild` sur simulateur.

### Hors M0 (volontairement)

Authentification/MFA, CRUD patient, cycle de vie consultation, WebSocket,
audio, Redis, worker, tout fournisseur IA réel.

### Résultat M0 (2026-09-17)

Fonctionne : base locale, migration aller-retour sans écart avec les modèles,
API `/health` et `/health/ready`, site web relié à l'API (vérifié dans le
navigateur), app iPhone compilée et testée sur simulateur.

Contrôles : API ruff + mypy strict + 45 tests ; web eslint + tsc + 8 tests +
build ; iOS 9 tests (Swift 6, warnings = erreurs) ; générateurs `--check` à jour.

Choix faits en cours de route :
- iOS 18 minimum (API `Tab` de SwiftUI) ; bundle id provisoire `fr.oris.app`.
- `node_modules` réel exclu d'iCloud par attribut étendu : un lien symbolique
  `node_modules.nosync` provoquait 113 avertissements Turbopack.
- CI iOS dans un workflow séparé filtré par chemins (coût des minutes macOS).
- Journaux : le champ `event` reprend le gabarit du message sans l'interpoler
  (ex. uvicorn `Uvicorn running on %s://%s:%d`) — voulu, les arguments ne sont
  jamais écrits.

Manque (hors M0) : tout le périmètre M1 (voir IMPLEMENTATION_PLAN.md).


---

## M1 — Synthetic vertical slice (2026-09-17)

Critères lus : ACCEPTANCE_CRITERIA (global, extraction, note, plan, learning),
spec §20–25, §29–34, §46–52, §57–58, §74, §116–118, §127.

### Flux

`Patient → Encounter (draft) → start → finish → [pipeline] → review →
correction (patch) → régénération → validation document → validation consultation`

Pipeline synchrone (pas de worker en M1), dans `services/pipeline.py` :

1. **STT** (`SpeechToTextProvider`) → `TranscriptionResult(segments, gaps)`.
   Le mock reçoit un chunk dont la charge utile est `oris-synthetic:<case_id>` et
   renvoie le transcript du corpus ; un segment `[coupure audio …]` devient un
   `AudioGap`. Sans source, la consultation passe en `transcription_failed`.
2. **Extraction** (`ClinicalExtractionProvider`) → `ExtractionResult(facts, plan,
   procedures)`. Le mock retrouve le cas par empreinte du transcript et rejoue les
   faits attendus ; transcript inconnu → résultat vide.
3. **Résolveur déterministe** (`domain/resolver.py`) : preuves existantes, pas de
   fait « réalisé » au futur, pas de statut praticien porté par le patient,
   incertitude cohérente, plan et actes appuyés par des faits de même statut,
   données d'acte appuyées par des faits. Toute violation → sortie **rejetée**
   (`generation_failed`), jamais corrigée.
4. **Alertes** (`domain/warnings.py`) : trou audio → `AUDIO_GAP` critique.
5. **Assemblage** : `ClinicalEncounter` v1 validé contre le schéma.
6. **Documents** : compte rendu + plan (si items), rendus depuis l'objet seul par
   un générateur à gabarits français (`documents/renderer.py`), chaque phrase
   portant ses `fact_ids`.
7. **Validateur factuel** (`domain/factual_validator.py`) : phrase sans appui,
   fait inconnu, dent citée non portée par les faits, « Réalisé » sans fait
   réalisé, fait non restitué.

### Stockage des versions

- `encounter_object_versions` (nouvelle table, append-only) : l'objet clinique
  complet par version = **source de vérité et historique** (§57).
- Tables normalisées M0 (faits, plan, actes, liens de preuve) = projection de la
  version courante, reconstruite à chaque version, pour requêtes et intégrité.
- `document_versions` : texte, phrases avec `fact_ids`, problèmes de validation,
  version d'objet source. `document_version_facts` est supprimée : une version de
  document cite les faits d'une version d'objet donnée, pas des lignes mutables.

### Corrections (D016)

`PATCH /encounters/{id}/clinical-object` avec `expected_object_version` et des
opérations : `replace_tooth`, `update_fact`, `set_plan_item_status`, `add_fact`,
`remove_fact`. Application pure sur l'objet → résolveur → version +1 → documents
`outdated` → régénération (par défaut) → LearningEvent(s) typés dans le store
`learning`. Validation d'un document sans modification → LearningEvent
`document_validated_unchanged` (signal faible, §127).

### Validation

Explicite uniquement. Refusée si le document est périmé, a un problème critique,
ou si une alerte critique n'est pas explicitement reconnue par le praticien.

### Identité

Pas d'authentification en M1 : organisation et praticien de démonstration créés
en `local`/`test` ; l'API refuse de servir en `staging`/`production`.

### Clients

- Web : patients, nouvelle consultation synthétique, écran de révision
  (document 65 % / alertes + faits 35 %, source d'une phrase, correction de dent
  et de statut, validation).
- iOS : liste des consultations et consultation en lecture (Compte rendu | Plan,
  À vérifier), depuis la même API.

### Honnêteté des tests critiques A–J

Avec un extracteur mock, A–I vérifient que la chaîne **conserve** dent, négation,
incertitude, temporalité et statut de l'extraction jusqu'aux documents, et que
le résolveur **rejette** les sorties qui les violent (cas mutés). Ils ne prouvent
pas qu'un modèle extrait correctement depuis la parole : c'est l'objet de M5.

### Résultat M1 (2026-09-17)

Gate atteint : tests critiques A–J verts (`services/api/tests/critical`), plus le
cas « conflit d'interlocuteurs ». Les 100 cas du corpus passent le pipeline via
l'API, avec objets conformes au schéma, alertes attendues, et documents sans
problème de validation. Correction 26 → 27 vérifiée de bout en bout (objet v2,
documents périmés puis régénérés, historique, LearningEvents). Parcours vérifié
dans le navigateur : coupure audio (validation bloquée puis acceptée après
reconnaissance), source d'une phrase, correction de dent, refus d'une correction
incohérente puis acceptation d'un changement de statut du plan.

Contrôles : API ruff + mypy strict + 104 tests ; web eslint + tsc + 13 tests +
build ; iOS 14 tests ; générateurs, OpenAPI et fixtures `--check`.

Choix et corrections faits en cours de route :
- Un fournisseur ne peut pas marquer un fait `manually_validated` (règle
  `EXTRACTION_SELF_VALIDATED`) : le mock recopiait ce drapeau du corpus, ce qui
  affichait « vérifié par le praticien » à tort.
- La règle « plan appuyé par un fait de même statut » s'applique à l'extraction ;
  un changement de statut par le praticien est la décision explicite et met à jour
  les faits de traitement qui appuient l'élément (spec §34).
- `document_version_facts` supprimée (migration 0002) : une version de document cite
  les faits d'une version d'objet, conservée intégralement dans
  `encounter_object_versions`.
- Statut document : `draft_ai` sans problème détecté, `needs_review` sinon ; les deux
  exigent une validation explicite.
- Contrat API ↔ iOS : `tests/test_client_fixtures.py` fige de vraies réponses
  normalisées dans `apps/ios/OrisTests/Fixtures`, décodées par `APIContractTests`.
- iPhone vérifié par tests uniquement : l'accès au simulateur n'a pas été accordé.


---

## M2 — Web audio capture (2026-09-17)

Critères lus : ACCEPTANCE_CRITERIA (global, active consultation), spec §10–13,
§59, §65, §68–69, §71, UI_SCREEN_SPEC S03, S05, S06. Règles cliniques inchangées.

### Format audio

PCM 16 bits signé, 16 kHz, mono (`audio/pcm;rate=16000;channels=1;encoding=s16le`),
en segments indépendants de 2 s. Raisons : format accepté par les STT de parole,
chaque segment décodable seul (un segment perdu ne corrompt pas les suivants, ce
qui n'est pas le cas de WebM/Opus via MediaRecorder), et durée exacte déduite du
nombre d'échantillons, donc détection exacte des trous. Coût : ~1,9 Mo/min.

### Serveur

- Tables `audio_sessions` (une par consultation) et `audio_chunks` (métadonnées :
  séquence, horodatage, durée, taille, SHA-256, réception). Le son lui-même n'est
  jamais en base.
- `AudioSink` : `memory` (tests) et `local_temp` (dev, hors iCloud, dans
  ~/Library/Caches/Oris/audio). Purge à la fin du traitement (D010, audio éphémère) ;
  les métadonnées restent pour l'audit de couverture.
- `PUT /encounters/{id}/audio/chunks/{sequence}` : idempotent (même séquence + même
  empreinte = doublon accepté ; empreinte différente = conflit), empreinte vérifiée,
  accepté en `recording` et `paused`.
- `POST /encounters/{id}/audio/gaps` : interruption signalée par le client (micro
  débranché, page rechargée pendant l'écoute).
- `GET /encounters/{id}/audio` : couverture (séquences manquantes, trous, durée),
  utilisée aussi pour reprendre après rechargement.
- `domain/audio_coverage.py` (pur) : séquences manquantes, discontinuités
  d'horodatage (> 50 ms), trous signalés → `AudioGap`.
- `finish` : refuse (409 `AUDIO_CHUNKS_MISSING` + liste) s'il manque des segments,
  sauf `accept_gaps=true` (perte irrécupérable assumée) → alerte `AUDIO_GAP`.
- Pipeline : les trous de capture s'ajoutent aux trous du STT ; purge audio ensuite.
- Information patient : `PATIENT_INFORMATION_MODE` = `confirm` (défaut) | `none`.
  En `confirm`, `start` exige `patient_informed=true` (tracé dans l'audit). Aucune
  interprétation juridique figée : c'est un paramètre (§65).
- `GET /config/client` : format audio, durée maximale (90 min, alerte à 80),
  mode d'information patient, sources de test autorisées.
- Pas de WebSocket en M2 : envoi HTTP ordonné avec reprise, suffisant sans
  transcription en direct (prévu avec le STT streaming, M4).

### Web

`src/lib/audio/` en TypeScript pur, testé sans navigateur :
- `pcm.ts` (rééchantillonnage 16 kHz, Int16), `chunker.ts` (segments 2 s horodatés
  à l'échantillon près), `checksum.ts` (SHA-256), `uploader.ts` (file ordonnée
  segments + événements pause/reprise/trou, une requête à la fois, nouvelle
  tentative avec attente croissante, suppression locale seulement après accusé de
  réception), `sources.ts` (micro via AudioWorklet ; source de test sans micro en
  local), `controller.ts` (états : prêt, autorisation, écoute, pause, reconnexion,
  erreur micro, envoi final, traitement).
- Écran `/consultations/{id}/ecoute` : pré-écran (patient, micro, réseau,
  information patient, « Commencer l'écoute ») puis écoute (chronomètre, niveau
  sonore, état micro, état réseau, Pause/Reprendre, Terminer).
- Révision : résumé audio (durée reçue, trous, purge) et explication claire tant
  que la transcription n'est pas branchée.

### Honnêteté

Sans STT (M4), une consultation au micro aboutit à `transcription_failed`
(`NO_TRANSCRIPT`) : l'audio est reçu, contrôlé puis purgé. Les tests de fusion
des trous dans l'objet clinique utilisent un STT de test.

### Résultat M2 (2026-09-17)

Vérifié dans le navigateur (son de test) : refus du micro expliqué sans démarrer la
consultation, écoute avec envoi continu (PUT 201), pause, rechargement de page
pendant la pause puis reprise au bon numéro de segment et au bon temps, fin
d'écoute → « Transcription impossible » expliquée, 57 s reçues sans interruption,
dossier audio vide sur le disque après purge.

Contrôles : API 126 tests ; web 33 tests + lint + typecheck + build ; iOS 14 tests.

Corrigé en cours de route : le choix de source (micro / test) était figé à la
première tentative ; il est désormais lu à l'ouverture de la source.


---

## M3 — iOS audio capture (2026-09-17)

Critères lus : ACCEPTANCE_CRITERIA (active consultation), spec §5.1, §13.2, §65,
§69–71, UI_SCREEN_SPEC S01, S03, S04, BACKLOG E06. Même contrat audio qu'en M2
(PCM 16 kHz mono, segments de 2 s, même API) : aucun changement de règle clinique.

### Architecture iOS (`apps/ios/Oris/Audio`)

- `PCM.swift`, `Chunker.swift` : mêmes calculs que le web (rééchantillonnage par
  moyenne, horodatage à l'échantillon).
- `ChunkStore.swift` : tampon local **chiffré** (AES-GCM, CryptoKit) des segments non
  confirmés, un fichier par segment, protection de données iOS en plus. Clé dans le
  trousseau (`AfterFirstUnlockThisDeviceOnly`, pour écrire écran verrouillé) : les
  segments survivent à une fermeture de l'app et sont renvoyés à la réouverture.
  Suppression dès l'accusé de réception du serveur.
- `Uploader.swift` (actor) : file ordonnée segments + événements (pause, reprise,
  trou), un envoi à la fois, nouvelles tentatives croissantes, réveil immédiat au
  retour du réseau (`NWPathMonitor`).
- `AudioTransport.swift` : même traduction des réponses que le web.
- `AudioInput.swift` : `AVAudioSession` (`.record`, mode `.spokenAudio`,
  AirPods/Bluetooth autorisés) + `AVAudioEngine` ; interruptions (appel, Siri),
  changement de route (AirPods retirés), réinitialisation des services média.
  `TestToneInput` pour le simulateur sans micro (DEBUG, local).
- `CaptureController.swift` (@MainActor @Observable) : états prêt, écoute, pause,
  interrompu (appel), micro perdu, envoi final, terminé, erreur.

### Règles propres à l'iPhone

- Appel / Siri : écoute suspendue, **pas de reprise automatique** ; le praticien
  reprend explicitement ; la durée d'interruption devient un trou signalé
  (`audio_interruption`) → alerte critique.
- AirPods retirés / nouvelle entrée : redémarrage de la capture sur la nouvelle
  entrée ; si plus d'1 s sans son, trou signalé (`route_change`).
- Écran verrouillé / arrière-plan : la capture continue (mode audio en arrière-plan)
  et l'état reste affiché (indicateur micro iOS).
- App tuée pendant l'écoute : à la réouverture, segments chiffrés renvoyés, trou
  `app_terminated` signalé, reprise ou fin proposées.
- Micro refusé : explication et bouton vers Réglages.

### Serveur

Motifs de trou ajoutés : `audio_interruption`, `route_change`, `app_terminated`
(un trou reste un trou : même alerte critique).

### Écrans

Accueil : « Nouvelle consultation » actif → choix du patient (ou création) →
pré-écran (S03) → écoute plein écran (S04) → consultation. Liste des consultations :
une écoute en cours ouvre l'écran d'écoute.

### Résultat M3 (2026-09-17)

Contrôles : iOS 39 tests (Swift 6, avertissements = erreurs), dont appel sans reprise
automatique, changement d'écouteurs court et long, micro perdu, coupure réseau,
« Terminer malgré tout », durée maximale, reprise après fermeture ; tampon chiffré
(aller-retour, jamais en clair, autre clé refusée) ; API 129 tests ; web 33 tests.

Choix en cours de route :
- Le bloc de capture audio est créé hors de tout acteur et passe les échantillons par
  un `AsyncStream` : appelé sur le fil temps réel, il ne doit pas hériter de
  l'isolation du fil principal (plantage d'isolation Swift 6).
- `UIBackgroundModes` dans `Config/Oris-Info.plist`, fusionné avec l'Info.plist généré.
- Tests temporels : attente d'état plutôt que délai fixe (52 s d'audio = 26 segments
  chiffrés à écrire).
- Écoute non vérifiée à l'écran : accès au simulateur toujours non accordé.


---

## M4 — STT benchmark adapter (2026-09-17)

Critères lus : docs/TECHNICAL_BENCHMARK.md, AI_ARCHITECTURE §1–2, spec §14–16,
§26, §66, BACKLOG E07. Aucun fournisseur choisi par défaut (D020).

### Candidats

Azure AI Speech et Deepgram Nova-3, la paire recommandée par la note technique
(« Azure Speech + one of Deepgram/Speechmatics ») : Azure = référence conformité
(périmètre HDS à vérifier), Deepgram = latence et mots-clés. Speechmatics et OpenAI
restent candidats ; l'interface permet de les ajouter sans toucher au domaine.

### Adaptateurs (`oris_api/stt/`), données fournisseur jamais dans le domaine

- Finalisation (fichier entier) : Azure *fast transcription*
  (`/speechtotext/transcriptions:transcribe`, `api-version=2025-10-15`, diarisation,
  `phraseList`) ; Deepgram `POST /v1/listen` (`nova-3`, `language=fr`, `diarize`,
  `utterances`, `keyterm` répété).
- Temps réel : Deepgram WebSocket (`interim_results`, `Finalize`, `CloseStream`,
  reconnexion avec trou signalé) ; Azure SDK `ConversationTranscriber` + flux poussé
  (extra optionnel `stt`).
- Sortie commune : `TranscriptionResult` (segments, trous, étiquettes de locuteur,
  identifiant de requête). Rôles : `domain/speaker_roles.py` (densité de vocabulaire
  dentaire ; en dessous du seuil de confiance → `unknown`, jamais deviné).
- Glossaire dentaire (`ontology/stt_glossary.py`) : ≤ 50 termes (limite Deepgram).
- Garde-fou : un STT externe exige `ALLOW_EXTERNAL_STT=true` et ses clés (fichier
  `.env` local, jamais dans le dépôt ni dans le chat). Par défaut : `mock`.
- Pipeline : erreur temporaire du fournisseur → `transcription_failed`
  (`STT_UNAVAILABLE`), audio **conservé** pour relance ; purge après transcription
  réussie ou absence de parole (correction de la limite M2).

### Banc d'essai (`oris_api/benchmark/`, `scripts/stt_benchmark.py`)

- Jeu synthétique : les 100 transcripts du corpus lus par les voix françaises de
  macOS (praticien Thomas, patient Aurélie, assistant(e) Jacques, accompagnant Flo),
  segments horodatés → vérité exacte des mots, dents, négations et locuteurs. Audio
  régénérable, hors dépôt. **Non décisionnel** : voix de synthèse ≠ cabinet réel.
- Le banc refuse tout jeu non marqué `synthetic_only` ou `consent_documented`.
- Métriques (TECHNICAL_BENCHMARK) : WER dentaire (nombres normalisés), exactitude
  des numéros de dent, rappel matériaux/marques, conservation des négations,
  attribution des locuteurs (meilleure correspondance), latence finale et
  intermédiaire p50/p95, reconnexion, gain du glossaire, coût pour 30 min (tarifs à
  renseigner depuis le contrat, jamais inventés), score pondéré ; conformité = gate.
- Sortie : `EvaluationRun` (schéma existant) + rapport Markdown en français.

### Résultat M4 (2026-09-17)

Fait : adaptateurs Azure (fichier + temps réel) et Deepgram (fichier + temps réel),
garde-fou d'envoi externe, conservation de l'audio en cas de panne, banc d'essai
complet, jeu synthétique de 100 enregistrements (35 min, voix macOS), rapport français.

Vérifié hors ligne : `stt_benchmark.py check` sur les 100 enregistrements avec le
fournisseur « référence » → 100 % (243 numéros de dent, 212 négations, 268 termes
examinés). Aucun fournisseur réel appelé : clés absentes.

Contrôles : API 174 tests (dont faux serveur WebSocket coupant la connexion) ; web 33 ;
iOS 39 (inchangé).

Trouvé et corrigé grâce au contrôle hors ligne :
- l'attribution des rôles par densité de vocabulaire ne trouvait le bon rôle que
  34 % du temps **et se trompait avec assurance dans 10 consultations** (patient pris
  pour le praticien, en comptant « je » et « on »). Remplacée par des tournures propres
  à chaque rôle, avec abstention en cas de doute : 97,9 % justes, 0 faux, plus des
  tests de phrases pièges écrites hors corpus ;
- une clé vide dans `.env` était prise pour une clé présente ; les tests lisaient le
  `.env` privé du poste (désormais isolés, STT factice forcé).
- `say` (macOS) se bloque parfois : délai maximal et nouvel essai par phrase.


---

## M5 — Clinical extraction (2026-09-18)

Critères lus : ACCEPTANCE_CRITERIA (clinical extraction), spec §18–25, §27, §29–31,
§101–102, TECHNICAL_BENCHMARK (extraction). Les garde-fous existants (résolveur,
validateur factuel, rédaction par gabarits) ne changent pas : c'est l'extraction
factice qui est remplacée par un vrai modèle.

### Adaptateur (`oris_api/llm/anthropic_extraction.py`)

- API Messages d'Anthropic (HTTP direct, comme les adaptateurs STT), sortie forcée
  par un outil dont le schéma est **dérivé des JSON Schemas d'Oris** (un seul
  schéma, références résolues) : pas de champ libre, pas de second vocabulaire.
- Prompt système : §27 (n'inventer aucune donnée absente, préserver négation,
  temporalité, incertitude, rôle du locuteur, et la distinction proposé / accepté /
  refusé / prévu / réalisé ; dans le doute, marquer incertain ou omettre).
- Le modèle ne décide pas de la provenance : `source_type=audio` et
  `manually_validated=false` sont posés par l'adaptateur, jamais par le modèle.
- Concepts : liste du vocabulaire connu (`ontology/labels.py`) fournie au modèle ;
  un concept hors liste reste possible mais le document le signalera « à rédiger ».
- Sortie invalide → **jusqu'à trois essais expliqués** (l'erreur exacte est renvoyée au
  modèle), puis rejet (jamais de correction silencieuse). Mesuré le 18/09 : sur les six
  consultations en échec du premier banc, deux n'aboutissaient qu'au troisième essai —
  la limite à deux essais rejetait une sortie que le modèle savait corriger.
- Panne réseau, quota (429) ou erreur serveur (5xx) → **le même appel est repassé** deux
  fois (attente 1 s puis 4 s) avant d'abandonner : une coupure n'est pas un défaut de la
  sortie et ne doit pas coûter la consultation.
- L'échec porte sa raison : `ExtractionUnavailable(code, details)`, et
  `rule_codes()` n'en extrait que les noms de règles (aucun contenu clinique). Le
  pipeline attrape désormais cette erreur — auparavant elle remontait en 500 — et
  classe la consultation en `generation_failed` avec ces règles en `processing_errors`.
- Jetons consommés remontés pour mesurer le coût réel.

### Configuration

`CLINICAL_EXTRACTION_PROVIDER=mock|anthropic`, `ANTHROPIC_API_KEY`,
`ANTHROPIC_MODEL` (défaut `claude-sonnet-5`), `ALLOW_EXTERNAL_LLM=true` requis :
même garde-fou explicite que pour la transcription.

### Banc d'essai extraction (`benchmark/extraction.py`)

Sur les 100 consultations du corpus (transcripts, sans audio) contre les faits
attendus : précision et rappel des faits, exactitude des négations, de la
temporalité et du statut prévu/réalisé, taux d'énoncés non appuyés, validité du
schéma au premier essai, taux de rejet par le résolveur, latence, coût réel.
Comparaison entre modèles (Sonnet, Haiku, Opus) : aucun n'est choisi d'office.

## M6 — sortie des documents : PDF, texte, copie pour le dossier (2026-09-19)

Critères visés (`ACCEPTANCE_CRITERIA`, spec §78–79, §50) : export PDF et texte,
« Copier pour le dossier », statut `exported`, aucune validation implicite.

Modules touchés :
- `documents/export.py` (nouveau) : mise en page PDF A4 (reportlab) et rendu texte,
  simple ou structuré ;
- `services/documents.py` : `export_document` — audit, passage du document à
  `exported`, consultation à `exported` quand tous ses documents le sont ;
- `api/encounters.py` : `GET /documents/{id}/export?format=pdf|text|structured` ;
- `apps/web` : boutons « Exporter en PDF » et « Copier pour le dossier ».

Décisions :
- un brouillon **peut** être exporté, mais le PDF le dit en toutes lettres
  (« brouillon, non validé ») et son statut ne change pas : seul un document validé
  devient `exported` ;
- le nom du fichier ne porte pas le nom du patient (il apparaît dans le document,
  pas dans un nom de fichier qui traîne dans un dossier de téléchargements) ;
- reportlab : dépendance ajoutée plutôt qu'un générateur PDF maison — un PDF mal
  formé qu'un lecteur refuse n'est pas acceptable pour un document médical.

Résultat : PDF A4 vérifié à l'écran (en-tête d'identification, sections en gras,
pagination, mention de validation), texte structuré collable dans le logiciel métier.
Le presse-papiers du navigateur peut refuser la copie (permission, navigateur) : dans ce
cas le texte s'affiche dans une zone sélectionnable plutôt que de disparaître — observé
en vrai dans le navigateur intégré, pas seulement supposé.

Les intitulés de section ne sont pas devinés à la mise en page : la liste vient du
rédacteur (`SECTION_ORDER`), sinon une phrase en majuscules deviendrait un titre.

## Cadre des séances jouées (2026-09-20)

Ce que le jalon M11 laissait en suspens : de quoi organiser les enregistrements sans que
je sois là. Trois documents pour le praticien (note d'information, consentement,
protocole) et un outil qui refuse ce qui n'est pas en règle.

Le protocole est écrit pour mesurer ce qui compte, pas pour produire du beau son : garder
le bruit du cabinet, ne pas répéter les numéros de dents, ne pas recommencer une phrase
hésitante. La sixième consultation, dite « piège », contient exprès les six situations où
Oris peut se tromper gravement (correction de dent, négation, incertitude, parole du
patient non reprise, acte futur, refus).

`prepare_recordings.py` convertit (afconvert sur macOS, ffmpeg sinon), lit les
transcriptions « rôle | texte » — un rôle inconnu est refusé, pas deviné — et écrit un
manifeste que `check_dataset.py` accepte. Sans référence de consentement, il n'écrit
rien : la règle est la même à l'entrée, au contrôle et à la porte d'entrée en bêta.

## M11 — mise en situation clinique (2026-09-20)

Critères visés (`IMPLEMENTATION_PLAN` M11) : environnement cible compatible HDS, flux de
données fournisseurs revus, séances synthétiques **et** jouées par des professionnels,
cadre de mode ombre, porte d'entrée en bêta. Ce qui relève du contrat et de
l'hébergement n'est pas du code : ce jalon fournit ce qui rend la décision **vérifiable**,
pas la décision elle-même.

Modules :
- `services/encounters.py` : **mode ombre** — Oris écrit, personne ne s'en sert ; un
  document d'ombre ne peut être ni validé ni exporté ;
- `docs/VENDORS.md` + `benchmarks/providers.json` : inventaire des flux (finalité, données
  envoyées, région, conservation, usage pour l'entraînement, sous-traitants, DPA) ;
- `scripts/beta_gate.py` : la règle de sortie devient exécutable — elle refuse tant qu'un
  fournisseur n'est pas revu, qu'un jeu de données n'a pas de consentement documenté ou
  que les tests critiques ne passent pas ;
- `benchmarks/datasets/` : format des séances jouées par des praticiens, avec
  consentement, et validateur.

### Résultat M11

**Mode ombre.** Une consultation créée avec `shadow: true` est traitée comme les autres —
c'est l'intérêt : mesurer Oris en conditions réelles. Mais ses documents sont refusés à
la validation **et** à l'export (`SHADOW_ENCOUNTER`), le mode est écrit dans le journal
d'audit, et l'écran le dit en toutes lettres. La règle est appliquée côté serveur, pas
seulement masquée dans l'interface.

**Porte d'entrée en bêta.** `scripts/beta_gate.py` remplace une case à cocher par une
vérification. Aujourd'hui elle **refuse**, et elle dit pourquoi : aucun jeu de données
joué par des praticiens, trois fournisseurs non revus, 21 cases « à documenter » dans
`docs/VENDORS.md`, hébergement agréé absent. Un point qui dépend d'un contrat est déclaré
comme tel : il ne se coche pas en écrivant du code.

**Séances jouées.** `scripts/check_dataset.py` contrôle un jeu d'enregistrements avant
usage : format 16 kHz mono 16 bits, consentement documenté **et** référencé, rôles
présents dans la transcription de référence. Un jeu non synthétique sans consentement est
refusé par le contrôle comme par la porte d'entrée.

**Défaut d'interface corrigé au passage** : un attribut `hidden` ne pesait rien face à un
`display` posé par une classe ou en ligne — deux boutons restaient visibles en mode ombre.
Règle CSS globale ajoutée (`[hidden] { display: none !important }`).

## M10 — sécurisation (2026-09-20)

Critères visés (`IMPLEMENTATION_PLAN` M10, `docs/SECURITY.md`) : journal d'audit,
observabilité sans PHI, authentification, purge de l'audio observable et rejouable,
récupération après panne. Ce qui relève de l'hébergement (HDS, sauvegardes chiffrées,
MFA d'un fournisseur d'identité) n'est pas du code et reste hors de ce jalon : il est
listé comme tel, pas coché en douce.

Modules :
- `db/models.py` + migration `0005` : `api_tokens` (jeton d'accès par praticien,
  empreinte seule, jamais le secret) ;
- `services/authentication.py` (nouveau) : émission, vérification, révocation ;
- `api/dependencies.py` : hors `local`/`test`, aucune route métier sans jeton valide ;
- `scripts/issue_token.py` : créer un jeton, affiché une seule fois ;
- `services/audio.py` : purge rejouable des sessions restées avec du son ;
- `api/audit.py` : lecture du journal (identifiants et actions, jamais de contenu).

### Résultat M10

**Authentification.** `Authorization: Bearer oris_…`. La base ne contient qu'une
empreinte scrypt salée : un vol de base ne rend aucun jeton utilisable. La comparaison
est en temps constant, et un jeton sans le préfixe est refusé avant toute lecture de
base. `scripts/issue_token.py` crée, liste et révoque ; le secret n'est affiché qu'une
fois. En `local`/`test`, l'identité de démonstration reste acceptée **tant qu'aucun
jeton n'est présenté** — ailleurs, il n'existe aucun mode ouvert, c'est testé.

Ce n'est pas du MFA : le second facteur viendra d'un fournisseur d'identité au moment de
l'hébergement agréé. Écrit tel quel dans `docs/SECURITY.md` et dans les limites connues.

**Journal d'audit.** Défaut trouvé au passage : les actions du système (génération d'un
document, purge du son) étaient enregistrées sans organisation, donc **invisibles** dans
le journal du praticien. Corrigé : `audit.record` accepte l'organisation pour les actions
sans acteur. Le test vérifie que le journal contient bien ces actions, et qu'aucun mot
clinique n'apparaît dans les détails.

**Purge du son.** `purge_pending` repasse sur les consultations déjà traitées : une
session déjà purgée est ignorée, une panne de stockage n'interrompt pas la passe et
ressort dans le rapport (`purged`, `failed`, `remaining`). Rejouable sans risque.

## M9 — personnalisation (2026-09-20)

Critères visés (`IMPLEMENTATION_PLAN` M9, spec §53–54, §120, §123, §124, §176–178) :
dictionnaire du praticien, terminologie préférée, préférences rédactionnelles, suggestion
à partir des corrections répétées, et **tout doit être réversible**. Invariants
d'apprentissage : la personnalisation améliore la reconnaissance et le style, elle
n'insère **jamais** un fait clinique ; rien ne devient global tout seul.

Modules :
- `db/models.py` + migration `0004` : `learning.glossary_terms` (dictionnaire personnel,
  hors dossier patient) ;
- `domain/preferences.py` (nouveau) : préférences validées (longueur, style, terminologie) ;
- `services/personalization.py` (nouveau) : dictionnaire, préférences, suggestions issues
  des corrections répétées ;
- `services/encounters.py` : le dictionnaire du praticien est transmis à la transcription
  **et** à l'extraction (il ne l'était pas) ;
- `documents/renderer.py` : terminologie et concision appliquées à la rédaction, sans
  jamais retirer un fait ;
- `apps/web` : écran « Oris apprend de vous ».

### Résultat M9

Le dictionnaire du praticien part maintenant **avec** l'audio (mots soufflés à Deepgram)
et **avec** le transcript (mots soufflés à Claude). Il ne l'était nulle part : la
plomberie existait depuis M4, elle recevait une liste vide.

Préférences appliquées au compte rendu de consultation : `terminology` remplace le mot
d'Oris par celui du praticien (« avulsion » plutôt que « extraction ») ; `concise` retire
les préfixes qui ne font que répéter le titre de la section (« Rapporté par le patient : »
sous « Symptômes rapportés »). Une nuance — absence, incertitude, antécédent — n'est
jamais retirée : c'est du fond, pas de la forme. Le plan et le compte rendu de soins
gardent leur formulation (leurs mots viennent du modèle et des modèles d'actes, pas de
l'ontologie).

Suggestions (§123) : Oris **propose** après deux corrections allant dans le même sens, et
ne décide jamais. Deux sources aujourd'hui — une préférence de rédaction demandée deux
fois, et un nom de produit corrigé deux fois (`material_name_correction`, nouveau).

Réversibilité (§177) : un terme se désactive sans être effacé (il cesse d'être soufflé
aux fournisseurs), une préférence revient au défaut, un mot préféré se retire. L'écran
« Oris apprend de vous » montre les trois et permet de les défaire.

## M8 — correction dictée (2026-09-20)

Critères visés (spec §46–48, `IMPLEMENTATION_PLAN` M8) : interpréter la commande,
produire un **patch structuré**, confirmer si l'impact est significatif, appliquer à
l'objet clinique, invalider et régénérer les documents, garder l'historique, émettre un
`LearningEvent`. Le moteur distingue une correction clinique d'une préférence de
rédaction (§46 A/B).

Modules :
- `domain/correction_intent.py` (nouveau) : interprétation déterministe d'une phrase en
  français → opérations existantes (`replace_tooth`, `set_plan_item_status`,
  `update_fact`, `remove_fact`). Ce qui n'est pas clair n'est **pas** deviné : la
  commande est rendue avec la raison et, si besoin, les cibles possibles ;
- `api/encounters.py` : `POST /encounters/{id}/corrections/text` — aperçu par défaut,
  application sur confirmation ;
- `apps/web` : dicter ou écrire une correction, voir le patch avant d'appliquer.

### Résultat M8

Le pipeline de la spec §47 est en place : interpréter → patch → confirmer → appliquer →
invalider → régénérer → historiser. L'aperçu est le comportement **par défaut** de la
route : appliquer demande un `apply` explicite **et** la version d'objet attendue, sinon
`OBJECT_VERSION_REQUIRED`. Une correction sur une version périmée est refusée.

Ce que l'interprète sait faire, en français : remplacer une dent (quatre tournures),
ajouter une dent à un élément, retirer un élément nommé, changer le statut d'un
traitement (accepté, refusé, reporté, prévu, réalisé, proposé). Ce qu'il **refuse** de
faire : deviner. Une cible ambiguë revient avec la liste des éléments possibles, écrits
en français ; une phrase non reconnue revient avec des exemples.

Une préférence de rédaction (« plus court », « reformule ») est reconnue comme telle :
elle n'est jamais appliquée au dossier clinique, seulement retenue comme
`style_preference_detected` (§46 B).

La dictée passe par `POST /corrections/voice` : l'audio est transcrit **dans la requête**
par le fournisseur configuré, puis oublié — il n'entre pas dans le stockage audio de la
consultation (D010). Vérifié par un test ; un vrai micro reste à essayer par le praticien.

## M7 — comptes rendus opératoires (2026-09-19)

Critères visés (`ACCEPTANCE_CRITERIA`, spec §37–45, §77, §81) : les champs d'un modèle
sont des **emplacements de preuve facultatifs**, jamais des valeurs par défaut ; le
matériau habituel du praticien n'est jamais inscrit comme réalisé ; un champ important
manquant peut alerter mais jamais être rempli ; le compte rendu opératoire n'est produit
que si le praticien le demande (§81).

Modules :
- `documents/operative_templates.py` (nouveau) : les sept modèles de la spec (composite,
  esthétique direct, facettes préparation, facettes collage, usures additives, avulsion,
  chirurgie mineure générique), chacun une suite d'emplacements ordonnés (clé, libellé,
  section, champ important ou non) ;
- `documents/renderer.py` : `render_operative_note` — une phrase par emplacement
  **renseigné**, appuyée sur les faits de l'acte ;
- `domain/factual_validator.py` : `operative_field_missing` (à vérifier, jamais rempli) ;
- `services/documents.py` + `api/encounters.py` : génération à la demande ;
- `apps/web` : proposition « un acte a été détecté » et onglet du compte rendu de soins.

### Résultat M7

Un emplacement se renseigne de deux façons, et jamais d'une troisième :
1. l'acte l'a dicté (`structured_data`) ;
2. une **information dite pendant l'intervention et déjà retenue comme fait** le
   renseigne (table `FACT_SOURCES`, un fait par emplacement, mêmes dents, même statut) —
   la phrase cite alors ce fait, pas l'acte en bloc.
Rien d'autre. Le matériau habituel du praticien reste absent tant qu'il n'a pas été dit.

Un emplacement prévu « oui/non » qui arrive précisé (« provisoires posés le jour même »)
garde la précision : elle a été dite, on ne la jette pas.

L'invite d'extraction connaît maintenant les emplacements de chaque modèle
(`champs_par_acte`, version `extraction-fr-5`). Avant, le modèle rangeait l'adhésif dans
un fait et laissait l'emplacement vide : le compte rendu alertait « champ important non
dicté » alors que l'information avait bien été prononcée.

Vérifié de bout en bout sur quatre types d'acte du corpus (composite, préparation de
facettes, collage, avulsion), transcription et extraction réelles : notes complètes,
aucune alerte injustifiée, PDF « compte rendu de soins » relu à l'écran.

## Habillage des documents : un modèle par type (2026-09-19)

Spec §78 (logo, identité, pagination) et demande du praticien : un courrier à un confrère
ne se présente pas comme un résumé remis au patient.

- `documents/theme.py` : identité du cabinet lue dans `services/api/config/cabinet.json`
  (nom, adresse, téléphone, courriel, mention légale, logo). Tout est facultatif ; un
  champ vide ne laisse pas de ligne vide, il disparaît. Sans fichier, l'en-tête reste
  sobre et le document sort quand même — c'est testé.
- Couleurs prises dans `docs/DESIGN_SYSTEM.md` (bleu profond pour les titres, gris pour
  les mentions), pas inventées à la volée.
- `LAYOUTS` dans `documents/export.py` : un modèle par type de document.
  - compte rendu de consultation et plan de traitement : document clinique sobre ;
  - **compte rendu de soins** : même ossature, titre distinct ;
  - **courrier d'adressage** : formule d'appel (« Chère Consœur, Cher Confrère, »),
    formule de politesse et signature du praticien ;
  - **résumé patient** : corps plus grand (12 pt), interligne aéré, phrase d'introduction
    et mention de remise en pied de page.
- Logo : `assets/oris-logo.png`, recadré sur l'encre depuis le logo de marque. Le logo du
  cabinet de Franck le remplacera par simple changement de chemin.
- Pages suivantes : rappel discret « type — patient » en haut, pagination en bas.

Les quatre modèles ont été rendus en image et regardés, pas seulement testés.

## M6 (2/2) — cartes de plan et corrections lisibles (2026-09-19)

Le plan de traitement n'existait que comme paragraphe, et le statut se changeait dans un
panneau séparé, loin de ce qu'on lit. Chaque élément du plan est désormais une carte :
dents, intitulé, statut, motif, faits d'appui cliquables (provenance), alternatives,
préalables, incertitudes — et le statut se change **sur la carte**. La numérotation
n'apparaît que si la séquence a été énoncée (§33.3).

`lib/useCorrection.ts` : la logique de correction (version attendue, régénération,
message) était dupliquée dès qu'un deuxième écran corrigeait. Un seul endroit
maintenant ; `CorrectionPanel` garde la correction de dent et renvoie vers la carte.

Historique : un événement d'apprentissage affichait son intitulé seul (« Statut de
traitement corrigé »). Il affiche ce qui a changé (« proposé → accepté ») en lisant
`before`/`after`, sans nouveau champ côté serveur.

Vérifié dans le navigateur : changement de statut depuis la carte → dossier clinique v2,
documents régénérés, texte du plan à jour, historique « proposé → accepté ».

## Vocabulaire clinique (2026-09-19)

**Deuxième passe, dictée du praticien** : 42 termes de plus (269 au total, 16 thèmes).
Deux listes distinctes, souvent confondues :

- le **vocabulaire de rédaction** (`ontology/labels.py`) : ce qu'Oris sait écrire.
  Aucune limite de taille ; son coût est quelques centaines de jetons dans l'invite.
- le **glossaire de transcription** (`ontology/stt_glossary.py`) : ce qu'on pousse au
  fournisseur STT pour qu'il *entende* juste. Plafonné à 50 termes (au-delà, Deepgram
  dégrade). Les noms propres y passent en priorité — ce sont eux que la machine rate.

Choix faits sur des termes ambigus, à confirmer par le praticien : « gouttière » a été
rattachée à l'éclaircissement (la gouttière occlusale existait déjà), « contrôle » à la
séance de contrôle après traitement (le contrôle périodique existait), « système » au
système de collage, « classe 2 / 3 » à la classe d'Angle (la classe squelettique est un
terme séparé), « reprise » à la reprise d'un travail existant.

50 concepts couvraient le corpus synthétique et rien d'autre : sur une vraie
consultation, « couronnes » sortait en « à rédiger : élément non reconnu ». L'ontologie
passe à 227 termes, rangés par thème (`THEMES` dans `ontology/labels.py`, `CONCEPTS`
restant la vue à plat lue par le rédacteur et par l'invite du modèle).

Le classement n'est pas cosmétique : c'est la seule façon pour le praticien de relire et
de compléter la liste. `scripts/vocabulaire.py` produit `docs/VOCABULAIRE.md` depuis le
code, avec un tableau « à ajouter » par thème ; un test compare les deux et échoue si la
liste dérive. Les ajouts manuscrits du praticien y sont ignorés (ils vivent dans les
tableaux « à ajouter »).

Effet sur la consultation de démonstration : plus aucun « à rédiger », deux documents à
zéro problème de validation, et les options s'écrivent en français (« Option écartée :
couronnes », « surveillance sans traitement » au lieu du code brut).

Limite assumée : un libellé n'est pas un savoir clinique. Élargir le vocabulaire élargit
ce qu'Oris sait **rédiger**, jamais ce qu'il sait **déduire** ; un terme absent reste
signalé plutôt que deviné.

## M5ter — la chaîne complète branchée (2026-09-19)

Jusqu'ici les deux moteurs réels fonctionnaient chacun de leur côté (bancs d'essai) ;
une consultation enregistrée au micro n'allait chez aucun des deux. Le pipeline est
resté inchangé : ce sont les fournisseurs qui changent (`STT_PROVIDER=deepgram`,
`CLINICAL_EXTRACTION_PROVIDER=anthropic`).

### Consultation fictive et vraie consultation ne suivent plus le même fournisseur

`ProviderSet` porte désormais un `synthetic_speech_to_text` (toujours factice). Une
consultation fictive n'a pas de son : son « enregistrement » est l'étiquette
`oris-synthetic:<case_id>`, que seul le fournisseur factice sait lire. L'envoyer à
Deepgram produisait une transcription vide et un échec incompréhensible.

### Alerte quand les voix ne sont pas séparées

Mesuré sur l'audio de synthèse (30 enregistrements, 19/09) : **72 % reviennent d'une
seule voix**. L'ancienne règle donnait alors le même rôle à toute la consultation — la
phrase du patient devenait une parole du praticien, avec assurance. Désormais, une voix
unique n'est plus traitée comme « une seule personne » : chaque passage est jugé sur ses
propres mots et reste `unknown` s'il n'a rien de décisif. Ce n'est pas une garantie : nouvelle
alerte `SPEAKER_ROLES_UNKNOWN` (severité `review`, non bloquante) dès qu'un segment
parlé reste sans rôle — invariant 5.

Conséquence sur le banc d'essai : `speaker_accuracy` récompensait un fournisseur qui met
tout le monde dans la même voix (il suffit que le praticien parle le plus). Le rapport
publie maintenant aussi `single_voice_rate`, la part d'enregistrements rendus d'une seule
voix alors que la référence en compte plusieurs.

### Vérification de bout en bout

Un vrai fichier audio découpé en segments PCM de 2 s et poussé par l'API exactement
comme le fait le micro du site : Deepgram transcrit, l'audio est purgé, Claude extrait,
le compte rendu est rendu — 5 s au total, zéro problème de validation, négation
conservée (« absence de douleur nocturne »).

### Reprise des pannes passagères côté transcription

Le banc du 19/09 a perdu 5 requêtes sur 30 (4 coupures réseau, un 408) : l'audio était
bon, seule la requête avait échoué, et la consultation entière était perdue. Deepgram
reprend maintenant deux fois (1 s puis 4 s) sur `NETWORK`, 429, 5xx et 408, comme
l'adaptateur Claude.

### Imports différés dans la fabrique de fournisseurs

`providers.factory` importait les adaptateurs STT au chargement du module, qui
importaient en retour `providers.base` : importer `oris_api.stt.deepgram` en premier
cassait. Même correction que pour l'adaptateur Claude : import dans la fonction.

## « Votre journée » branché sur Dental Lens (21 septembre 2026)

L'écran affichait « chantier à venir ». Il affiche maintenant l'agenda réel du jour,
sans qu'Oris ait à parler à Doctolib : **Dental Lens**, l'autre outil du cabinet, lit
déjà l'agenda dans le navigateur et dépose la journée sur le poste. Oris vient la
chercher, c'est tout.

### Ce qui a été construit

- `services/agenda.py` — lecteur à deux chemins : d'abord le serveur Dental Lens
  (`http://127.0.0.1:8765/api/journee`), qui rapproche en prime chaque patient de son
  dossier SmileCloud ; sinon le fichier du jour
  (`~/Library/Application Support/SmileCloudPhotos/journees/AAAA-MM-JJ.json`), lisible
  serveur éteint. Une journée absente est **dite absente**, jamais devinée.
- `api/journee.py` — `GET /journee?jour=` ; pour chaque rendez-vous, l'identifiant du
  dossier Oris s'il existe déjà. Rapprochement insensible à la casse et aux accents :
  Doctolib écrit « MOREAU Chloé », Oris « Moreau Chloe ».
- `agenda_provider` (`none` par défaut), `dental_lens_url`, `dental_lens_registre` dans
  la configuration : un connecteur d'agenda est de la configuration, pas du domaine.
- Écran `/journee` : une ligne par rendez-vous, heure, patient, motif, voyant
  SmileCloud, et deux gestes — ouvrir le dossier, ou commencer l'écoute.

### Ce qui n'a **pas** été fait, exprès

Lire l'agenda n'écrit rien. Aucun dossier patient n'est créé automatiquement : il faut
cliquer. Ces noms-là sont de vrais patients, et rien ne doit entrer dans Oris tant que
l'hébergement de santé n'est pas en place — l'écran le dit en toutes lettres.

### Deux défauts trouvés à la vérification

- `new Date().toISOString()` donnait la veille après minuit : le jour est maintenant lu
  sur l'heure locale.
- `useApi` gardait les données de la ressource précédente pendant le chargement de la
  suivante : les rendez-vous de la veille s'affichaient une seconde sous la date du
  lendemain. Le résultat retient désormais de quelle ressource il vient.

## L'écran reprend la mise en page de Dental Lens (21 septembre 2026)

Demande de Franck : la même mise en page que « Préparer la journée » de Dental Lens —
semaine navigable à gauche, patients à droite, et seule l'action qui attend un geste est
un bouton. C'est la mise en page que `docs/JOURNEE_DOCTOLIB.md` désignait déjà comme
référence. Une seule différence de fond : « Créer le dossier » crée le dossier **dans
Oris**, là où Dental Lens créait le dossier SmileCloud.

- `agenda.lire_semaine()` et `GET /journee/semaine?depuis=&jours=` — l'état de chaque
  jour : lu ou non, combien de patients, combien de dossiers manquants dans Oris. Le
  serveur Dental Lens n'est interrogé qu'une fois : muet au premier jour, il le serait
  aux six suivants, et sept attentes de 1,5 s figeraient la colonne dix secondes.
- `app/journee/dates.ts` — lundi de la semaine, décalage de jours, « Aujourd'hui /
  Demain / Hier », libellé « 28 sept. – 4 oct. ». Tout en heure locale, jamais
  `toISOString`. Cinq tests.
- `app/journee/Semaine.tsx` — la colonne, avec sa pastille de couleur doublée d'un mot.
- « Créer N dossiers » en haut, qui saute les rendez-vous annulés, et reprend ligne par
  ligne ce qui a échoué sans abandonner le reste.

### Une journée « lue » est une journée relevée

Dental Lens répond pour n'importe quelle date, avec une liste vide si personne n'a encore
ouvert cet agenda. Se fier à sa réponse faisait passer un jeudi jamais relevé pour un
jeudi sans patient. `Journee.disponible` exige maintenant l'heure de lecture.

## La journée est maintenant **déposée**, plus jamais cherchée (21 septembre 2026)

Décision de Franck, le même jour : Oris ne va plus interroger Dental Lens. C'est
l'extension Chrome qui livre la journée à Oris comme elle la livre déjà à Dental Lens.
Oris n'a plus besoin que personne d'autre tourne.

- `POST /journee/depot`, ouvert **à cette machine seulement** (403 `DEPOT_NON_LOCAL`).
  Aucun praticien connecté : c'est une livraison de machine à machine. Et surtout,
  **aucun patient n'est créé** — la création reste le geste du praticien (§58).
- Rangement hors de la base clinique : un fichier par date dans
  `~/Library/Application Support/Oris/journees/`, écrit en deux temps (fichier
  provisoire puis renommage) pour qu'une coupure ne laisse pas une journée tronquée,
  illisible le matin où on en a besoin.
- La date venue du dehors est refabriquée à partir d'une vraie date avant de composer
  un nom de fichier : sans cela, un `jour` valant `../../ailleurs` écrirait où il veut.
- Une livraison vide ne remplace jamais une journée qui ne l'était pas. Une lecture
  ratée renvoie zéro ligne, et elle effacerait la seule liste du praticien.
- Secret partagé facultatif (`JOURNEE_DEPOT_TOKEN`), comparé en temps constant.

Disparaissent : `agenda_provider`, `dental_lens_url`, `dental_lens_registre`,
`_par_le_serveur`, `_par_le_fichier`, et la dépendance à `httpx` pour cet écran.

### Ce que l'écran y perd

Le voyant SmileCloud des lignes venait du rapprochement fait par Dental Lens. L'extension
ne livre que ce qu'elle lit dans Doctolib : le voyant n'a plus de source et a été retiré
des lignes. Le voyant SmileCloud de la fiche patient, lui, est indépendant et reste.

## Patients : une liste vivante, et un bouton qui écoute (21 septembre 2026)

- **La liste des patients** n'est plus un tableau à filets. Chaque dossier est une carte
  posée que le survol soulève, avec les initiales du patient, son nom, son âge et sa date
  de naissance. Les initiales servent de repère : on reconnaît quelqu'un, on ne fait pas
  que le trouver. Ce qui manque est dit en italique plutôt que tu.
- **« Nouvelle consultation »** porte le symbole d'Oris, dont les barres deviennent un
  niveau sonore au survol : le bouton dit ce qu'il va faire. Surtout, il **démarre la
  consultation** au lieu d'ouvrir l'écran de création, où il fallait rechoisir le patient
  qu'on venait justement d'ouvrir. La consultation se crée à la volée et l'écoute s'ouvre.
  L'information du patient (§65) reste demandée sur l'écran d'écoute : le raccourci porte
  sur la navigation, jamais sur le consentement.
- Le bouton « Commencer » de « Votre journée » est **le même composant** : même geste,
  même vert, posé et non surélevé pour que onze boutons côte à côte ne fassent pas un mur.
- **Les onglets** (Historique / Pièces jointes, et partout ailleurs) étaient trop discrets
  pour qu'on sache qu'on pouvait changer de vue. Rail creusé et bordé, onglet choisi
  surélevé et écrit dans le vert de l'action, texte plus grand.

## La liste des patients dit ce qu'elle sait (21 septembre 2026)

Les lignes étaient vides : un nom et une date de naissance. Chacune porte maintenant le
suivi — combien de comptes rendus, le dernier, et ce qui attend une relecture — et un
dossier jamais vu le dit en toutes lettres plutôt que de laisser un blanc.

- `patients.resumes()` : **une seule requête groupée** pour toute la liste, pas une par
  ligne. La liste en affiche vingt d'un coup.
- `PatientListOut` est une classe à part, et non trois champs de plus sur `PatientOut` :
  ailleurs ces comptes ne sont pas calculés, et un champ à zéro se lirait « aucune
  consultation » au lieu de « on n'a pas regardé ».
- Le relief vient du **creux** : le fond de la liste est enfoncé, chaque dossier est posé
  dessus avec sa propre bordure. Un filet entre deux lignes ne séparait rien.

**Les correspondants n'ont pas été mis** : rien n'existe en base pour les porter
(l'écran dédié est un chantier à venir). Une mention « aucun correspondant » sur chaque
ligne aurait été du bruit, pas de l'information.

## L'app iPhone recompile : elle appelait encore la palette bleue (21 septembre 2026)

Cause des courriels d'échec de GitHub. Le 20/09, la direction visuelle est passée du
bleu technologique aux neutres chauds et au vert profond. `design/tokens.json` a changé,
`Tokens.swift` a été régénéré — et les écrans SwiftUI ont continué d'appeler
`OrisColor.deepBlue`, `.orisBlue`, `.cloud`, `.graphite`, `.mistyTeal`, qui n'existaient
plus. L'app ne **compilait** plus ; les tests étaient annulés avant de commencer.

Correspondance appliquée, d'après ce que chaque couleur faisait dans l'ancienne palette :
`deepBlue → deepGreen`, `orisBlue → orisGreen`, `mistyTeal → brightGreen` (l'accent vif,
sur fond clair), `cloud → sand`, `graphite → ink`. 39 tests iOS repassent.

L'app iPhone n'est pas redessinée pour autant : elle a la nouvelle palette, pas la
nouvelle mise en page. C'est un chantier à part.

## Demander une journée, et la mettre à jour (21 septembre 2026)

Il manquait le geste inverse du dépôt : Oris ne va rien chercher, il ne pouvait donc pas
rafraîchir une journée. Il pose maintenant une **demande**, que l'extension vient lire.

- `POST /journee/demande` — geste du praticien, depuis l'écran. Écrit la demande, rien
  d'autre : ni patient, ni journée.
- `GET /journee/demandes` — lu par l'extension, sur cette machine seulement.
- Une demande est **servie par le dépôt** de la journée correspondante, pas par le fait
  de l'avoir lue : une lecture ratée laisse la demande debout.
- Oubliée au bout de douze heures. Chrome peut rester fermé une journée entière et la
  demande doit y survivre ; relire l'agenda d'avant-hier n'aurait aucun sens.
- Le bouton dit **« Charger la journée »** quand rien n'a été relevé, **« Mettre à
  jour »** ensuite. Tant qu'on attend, un bandeau le dit avec un point qui bat.
- L'écran se rafraîchit **dès qu'on revient sur sa fenêtre**, et toutes les huit secondes
  tant qu'une relecture est attendue : on part lire Doctolib dans Chrome, on revient, la
  journée est là. Vérifié de bout en bout.

### Un défaut de composant corrigé au passage

`EtatVide` est une grille : une explication contenant un passage en gras y partait à la
ligne toute seule, et l'écran vide de la journée ressemblait à un poème. Les enfants sont
maintenant enveloppés dans un seul élément — même défaut, même correction que pour les
bandeaux plus tôt dans la journée.

---

## Le dossier SmileCloud du patient, et une reconnaissance de noms commune (21 septembre 2026)

Deuxième pas du cadrage `docs/PIECES_JOINTES_SMILECLOUD.md` : avant de pouvoir
rapatrier les photos d'un patient, il faut savoir **quel dossier SmileCloud** est le
sien, et savoir le reconnaître quand son nom n'est pas écrit pareil des deux côtés.

### Le champ

`Patient.smilecloud_case_id` (migration `0012`, `String(64)`, nullable). Un champ à lui,
**pas** `external_id` : celui-ci porte le numéro de dossier du cabinet, saisi à la main
et affiché dans la liste des patients. Les confondre ferait perdre l'un des deux.

Il se pose et se retire par `PATCH /patients/{id}`, `None` valant « ce n'était pas le
bon dossier ». Le contrat n'accepte qu'une forme d'identifiant (`^[0-9a-fA-F-]{8,64}$`) :
assez souple pour survivre à un changement de format chez SmileCloud, assez stricte pour
refuser un nom de patient collé par erreur dans le champ.

### La reconnaissance de noms

`services/rapprochement.py`, transposé de `attribution.py` de Dental Lens, où il tourne
depuis septembre 2026 sur 772 dossiers réels. Deux seuils plutôt qu'une comparaison
binaire : `SUR = 0.995` (c'est le même patient, on l'affirme) et `DOUTE = 0.72` (ça
ressemble, **on demande**).

`proposer(nom, connus)` rend quatre états : `trouve`, `a_confirmer`, `ambigu`
(plusieurs correspondants certains — on ne tire pas au sort) et `absent`. Il ne sait pas
ce que désignent les clés qu'on lui donne, et c'est voulu : il sert au rapprochement des
patients d'Oris comme à celui des dossiers SmileCloud.

Le fond de l'affaire tient en un test : « Paul MARTIN » et « Paule MARTIN » se
ressemblent à 95 % et **ne doivent jamais** être rapprochés automatiquement. Rattacher
des photos ou une consultation au mauvais patient est pire qu'un doublon.

### Ce que ça change dans l'écran « Votre journée »

`api/journee.py` rapprochait les noms par égalité stricte après mise à plat des accents
et de la casse, prénom contre prénom. Il passe au rapprochement commun, avec la même
exigence de certitude : « MOREAU Chloé » reconnaît désormais « Moreau Chloe » **et**
« Chloe Moreau », ordre inversé compris. En dessous de la certitude, `patient_id` reste
`None` : la ligne s'affiche comme un patient à créer, et c'est au praticien de dire que
c'est le même.

### Fichiers

`db/models.py` · `alembic/versions/0012_patient_smilecloud_case.py` · `api/schemas.py` ·
`api/journee.py` · `services/rapprochement.py` (nouveau) ·
`tests/test_rapprochement.py` (nouveau, 19 cas) · `tests/test_pipeline_api.py` ·
contrats et gabarits iOS régénérés.

### Ce qui n'est pas fait, volontairement

**Rien de visible dans l'application.** Le champ s'écrit par l'API, mais aucun écran ne
permet encore de choisir un dossier SmileCloud — parce que la seule façon sensée de le
choisir est la liste des dossiers que l'extension Chrome livrera, et qu'elle n'existe
pas encore. C'est le troisième pas du cadrage.

## L'attente se montre, et « au prochain passage » veut dire quelque chose (21/09/2026)

Trois défauts signalés par Franck sur l'écran d'attente, et une question qui en valait
la peine : « que veut dire au prochain passage ? »

Réponse, lue dans le code de l'extension (`extension/background.js` de Dental Lens) :
elle se réveille sur une alarme **toutes les minutes** (`PERIODE_MINUTES = 1`), demande
au Mac ce qu'il y a à faire, et si un agenda est à lire, ouvre
`pro.doctolib.fr/calendar/<jour>/list` dans un onglet de fond, laisse la page s'installer
(≈ 6 s), lit la liste et livre. Soit **dix à quatre-vingt-dix secondes** en pratique.
L'écran le dit maintenant en ces termes, au lieu d'une formule creuse.

- **Barre d'attente** avec le temps écoulé, et trois phrases qui suivent le déroulé
  réel. La barre glisse sans prétendre connaître l'avancement — on ne sait pas où en est
  l'extension — mais le chrono, lui, dit quelque chose de vrai.
- **Passé deux minutes**, la barre s'arrête (continuer à glisser laisserait croire que
  quelque chose avance), le bandeau passe à l'orange et pose les deux bonnes questions :
  Chrome est-il ouvert, et Oris est-il déclaré comme destinataire ?
- **Le bouton ne se represse plus** tant qu'on attend : il affiche « Relecture
  demandée » et reste éteint.
- **`DELETE /journee/demande`** et un bouton « Annuler » : une demande sans réponse ne
  coince plus l'écran.

### Ce qui manque encore, et qui n'est pas dans Oris

L'extension demande à **Dental Lens** ce qu'il y a à lire ; elle ne connaît pas encore
`GET /journee/demandes` d'Oris. Tant que ces quelques lignes ne sont pas écrites dans le
projet Dental Lens, le bouton pose une demande que personne ne sert — et l'écran finit
par le dire, ce qui est déjà mieux que d'attendre en silence.

## Le carnet d'adresses des correspondants (21 septembre 2026)

Cadré avec Franck le matin même. L'écran n'est plus un « chantier à venir ».

**Ce que porte une fiche** : nature, civilité, nom, prénom, spécialité, nom du cabinet,
adresse électronique, téléphone, **adresse postale**, note libre.

L'adresse postale n'est pas un ornement : le courrier d'adressage existe déjà dans Oris
comme une **vraie lettre** (`export.py`, en-tête, « Chère Consœur, Cher Confrère, »,
« Confraternellement, »). Sans adresse, elle ne peut ni s'imprimer ni se poster. La liste
signale donc les fiches **sans adresse**, et rien sur celles qui en ont une : on marque
ce qui manque, pas ce qui va.

**Deux natures, et c'est ce qui structure la table.** Un praticien a une civilité, un
prénom, une spécialité, un cabinet. Une structure (CHU, service hospitalier) n'a rien de
tout cela — et la lettre ne lui dit pas « Chère Consœur ». Le serveur efface ces champs
plutôt que de les accepter en silence ; l'écran les fait disparaître du formulaire.

**Le filtre par spécialité** inclut « non renseignée », qui sert à retrouver les fiches à
compléter — mais **écarte les structures** : elles n'ont pas de spécialité par nature, pas
par oubli.

**Les spécialités** : trois connues d'avance dans le code (Omnipraticien, ODF, CMF), les
autres ajoutées depuis les Paramètres. Le correspondant range le **libellé**, pas un
renvoi : retirer une spécialité de la liste ne vide pas les fiches qui la portaient, et
un renommage n'a pas à réécrire la base.

### Écarté à la demande de Franck

Messagerie sécurisée de santé distincte de l'adresse mail, numéro RPPS, et
archivage plutôt que suppression. J'avais insisté sur le premier — un courrier
d'adressage porte des données de santé nommées, et une adresse mail ordinaire n'est pas
le bon tuyau. La décision est prise, elle est notée ici pour ne pas être reperdue.

### Reste à faire

Le rattachement patient ↔ correspondant, avec son qualificatif (adressé par / adressé à /
suit aussi ce patient). La fiche patient affiche toujours « aucun — à venir ».

### Deux défauts attrapés en chemin

- Une fiche est un `<button>` dans une grille : sans `width: 100%`, chaque ligne
  s'arrêtait à son contenu et la liste faisait un escalier.
- Le modèle déclarait un index que la migration ne créait pas. Le test de cohérence
  entre modèles et migrations l'a vu — c'est exactement son travail. Au passage, la base
  de test portait un second schéma (`learning`) qu'un `DROP SCHEMA public` laissait
  intact : les migrations se rejouent maintenant sur une base réellement vide.

## Le carnet, après relecture de Franck (21 septembre 2026)

- **Une seule frontière.** Le creux de la liste était un second cadre posé dans la carte :
  deux bordures emboîtées, et des lignes qui ne rejoignaient jamais le bord. La carte
  passe en bords francs, le creux devient son corps, les lignes vont d'un bord à l'autre.
- **Ouvrir une fiche, c'est la lire.** On y vient pour retrouver un numéro ou vérifier une
  adresse ; tomber d'emblée sur un formulaire donne l'impression qu'on risque d'abîmer
  quelque chose. La fiche s'ouvre en lecture, un bouton « Modifier » discret la rend
  modifiable.
- **Nom du cabinet et adresse électronique** tiennent sur deux colonnes : dans une seule,
  ils étaient coupés la plupart du temps.
- **Mettre en avant** (migration 0014) : une étoile à gauche de chaque ligne, hors du
  bouton qui ouvre la fiche — c'est un geste de tri, pas une modification. Les marqués
  remontent en tête. À quoi cela servira d'autre n'est pas tranché ; le champ est posé
  parce qu'il ne coûte rien.

L'étoile est **verte**, pas orange : l'orange veut dire « à corriger » partout ailleurs
dans le site, et se serait battue avec la pastille « sans adresse » de la même ligne.
