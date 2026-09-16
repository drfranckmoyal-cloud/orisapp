# Changelog

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
