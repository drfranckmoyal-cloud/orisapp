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
