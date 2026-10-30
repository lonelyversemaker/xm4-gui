#!/bin/sh
# Builds dist/xm4gui (a folder with the executable). Needs BlueZ at runtime.
# Optionally wraps it into an AppImage when appimagetool is on PATH.
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"
"$PY" -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller packaging/xm4gui.spec

if command -v appimagetool >/dev/null 2>&1; then
  APPDIR=build/XM4GUI.AppDir
  rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/bin"
  cp -r dist/xm4gui/. "$APPDIR/usr/bin/"
  cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
exec "$(dirname "$0")/usr/bin/xm4gui" "$@"
RUN
  chmod +x "$APPDIR/AppRun"
  cat > "$APPDIR/xm4gui.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=XM4 Firmware Tool
Exec=xm4gui
Icon=xm4gui
Categories=AudioVideo;Utility;
DESKTOP
  cp xm4gui/ui/resources/icon.png "$APPDIR/xm4gui.png"
  appimagetool "$APPDIR" dist/XM4_Firmware_Tool-x86_64.AppImage
  echo "Built dist/XM4_Firmware_Tool-x86_64.AppImage"
else
  echo "Built dist/xm4gui/ (install appimagetool to also produce an AppImage)"
fi
