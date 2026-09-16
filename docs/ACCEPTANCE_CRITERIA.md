# Acceptance Criteria — Oris V1

## Global release gates
- 0 unsupported clinical statements in curated critical regression set.
- 100% of critical cases preserve tooth number, negation, temporality and treatment status.
- no document reaches `validated` without explicit practitioner action.
- all clinical claims can resolve to supporting fact IDs.
- audio capture failure is visible and blocks false completeness.
- no PHI in standard logs/analytics.

## Active consultation
- start/stop/pause/reconnect states deterministic;
- timer and microphone state visible;
- chunks ordered and idempotent;
- short network interruption recoverable;
- unrecoverable gap creates critical warning.

## Clinical extraction
- strict schema validation;
- invalid provider output retried or rejected, never silently coerced;
- corrections like “26… pardon 27” resolve to final intended tooth;
- patient belief is not promoted to clinician diagnosis;
- “peut-être” remains uncertain;
- future treatment is not marked performed.

## Consultation note
- empty sections omitted;
- no invented material/protocol/diagnosis;
- output style follows practitioner preference without altering facts.

## Treatment plan
- alternatives remain alternatives until explicit decision;
- sequence only when explicit;
- statuses are one of schema enums;
- manual status change updates the clinical object.

## Operative note
- template fields are optional evidence slots, not defaults;
- usual practitioner materials are never auto-filled as performed facts;
- missing critical configured field may warn but not fabricate.

## Learning
- meaningful correction emits LearningEvent;
- user preference can be inspected and reverted;
- local preference never becomes global automatically;
- learning store is logically separate from patient record store.
