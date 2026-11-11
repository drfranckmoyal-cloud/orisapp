#!/bin/bash
# Publie Oris partout à la fois : le serveur et le site en ligne, puis l'app iPhone.
#
# Franck, le 11/11/2026 : « j'aimerais que l'app ordi et téléphone soient toujours
# coordonnées et à jour en même temps ». Une seule commande, donc, et dans cet ordre :
#   1. les essais (serveur et site) — rien ne part s'ils échouent ;
#   2. le serveur et le site en ligne (deployer-en-ligne.command) ;
#   3. l'app iPhone, envoyée à Apple pour TestFlight.
#
# L'envoi à Apple se fait tout seul si une clé App Store Connect est posée dans
# ~/.config/oris/appstoreconnect (voir docs/IPHONE.md) ; sinon l'archive s'ouvre dans
# Xcode, et il reste un clic : « Distribute App ».

set -u
cd "$(dirname "$0")" || exit 1
PROJET="$(pwd)"
JOUR="$(date +%Y-%m-%d)"
ARCHIVE="$HOME/Library/Developer/Xcode/Archives/$JOUR/Oris $(date +%d-%m-%Y-%Hh%M).xcarchive"
CLE="$HOME/.config/oris/appstoreconnect"

echo "Oris — publication sur le site et l'iPhone"
echo

echo "1/3  Essais…"
(cd services/api && .venv/bin/python -m pytest -q >/tmp/oris-essais-serveur.log 2>&1) \
  || { echo "     essais du serveur en échec — rien n'est publié (voir /tmp/oris-essais-serveur.log)"; exit 1; }
(cd apps/web && npm test --silent >/tmp/oris-essais-site.log 2>&1) \
  || { echo "     essais du site en échec — rien n'est publié (voir /tmp/oris-essais-site.log)"; exit 1; }
echo "     au vert"

echo "2/3  Serveur et site en ligne…"
./deployer-en-ligne.command || { echo "     échec de la mise en ligne — l'iPhone n'est pas envoyé."; exit 1; }

echo "3/3  App iPhone…"
mkdir -p "$(dirname "$ARCHIVE")"
(cd apps/ios && xcodebuild -project Oris.xcodeproj -scheme Oris -configuration Release \
  -destination 'generic/platform=iOS' -archivePath "$ARCHIVE" archive -allowProvisioningUpdates \
  >/tmp/oris-archive.log 2>&1) || { echo "     fabrication de l'app en échec (voir /tmp/oris-archive.log)"; exit 1; }

if [ -f "$CLE" ]; then
  # shellcheck disable=SC1090
  . "$CLE"
  (cd apps/ios && xcodebuild -exportArchive -archivePath "$ARCHIVE" -exportOptionsPlist export.plist \
    -exportPath /tmp/oris-envoi -allowProvisioningUpdates \
    -authenticationKeyPath "$CLE_FICHIER" -authenticationKeyID "$CLE_ID" \
    -authenticationKeyIssuerID "$CLE_EMETTEUR" >/tmp/oris-envoi.log 2>&1) \
    && echo "     envoyée à Apple : elle arrive dans TestFlight d'ici un quart d'heure." \
    || { echo "     envoi refusé (voir /tmp/oris-envoi.log) — l'archive s'ouvre dans Xcode."; open "$ARCHIVE"; }
else
  open "$ARCHIVE"
  echo "     archive ouverte dans Xcode : cliquez « Distribute App », puis « Distribute »."
fi

echo
echo "Oris est publié : site en ligne à jour, app iPhone en route."
