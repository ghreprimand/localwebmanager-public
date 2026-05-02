#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# GTK comes from system python packages; ensure psutil exists for that interpreter.
if ! python3 -c "import gi; gi.require_version('Gtk', '4.0')" >/dev/null 2>&1; then
  cat >&2 <<'EOF'
GTK 4 Python bindings are required.

Install them with your system package manager, for example:
  Arch:   sudo pacman -S python-gobject gtk4
  Debian: sudo apt install python3-gi gir1.2-gtk-4.0
EOF
  exit 1
fi

if ! python3 -c "import psutil" >/dev/null 2>&1; then
  python3 -m pip install --user psutil >/dev/null
fi

exec python3 -m localwebmanager.desktop
