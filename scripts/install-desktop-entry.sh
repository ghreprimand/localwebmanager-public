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
GenericName=Local Service Dashboard
Comment=View and manage active local web services
Exec=$ROOT_DIR/scripts/localwebmanager start
Icon=localwebmanager
Terminal=false
Categories=Development;Utility;Network;
StartupNotify=false
SingleMainWindow=true
Keywords=web;services;localhost;ports;dev;server;
DESKTOP

chmod +x "$DESKTOP_FILE"
echo "Installed: $DESKTOP_FILE"
