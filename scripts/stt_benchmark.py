#!/usr/bin/env python3
"""Banc d'essai transcription. Voir `oris_api.benchmark.cli`.

  services/api/.venv/bin/python scripts/stt_benchmark.py generate [--limit 10]
  services/api/.venv/bin/python scripts/stt_benchmark.py run --providers deepgram,azure_speech [--streaming]
"""

import sys

from oris_api.benchmark.cli import main

sys.exit(main())
