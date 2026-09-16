# Security & Clinical Data Guardrails

This is an engineering checklist, not legal advice.

## Data classification
- PHI/health data: patient identity, audio, transcript, facts, documents, treatment plans.
- Sensitive operational data: audit events, user IDs, model runs linked to encounters.
- Non-PHI telemetry: latency, status code, anonymous counters when not linkable to patient content.

## Required controls
- TLS in transit;
- encryption at rest;
- MFA in production;
- least privilege;
- secrets manager;
- separate dev/staging/prod;
- synthetic-only dev fixtures;
- encrypted backups and restore drills;
- audit events by stable IDs, not content;
- no transcript/document/audio in generic logs or crash reporting;
- explicit data lifecycle for transient audio;
- vendor data-flow inventory;
- deletion/purge jobs observable and retryable.

## Audio rule
Production default is ephemeral audio. Learning cannot silently override purge policy.

## External providers
Before production, record for each provider:
- purpose;
- data sent;
- region/processing location;
- retention;
- training use;
- subprocessors;
- contractual terms/DPA;
- HDS relevance/scope;
- failure and deletion behavior.

## High-risk engineering mistakes
- storing prompt/transcript bodies in tracing SaaS;
- allowing support snapshots with PHI by default;
- sending full patient identity to STT/LLM when not required;
- using live production examples in unit tests;
- assuming cloud-provider HDS automatically makes the whole application compliant.
