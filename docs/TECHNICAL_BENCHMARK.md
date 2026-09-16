# Technical Benchmark — providers & infrastructure (16 Sep 2026)

Purpose: define the evaluation harness, not lock Oris into one vendor.

## Current shortlist

### Azure AI Speech
Why benchmark:
- `fr-FR` supported for speech recognition and phrase lists/customization paths;
- Microsoft documents real-time diarization configuration;
- Azure has an HDS v2.0 certification scope including France/EU regions, subject to exact service/contract configuration.

Oris hypothesis: **compliance-first baseline** and strong candidate for production if dental vocabulary accuracy is competitive.

### Deepgram Nova-3
Why benchmark:
- French is included in Nova-3 multilingual;
- streaming diarization available;
- keyterm prompting can inject domain terminology;
- vendor documents sub-300 ms streaming latency for Nova-3;
- self-hosted option exists.

Caveat: do not assume Deepgram cloud itself satisfies the French HDS architecture; legal/hosting scope must be checked. Self-hosted deployment may change the analysis.

### Speechmatics
Why benchmark:
- French real-time transcription;
- real-time diarization and custom dictionary are documented;
- custom dictionary supports large domain term sets;
- cloud, on-prem/container deployment options.

Caveat: marketing benchmark numbers are not decision-grade for dental French; Oris must test its own audio.

### OpenAI transcription
Why benchmark:
- current transcription API includes GPT transcription models and a diarization model;
- streaming output is available on supported transcription models;
- API offers European data residency for eligible customers and ZDR options on eligible endpoints.

Caveat: data residency/ZDR does **not by itself establish HDS compliance for Oris**. Exact contractual and hosting architecture must be reviewed.

## Clinical extraction shortlist

### Azure OpenAI / structured outputs
Structured outputs can enforce a supplied JSON Schema and are therefore a strong fit for ClinicalFact extraction. Azure's HDS certification is attractive, but the exact service/region/deployment scope must be verified before production.

### OpenAI API / structured extraction
Keep as benchmark candidate with strict JSON Schema, EU processing/ZDR configuration when eligible. Same caveat: compliance is an architecture/contract question, not a model feature.

## Benchmark harness

Test each STT provider on the **same audio files**. Required metrics:
- dental WER;
- Tooth Number Accuracy;
- material/brand recall;
- negation word preservation;
- speaker attribution accuracy;
- interim latency p50/p95;
- finalization latency p50/p95;
- reconnect behavior;
- keyterm/glossary gain;
- cost per 30-minute consultation.

### Critical weighted score
Do not select using WER alone.

Example weights:
- Tooth Number Accuracy 25%
- critical term recall 15%
- negation preservation 15%
- speaker diarization 10%
- overall dental WER 10%
- latency 10%
- customization 5%
- operational reliability 5%
- cost 5%

Compliance/security is a **gate**, not a weighted bonus.

## Extraction benchmark
Use finalized transcripts and the 100-case synthetic truth set.
Measure:
- Clinical Fact Precision/Recall;
- Negation Accuracy;
- Temporality Accuracy;
- Plan-vs-Performed Accuracy;
- Unsupported Statement Rate;
- schema validity;
- latency/cost.

## Provisional architecture recommendation
1. Build `SpeechToTextProvider` adapters for at least Azure Speech + one of Deepgram/Speechmatics.
2. Build `ClinicalExtractionProvider` with strict JSON Schema.
3. Keep raw vendor payloads out of the domain layer.
4. Run Oris-specific benchmark before choosing default provider.
5. Allow finalization STT provider to differ from live interim provider if tests justify it.

## HDS cloud candidates
Azure and Google Cloud both publish HDS v2.0 certification information. Either can host the Oris application layer, subject to service scope, EEA configuration, contracts and shared-responsibility controls.

## Sources
- Microsoft HDS France: https://learn.microsoft.com/en-us/compliance/regulatory/offering-hds-france
- Azure Speech language support: https://learn.microsoft.com/fr-fr/azure/ai-services/speech-service/language-support
- Azure diarization config: https://learn.microsoft.com/fr-fr/azure/ai-services/speech-service/configure-language-identification-diarization
- Azure structured outputs: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs
- Deepgram keyterm prompting: https://developers.deepgram.com/docs/keyterm
- Deepgram diarization: https://developers.deepgram.com/docs/diarization
- Deepgram models/languages: https://developers.deepgram.com/docs/models-languages-overview
- Speechmatics real-time: https://www.speechmatics.com/product/real-time
- Speechmatics French: https://www.speechmatics.com/speech-to-text/french
- Google Cloud HDS: https://cloud.google.com/security/compliance/hds
- OpenAI transcription API: https://platform.openai.com/docs/api-reference/audio
- OpenAI EU data residency: https://openai.com/index/introducing-data-residency-in-europe/

## Decision status
**No production provider selected in v1.2.** This is intentional.
