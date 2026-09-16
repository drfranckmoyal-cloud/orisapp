# AI Architecture — Oris

## Components

### 1. SpeechToTextProvider
Input: ordered audio chunks + locale + glossary hints.
Output: TranscriptSegments with timestamps, confidence and optional speaker labels.

### 2. TranscriptFinalizer
Responsibilities: consolidate interim text, normalize obvious formatting, retain raw final segments, never invent semantic facts.

### 3. ClinicalExtractionProvider
Input: finalized segments + schema + practitioner glossary.
Output: strict ClinicalFact candidates.

### 4. DeterministicClinicalResolver
Rules: FDI validity, negation consistency, correction precedence, temporal/status conflicts, duplicate merging.

### 5. ClinicalEncounterAssembler
Creates canonical encounter object and versions it.

### 6. DocumentGenerationProvider
Input: clinical object only.
Output: consultation note / plan text / operative note.

### 7. FactualValidator
Checks every claim against fact IDs. Cannot add facts.

### 8. CorrectionInterpreter
Voice/text correction → structured patch. High-impact patches require preview.

### 9. LearningEventEmitter
Records before/after structured diffs and practitioner confirmation.

## Critical design rule
STT text is evidence; ClinicalFacts are normalized evidence; ClinicalEncounter is the canonical state; documents are views.

## Recommended provider strategy
Benchmark STT separately from clinical extraction. The best French ASR does not need to be the best reasoning model.
