#!/bin/bash
# Ramène la dernière sauvegarde du serveur en ligne sur ce Mac.
# Une sauvegarde qui ne vit que sur la machine qu'elle protège ne protège de rien.
# Double-cliquez ce fichier depuis le Finder.

set -u
SERVEUR="root@51.159.130.158"
DOSSIER="$HOME/Library/Application Support/Oris/sauvegardes"

echo "Oris — rapatriement de la sauvegarde en ligne"
echo

if ! ssh -o ConnectTimeout=15 -o BatchMode=yes "$SERVEUR" true 2>/dev/null; then
  echo "Serveur injoignable."
  read -r -p "Appuyez sur Entrée pour fermer." _
  exit 1
fi

mkdir -p "$DOSSIER"

# Une sauvegarde fraîche, puis on la descend.
echo "1/2  Sauvegarde du serveur…"
ssh "$SERVEUR" "systemctl start oris-sauvegarde.service" || exit 1
sleep 3

echo "2/2  Rapatriement…"
ssh "$SERVEUR" "ls -t /var/backups/oris/base-*.sql.gz | head -1" > /tmp/oris-derniere 2>/dev/null
DERNIERE=$(cat /tmp/oris-derniere); rm -f /tmp/oris-derniere
[ -n "$DERNIERE" ] || { echo "     aucune sauvegarde trouvée."; read -r -p "Entrée pour fermer." _; exit 1; }
scp -q "$SERVEUR:$DERNIERE" "$DOSSIER/" || exit 1

# Les pièces jointes (photos) suivent le même chemin.
PIECES=$(ssh "$SERVEUR" "ls -t /var/backups/oris/pieces-*.tgz 2>/dev/null | head -1")
[ -n "$PIECES" ] && scp -q "$SERVEUR:$PIECES" "$DOSSIER/"

# On ne garde que les douze dernières : le disque du Mac n'est pas un coffre sans fond.
cd "$DOSSIER" && ls -t base-*.sql.gz 2>/dev/null | tail -n +13 | xargs -r rm -f
ls -t pieces-*.tgz 2>/dev/null | tail -n +13 | xargs -r rm -f

echo
echo "Sauvegardes gardées dans :"
echo "  $DOSSIER"
ls -lht "$DOSSIER" | head -4 | tail -3 | awk '{print "  "$9"  ("$5")"}'
echo
