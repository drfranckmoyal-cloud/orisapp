# Développement local — Oris

Uniquement des données synthétiques. Aucun fournisseur IA réel (tous `mock`).

## Prérequis

- Python 3.12+ ; Node 20.9+ ; Xcode 26 (pour iOS).
- PostgreSQL 16 : **soit** Docker (`infra/docker/docker-compose.yml`), **soit** la
  base embarquée (`scripts/dev_postgres.py`, sans Docker ni droits administrateur).

## Première installation

```bash
cd services/api
python3 -m venv .venv.nosync && ln -s .venv.nosync .venv   # .nosync : hors iCloud
.venv/bin/pip install -e ".[dev,localdb]"
cd ../../apps/web && npm ci
```

Sur un Bureau synchronisé iCloud, exclure aussi `apps/web/node_modules` et
`apps/web/.next` : `xattr -w 'com.apple.fileprovider.ignore#P' 1 <dossier>`.

## Lancer

```bash
services/api/.venv/bin/python scripts/dev_postgres.py start    # ou : docker compose -f infra/docker/docker-compose.yml up -d
cd services/api && .venv/bin/alembic upgrade head
.venv/bin/uvicorn oris_api.main:app --port 8000 --no-access-log
cd apps/web && npm run dev                                       # http://localhost:3000
open apps/ios/Oris.xcodeproj                                     # schéma Oris, simulateur iPhone
```

## Vérifier

| Partie | Commandes |
|---|---|
| Contrats | `python3 scripts/generate_contracts.py --check` · `python3 scripts/generate_tokens.py --check` |
| API | `ruff check . && ruff format --check . && mypy && pytest` (dans `services/api`, base de test `oris_test` requise) |
| Web | `npm run lint && npm run typecheck && npm test && npm run build` (dans `apps/web`) |
| iOS | `xcodebuild test -project Oris.xcodeproj -scheme Oris -destination 'platform=iOS Simulator,name=iPhone 17'` (dans `apps/ios`) |

## Modifier un contrat

1. Modifier `schemas/*.schema.json` (décision consignée dans `docs/DECISIONS.md` si besoin).
2. `python3 scripts/generate_contracts.py` régénère Python, TypeScript et Swift.
3. Si une valeur d'enum change : nouvelle migration Alembic
   (`alembic revision --autogenerate`), relue à la main.
