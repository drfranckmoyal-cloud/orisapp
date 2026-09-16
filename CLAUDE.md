# CLAUDE.md — Permanent Repository Instructions for Oris

You are implementing a clinical documentation product. Optimize for correctness, auditability, recoverability, and simplicity before feature count.

## Non-negotiable architecture

- iOS native: Swift + SwiftUI.
- Web: Next.js + TypeScript.
- Backend: Python + FastAPI + PostgreSQL.
- One backend and one clinical domain model for both clients.
- Clinical Encounter Object is the source of truth.
- Documents are projections of structured clinical facts.
- A clinical correction updates the structured object first, then invalidates/regenerates projections.
- Provider interfaces must isolate STT and LLM vendors.
- Production providers are configuration, not domain logic.

## Clinical safety invariants

1. Never invent a missing clinical fact.
2. Preserve negation.
3. Preserve uncertainty.
4. Preserve temporality.
5. Distinguish patient-reported vs clinician-observed/assessed.
6. Distinguish discussed/proposed/accepted/refused/deferred/planned/performed.
7. Tooth numbers are high-risk data.
8. Audio loss must generate an explicit warning.
9. AI drafts are never automatically validated.
10. Every document claim must be supportable by structured facts.

## Learning invariants

- Capture corrections as LearningEvents.
- Personalization may improve recognition/style, never insert a clinical fact.
- No online self-modifying model in production.
- Prompt/model/rule changes are versioned and evaluated.
- A validated correction has more learning weight than an unchanged draft.

## Engineering rules

- Strict types everywhere practical.
- JSON Schema/OpenAPI are contracts; do not fork definitions manually.
- DB changes require migrations.
- Critical domain logic requires tests.
- Never log raw transcripts, patient names, diagnoses, documents, or audio.
- Use synthetic fixtures in dev/test.
- Idempotency for audio chunks and AI processing steps.
- Prefer a modular monolith over premature microservices.
- Use feature flags for incomplete/high-risk functionality.

## Workflow

Before implementing a milestone:
1. read its acceptance criteria;
2. state files/modules to change in IMPLEMENTATION_LOG.md;
3. implement smallest coherent slice;
4. run tests/lint/typecheck;
5. update CHANGELOG and KNOWN_LIMITATIONS;
6. do not silently expand scope.

## Stop conditions

If a requested change conflicts with MASTER_SPEC or schemas, do not guess. Record the conflict and preserve the higher-priority source of truth.
