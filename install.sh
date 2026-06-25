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

# Icon into the hicolor theme
ICON_BASE="$HOME/.local/share/icons/hicolor"
for sz in 16 32 48 64 128; do
    if [ -f "$SRC_DIR/icons/anthrophonic-$sz.png" ]; then
        mkdir -p "$ICON_BASE/${sz}x${sz}/apps"
        cp "$SRC_DIR/icons/anthrophonic-$sz.png" "$ICON_BASE/${sz}x${sz}/apps/anthrophonic.png"
    fi
done
mkdir -p "$ICON_BASE/256x256/apps"
cp "$SRC_DIR/icons/anthrophonic.png" "$ICON_BASE/256x256/apps/anthrophonic.png"
gtk-update-icon-cache -f -t "$ICON_BASE" 2>/dev/null || true

echo ">> Done. Look for 'Anthrophonic' in your menu, or run: $BIN"
