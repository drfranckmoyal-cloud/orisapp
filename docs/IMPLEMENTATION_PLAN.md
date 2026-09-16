# Implementation Plan — Milestones exécutables

## M0 — Repository & contracts
**Goal:** repo compilable, CI, schemas, DB, MockProviders.
- monorepo folders;
- FastAPI health endpoint;
- PostgreSQL + migrations;
- schemas generated/validated;
- web/iOS shells;
- no real AI.

## M1 — Synthetic vertical slice
- patient CRUD minimal;
- encounter lifecycle;
- synthetic transcript fixture;
- mock clinical extraction;
- treatment plan;
- document projections;
- explicit validation;
- LearningEvent on correction.

**Gate:** critical tests A–J pass.

## M2 — Web audio capture
- microphone permission;
- chunk sequence/checksum/idempotency;
- pause/resume;
- reconnect buffer;
- visible recording state.

## M3 — iOS audio capture
- AVAudioSession/engine;
- interruption handling;
- local encrypted transient chunk buffer;
- reconnect;
- route change handling.

## M4 — STT benchmark adapter
- implement at least 2 providers behind SpeechToTextProvider;
- run `corpus` audio benchmark when real audio dataset exists;
- vocab/keyterm support;
- diarization mapping;
- record latency/cost/accuracy.

## M5 — Clinical extraction
- provider with strict structured output;
- rules: tooth/negation/temporality/status;
- provenance links;
- factual validator;
- regression suite.

## M6 — Consultation UX
- review screen;
- warnings;
- provenance drawer;
- treatment plan cards;
- validate/export;
- PDF/text.

## M7 — Operative templates
- composite;
- direct aesthetic;
- veneer prep/provisional;
- veneer bonding;
- wear additive;
- extraction;
- generic minor surgery.

## M8 — Voice correction
- correction intent parser;
- structured patch;
- preview for high-impact change;
- version bump;
- document invalidation/regeneration;
- LearningEvent.

## M9 — Personalization MVP
- practitioner glossary;
- preferred terminology;
- style preferences;
- repeated correction suggestion;
- reversible learned preferences.

## M10 — Hardening
- audit log;
- PHI-safe observability;
- MFA;
- backup/restore;
- audio purge;
- failure recovery;
- load/latency tests.

## M11 — Clinical staging
- HDS-compatible target environment;
- vendor contracts/data flows reviewed;
- synthetic + professional simulated sessions;
- shadow mode framework;
- beta gate.

### Release rule
No milestone is considered done if tests pass but the clinical invariants are violated.
