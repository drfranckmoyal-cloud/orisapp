#!/bin/bash
# Fabrique l'icône « Oris » et la pose dans le Dock.
#
# Un clic dessus ouvre Oris en ligne — le même que sur l'iPhone. Rien à démarrer sur le
# Mac, rien à taper, pas de fenêtre noire.
#
# À relancer si le dossier du projet est déplacé, ou pour remettre l'icône.

set -u
PROJET="$(cd "$(dirname "$0")/.." && pwd)"
APPS="/Applications"
[ -w "$APPS" ] || APPS="$HOME/Applications"
APP="$APPS/Oris.app"
SITE="https://51-159-130-158.nip.io"

echo "Oris — fabrication de l'icône du Dock"
echo "     projet : $PROJET"
echo "     icône  : $APP"
echo

# --- Le programme que lance l'icône -------------------------------------------------
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cat > "$APP/Contents/MacOS/Oris" <<SCRIPT
#!/bin/bash
# Lanceur d'Oris. Fabriqué par scripts/icone-dock.command — ne pas modifier à la main.
#
# Il ouvre le site en ligne : le même serveur, les mêmes dossiers que l'iPhone. Jusqu'au
# 11/11/2026 il ouvrait la copie du Mac (localhost:3000), et les dossiers créés ici
# n'arrivaient jamais sur le téléphone (Franck : « je ne les ai pas retrouvés sur
# l'iPhone »). Rien ne démarre sur le Mac : il n'y a rien à attendre.
open "$SITE"
SCRIPT
chmod +x "$APP/Contents/MacOS/Oris"

# --- L'icône elle-même --------------------------------------------------------------
SOURCE="$PROJET/apps/ios/Oris/Assets.xcassets/AppIcon.appiconset/icone-1024.png"
if [ -f "$SOURCE" ]; then
  JEU="$(mktemp -d)/oris.iconset"
  mkdir -p "$JEU"
  for TAILLE in 16 32 128 256 512; do
    sips -z $TAILLE $TAILLE "$SOURCE" --out "$JEU/icon_${TAILLE}x${TAILLE}.png" >/dev/null 2>&1
    sips -z $((TAILLE * 2)) $((TAILLE * 2)) "$SOURCE" --out "$JEU/icon_${TAILLE}x${TAILLE}@2x.png" >/dev/null 2>&1
  done
  iconutil -c icns "$JEU" -o "$APP/Contents/Resources/oris.icns" >/dev/null 2>&1
fi

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Oris</string>
  <key>CFBundleDisplayName</key><string>Oris</string>
  <key>CFBundleExecutable</key><string>Oris</string>
  <key>CFBundleIdentifier</key><string>fr.oris.lanceur</string>
  <key>CFBundleIconFile</key><string>oris</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

touch "$APP"  # le Finder relit l'icône

# --- La pose dans le Dock -----------------------------------------------------------
if defaults read com.apple.dock persistent-apps 2>/dev/null | grep -q "$APP"; then
  echo "L'icône est déjà dans le Dock."
else
  defaults write com.apple.dock persistent-apps -array-add "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$APP</string><key>_CFURLStringType</key><integer>0</integer></dict></dict></dict>"
  killall Dock 2>/dev/null
  echo "Icône posée dans le Dock."
fi

echo
echo "Terminé. L'icône verte « Oris » est dans votre Dock, à droite."
echo "Un clic : Oris s'ouvre en ligne, avec les mêmes dossiers que sur l'iPhone."
