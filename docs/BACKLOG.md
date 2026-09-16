# Backlog — Oris V1

Priority: P0 blocks V1, P1 high-value, P2 later V1.x.

## EPIC E01 — Foundation (P0)
- E01-S01 repo/CI/typecheck/lint/test
- E01-S02 environment config + secrets
- E01-S03 DB + Alembic
- E01-S04 shared schemas/codegen
- E01-S05 feature flags

## E02 — Identity/Auth (P0)
- practitioner login
- MFA production
- roles skeleton
- Keychain/token handling iOS

## E03 — Patients (P0)
- minimal patient create/search/open
- PHI-safe audit references

## E04 — Encounter state machine (P0)
- draft/recording/paused/finalizing/processing/review/validated/exported
- recoverable error states

## E05 — Audio Web (P0)
- permission/device selection
- chunking/checksum/retry
- local transient queue

## E06 — Audio iOS (P0)
- AVAudioSession
- interruption/route/network handling
- encrypted transient cache

## E07 — STT abstraction (P0)
- provider interface
- interim/final segments
- diarization mapping
- lexicon injection adapter
- benchmark harness

## E08 — Clinical Engine (P0)
- ClinicalFact creation
- tooth normalizer
- negation/temporality/certainty/status resolver
- provenance
- conflict detector

## E09 — Consultation Note (P0)
- projection from facts
- factual validator
- versions
- source view

## E10 — Treatment Plan (P0)
- item/status/sequence
- cards UI
- manual patch

## E11 — Operative Templates (P0)
- composite
- direct aesthetic
- veneer prep
- veneer bonding
- wear additive
- extraction
- generic minor surgery

## E12 — Review/Validation (P0)
- warnings
- manual edit
- stale document indicator
- validate/export

## E13 — Voice Correction (P0)
- intent → patch
- high-impact confirmation
- object version bump
- LearningEvent

## E14 — Learning Foundation (P0 architecture / P1 UX)
- LearningEvent
- practitioner profile
- glossary
- preference suggestion/revert
- prompt/model/rule registries

## E15 — Export (P0)
- plain text
- structured text
- PDF A4

## E16 — Security/Compliance foundation (P0)
- PHI-safe logging
- audit log
- encryption
- audio purge
- backup/restore

## E17 — Quality/Evals (P0)
- schema validation
- golden suite
- regression suite
- weighted critical score
- evaluation report

## E18 — Attachments (P2)
- attach only, no interpretation

## Explicitly deferred
PMS integrations, billing, agenda, CCAM, implants, specialized endodontics, Android, image diagnosis, patient portal.
