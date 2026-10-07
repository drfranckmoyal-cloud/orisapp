#!/bin/bash
# Envoie la version du Mac vers le serveur en ligne, puis relance Oris.
# Double-cliquez ce fichier depuis le Finder. Détails : docs/EN_LIGNE.md

set -u
cd "$(dirname "$0")" || exit 1
SERVEUR="root@51.159.130.158"
ADRESSE="https://51-159-130-158.nip.io"

echo "Oris — mise à jour du serveur en ligne"
echo

if ! ssh -o ConnectTimeout=15 -o BatchMode=yes "$SERVEUR" true 2>/dev/null; then
  echo "Serveur injoignable ($SERVEUR)."
  echo "Vérifiez votre connexion, ou que la machine tourne dans la console Scaleway."
  read -r -p "Appuyez sur Entrée pour fermer." _
  exit 1
fi

echo "1/5  Envoi du code…"
# .env, données et dépendances installées restent au serveur : on n'envoie que le code.
rsync -a --delete \
  --exclude '.git' --exclude 'node_modules' --exclude '.venv' --exclude '.venv.nosync' \
  --exclude 'logs' --exclude '__pycache__' --exclude '.next' --exclude '*.pyc' \
  --exclude '.DS_Store' --exclude 'benchmarks/datasets' --exclude 'services/api/.env' \
  ./ "$SERVEUR:/home/oris/app/" || { echo "     échec de l'envoi."; read -r -p "Entrée pour fermer." _; exit 1; }
ssh "$SERVEUR" "chown -R oris:oris /home/oris/app"

echo "2/5  Dépendances du serveur…"
ssh "$SERVEUR" "su - oris -c 'cd /home/oris/app/services/api && .venv/bin/pip install -q -e \".[localdb]\"'" || exit 1

echo "3/5  Mise à jour de la base…"
ssh "$SERVEUR" "su - oris -c 'cd /home/oris/app/services/api && .venv/bin/alembic upgrade head' 2>&1 | tail -1"

echo "4/5  Fabrication du site… (une à deux minutes)"
ssh "$SERVEUR" "su - oris -c 'cd /home/oris/app/apps/web && npm ci --no-audit --no-fund >/dev/null 2>&1 && NEXT_PUBLIC_ORIS_API_URL=$ADRESSE/api NODE_OPTIONS=--max-old-space-size=3000 npm run build >/dev/null 2>&1'" \
  || { echo "     échec de la fabrication du site — rien n'a été relancé."; read -r -p "Entrée pour fermer." _; exit 1; }

echo "5/5  Relance…"
ssh "$SERVEUR" "systemctl restart oris-api oris-web"
sleep 6

CODE=$(curl -s -o /dev/null -w '%{http_code}' "$ADRESSE/")
if [ "$CODE" = "401" ] || [ "$CODE" = "200" ]; then
  echo
  echo "Oris est à jour sur $ADRESSE"
else
  echo
  echo "Le site répond $CODE — regardez : ssh $SERVEUR 'journalctl -u oris-web -n 30'"
fi
echo
