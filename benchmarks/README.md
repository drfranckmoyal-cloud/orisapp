# Banc d'essai transcription (M4)

Compare les fournisseurs de transcription sur **les mêmes enregistrements**, avec les
mesures de `docs/TECHNICAL_BENCHMARK.md`. Aucun fournisseur n'est choisi ici (D020).

## Jeux d'essai

- `datasets/oris-synthetic-tts-v1/` : les 100 consultations du corpus lues par les voix
  françaises de macOS. Le manifeste (textes, locuteurs, horodatages) est versionné ;
  l'audio (`audio/*.wav`) est régénérable et n'est pas dans le dépôt.
  **Utile pour valider la mesure, insuffisant pour décider.**
- Jeux futurs (consultations simulées par des professionnels) : même format de
  manifeste, audio hors dépôt, `consent_documented: true` obligatoire.

Le banc refuse tout jeu qui n'est ni `synthetic_only` ni `consent_documented`.

## Utilisation

```bash
services/api/.venv/bin/python scripts/stt_benchmark.py generate
services/api/.venv/bin/python scripts/stt_benchmark.py run --providers deepgram,azure_speech --limit 10
services/api/.venv/bin/python scripts/stt_benchmark.py run --providers deepgram,azure_speech --streaming
```

## Extraction clinique (M5)

Compare des modèles sur les **transcripts** du corpus (sans audio) contre les faits
attendus : précision et rappel, négations, temporalité, prévu/réalisé, doublons, faits
rédigeables par Oris, rejets par le résolveur, latence, jetons et coût réel.

```bash
services/api/.venv/bin/python scripts/stt_benchmark.py extraction --limit 20
services/api/.venv/bin/python scripts/stt_benchmark.py extraction --models claude-sonnet-5,claude-haiku-4-5-20251001
```

`--limit` prend un échantillon réparti sur les six familles du corpus. Une sortie qui
viole les règles cliniques donne droit à trois essais expliqués au modèle, puis elle est
rejetée — le rapport nomme alors les règles refusées. Une coupure réseau ou un quota est
repassé deux fois : ce n'est pas un défaut de la sortie. Tarifs des modèles : `providers.json` (relevés sur la page officielle,
avec la date).

Clés dans `services/api/.env` (jamais dans le dépôt) : `ALLOW_EXTERNAL_STT=true`,
`DEEPGRAM_API_KEY`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_ENDPOINT` ; pour l'extraction
`ALLOW_EXTERNAL_LLM=true` et `ANTHROPIC_API_KEY`.
Tarifs et statut de conformité : `providers.json`.
Rapports : `reports/` (JSON `EvaluationRun` + Markdown).
