#!/usr/bin/env bash
# Anthrophonic installer
set -euo pipefail

BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$BIN_DIR/anthrophonic"
DESKTOP="$APP_DIR/anthrophonic.desktop"

uninstall() {
    rm -fv "$BIN" "$DESKTOP"
    echo "Uninstalled. (config in ~/.config/anthrophonic/ kept)"
    exit 0
}
[ "${1:-}" = "--uninstall" ] && uninstall

echo ">> Checking dependencies..."
missing=0
for cmd in python3 pactl pw-dump paplay; do
    command -v "$cmd" >/dev/null || { echo "  MISSING: $cmd"; missing=1; }
done
python3 -c "import tkinter" 2>/dev/null || { echo "  MISSING: python3-tk (tkinter)"; missing=1; }
python3 -c "import numpy"   2>/dev/null || { echo "  MISSING: numpy (pip install numpy)"; missing=1; }
if [ "$missing" -ne 0 ]; then
    echo ">> Install the missing pieces and retry. On Debian/Ubuntu:"
    echo "   sudo apt install pipewire-pulse pulseaudio-utils python3-tk python3-numpy"
    exit 1
fi

echo ">> Installing..."
mkdir -p "$BIN_DIR" "$APP_DIR"
install -m 755 "$SRC_DIR/anthrophonic.py" "$BIN"
sed "s|__EXEC__|$BIN|" "$SRC_DIR/anthrophonic.desktop" > "$DESKTOP"
chmod +x "$DESKTOP"

echo ">> Done. Look for 'Anthrophonic' in your menu, or run: $BIN"
