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

Clés dans `services/api/.env` (jamais dans le dépôt) : `ALLOW_EXTERNAL_STT=true`,
`DEEPGRAM_API_KEY`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_ENDPOINT`.
Tarifs et statut de conformité : `providers.json`.
Rapports : `reports/` (JSON `EvaluationRun` + Markdown).
