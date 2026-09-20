#!/bin/bash
# Arrête Oris : site, serveur, base de données.

set -u
cd "$(dirname "$0")" || exit 1

echo "Oris — arrêt"
pkill -f "next dev" 2>/dev/null && echo "  site arrêté"
pkill -f "uvicorn oris_api" 2>/dev/null && echo "  serveur arrêté"
services/api/.venv/bin/python scripts/dev_postgres.py stop >> logs/postgres.log 2>&1 \
  && echo "  base de données arrêtée"
echo
echo "Tout est arrêté. Vos consultations sont conservées."
