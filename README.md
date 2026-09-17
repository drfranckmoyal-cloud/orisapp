# Oris — Claude Code Handoff Pack v1.2

Ce dossier est le paquet de bascule officiel vers Claude Code.

## Ordre de lecture obligatoire

1. `START_HERE.md`
2. `CLAUDE.md`
3. `ORIS_MASTER_SPEC_V1_2.md`
4. `docs/DECISIONS.md`
5. `schemas/README.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. `docs/ACCEPTANCE_CRITERIA.md`
8. `docs/DESIGN_SYSTEM.md`
9. `docs/AI_ARCHITECTURE.md`
10. `docs/TECHNICAL_BENCHMARK.md`
11. `corpus/README.md`

## Règle

Ne pas commencer par connecter une API IA. Commencer par un vertical slice synthétique avec MockProviders et les schémas fournis.

## Où en est le projet

`PROJET-MAITRE.md` : état du projet en une page (ce qui marche, ce qui bloque, ce qui
est attendu du praticien). Mis à jour à la fin de chaque jalon.

## Développement

Le code vit à côté de la spécification : `services/api` (FastAPI), `apps/web`
(Next.js), `apps/ios` (SwiftUI). Installation, lancement et contrôles :
`docs/DEVELOPMENT.md`. Choix d'implémentation : `docs/IMPLEMENTATION_LOG.md`.
