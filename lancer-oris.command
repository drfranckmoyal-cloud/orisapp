#!/bin/bash
# Démarre Oris sur ce Mac : base de données, serveur, site, puis ouvre le navigateur.
# Double-cliquez ce fichier depuis le Finder.

set -u
cd "$(dirname "$0")" || exit 1
mkdir -p logs

PYTHON="services/api/.venv/bin/python"
UVICORN="services/api/.venv/bin/uvicorn"

echo "Oris — démarrage"
echo

if [ ! -x "$PYTHON" ]; then
  echo "L'environnement Python est introuvable ($PYTHON)."
  echo "Prévenez Claude : l'installation doit être refaite."
  read -r -p "Appuyez sur Entrée pour fermer." _
  exit 1
fi

echo "1/4  Base de données…"
"$PYTHON" scripts/dev_postgres.py start >> logs/postgres.log 2>&1 || {
  echo "     échec — voir logs/postgres.log"
  read -r -p "Appuyez sur Entrée pour fermer." _
  exit 1
}

echo "2/4  Mise à jour de la base…"
(cd services/api && .venv/bin/alembic upgrade head) >> logs/migrations.log 2>&1 || {
  echo "     échec — voir logs/migrations.log"
  read -r -p "Appuyez sur Entrée pour fermer." _
  exit 1
}

# Ce qui répond déjà n'est pas tué : redémarrer un serveur sain coûte deux minutes
# d'attente, le temps qu'il recharge tout. Les délais sont larges exprès — un service
# occupé met parfois plusieurs secondes à répondre sans être en panne pour autant.
echo "3/4  Serveur Oris…"
if curl -fs -m 8 http://localhost:8000/health >/dev/null 2>&1; then
  echo "     déjà en marche, conservé."
else
  pkill -f "uvicorn oris_api" 2>/dev/null
  # Ouvert au Wi-Fi du cabinet pour l'iPhone (décision du 21/09/2026). Hors de ce Mac,
  # le serveur exige un jeton d'accès : un appareil sans jeton ne lit rien.
  (cd services/api && nohup "../../$UVICORN" oris_api.main:app --host 0.0.0.0 --port 8000 \
    --no-access-log >> ../../logs/api.log 2>&1 &)
fi

echo "4/4  Site…"
if curl -fs -m 15 http://localhost:3000 >/dev/null 2>&1; then
  echo "     déjà en marche, conservé."
else
  pkill -f "next dev" 2>/dev/null
  (nohup npm --prefix apps/web run dev >> logs/web.log 2>&1 &)
fi

printf "     attente (jusqu'à deux minutes au premier démarrage)"
# Au premier démarrage, le site se compile : il faut lui laisser deux bonnes minutes,
# sinon le navigateur s'ouvre sur une page d'erreur.
for _ in $(seq 1 150); do
  if curl -fs -m 8 http://localhost:8000/health >/dev/null 2>&1 \
     && curl -fs -m 15 http://localhost:3000 >/dev/null 2>&1; then
    echo " — prêt."
    break
  fi
  printf "."
  sleep 1
done
echo

MOTEURS=$(curl -fs http://localhost:8000/health 2>/dev/null \
  | "$PYTHON" -c 'import json,sys; p=json.load(sys.stdin)["providers"]; print("transcription :", p["speech_to_text"], "· extraction :", p["clinical_extraction"])' 2>/dev/null)
[ -n "$MOTEURS" ] && echo "Moteurs actifs — $MOTEURS"
echo
echo "Oris est ouvert sur http://localhost:3000"
echo "Pour tout arrêter : double-cliquez arreter-oris.command"
echo
open http://localhost:3000
