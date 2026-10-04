#!/bin/bash
# Fabrique l'icône « Oris » et la pose dans le Dock.
#
# Un clic dessus : si Oris tourne déjà, le navigateur s'ouvre ; sinon tout démarre
# (base, serveur, site) puis le navigateur s'ouvre. Rien à taper, pas de fenêtre noire.
#
# À relancer si le dossier du projet est déplacé, ou pour remettre l'icône.

set -u
PROJET="$(cd "$(dirname "$0")/.." && pwd)"
APPS="/Applications"
[ -w "$APPS" ] || APPS="$HOME/Applications"
APP="$APPS/Oris.app"

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
# Le démarrage passe par le Terminal, et non par cette app directement : macOS interdit
# à une application de /Applications de lire le dossier Bureau, où vit le projet
# (« Operation not permitted »). Le Terminal, lui, y est déjà autorisé — et la fenêtre
# noire qui s'ouvre est celle que Franck connaît déjà, avec ses quatre étapes.
PROJET="$PROJET"

pret() { curl -fs -m 2 http://localhost:3000 >/dev/null 2>&1 && curl -fs -m 2 http://localhost:8000/health >/dev/null 2>&1; }

# Déjà en marche : on ouvre simplement la fenêtre, sans rien relancer.
if pret; then
  open http://localhost:3000
  exit 0
fi

open -a Terminal "\$PROJET/lancer-oris.command" || {
  osascript -e "display alert \\"Oris\\" message \\"Le dossier d'Oris est introuvable :

\$PROJET

S'il a été déplacé, prévenez Claude pour refaire l'icône.\\"" >/dev/null 2>&1
  exit 1
}
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
echo "Un clic : Oris démarre si besoin, puis la fenêtre s'ouvre."
