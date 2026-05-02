#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/localwebmanager.desktop"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
ICON_FILE="$ICON_DIR/localwebmanager.svg"

mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"
cp "$ROOT_DIR/assets/localwebmanager.svg" "$ICON_FILE"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=LocalWebManager
Comment=View active local web services
Exec=bash -lc 'cd "$ROOT_DIR" && ./run-desktop.sh'
Icon=localwebmanager
Terminal=false
Categories=Development;Utility;
StartupNotify=true
DESKTOP

chmod +x "$DESKTOP_FILE"
echo "Installed: $DESKTOP_FILE"
