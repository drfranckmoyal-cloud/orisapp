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

