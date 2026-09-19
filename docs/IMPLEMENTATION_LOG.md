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
