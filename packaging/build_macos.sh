#!/bin/sh
# Builds "dist/XM4 Firmware Tool.app". The RFCOMM helper is compiled here, so users
# of the app do not need the Xcode Command Line Tools.
set -eu
cd "$(dirname "$0")/.."
# For a release use the python.org universal2 Python (see README): it runs on macOS 12+
# and on both Apple Silicon and Intel. Homebrew Python gives a native, host-only build.
PY="${PYTHON:-.venv/bin/python}"
LIBPYTHON=$("$PY" -c 'import sys, sysconfig, os; print(os.path.join(sysconfig.get_config_var("PYTHONFRAMEWORKPREFIX") or sys.base_prefix, sysconfig.get_config_var("LDLIBRARY") or ""))')
if lipo -archs "$LIBPYTHON" 2>/dev/null | grep -q x86_64 && lipo -archs "$LIBPYTHON" | grep -q arm64; then
  ARCHS="arm64 x86_64"; TARGET_ARCH=universal2
else
  ARCHS="$(uname -m)"; TARGET_ARCH=""
fi

SRC_DIR=$("$PY" -c 'import xm4_optimizer.transport.macos_bridge as m; print(m.SOURCE_DIR)')
mkdir -p build
# Target an older macOS than the build host; the bundled Python and Qt set the real floor.
SLICES=""
for arch in $ARCHS; do
  swiftc -O -target "$arch-apple-macos12.0" "$SRC_DIR/rfcomm_bridge.swift" -o "build/rfcomm_bridge-$arch" \
    -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker "$SRC_DIR/Info.plist"
  SLICES="$SLICES build/rfcomm_bridge-$arch"
done
lipo -create $SLICES -output build/rfcomm_bridge
echo "Building for: $ARCHS"

XM4_TARGET_ARCH="$TARGET_ARCH" XM4_PREBUILT_BRIDGE="$PWD/build/rfcomm_bridge" "$PY" -m PyInstaller --noconfirm --clean \
  --distpath dist --workpath build/pyinstaller packaging/xm4gui.spec

# Ad-hoc signature so the bundle and the helper run locally; not notarized.
codesign --force --deep --sign - "dist/XM4 Firmware Tool.app"
echo "Built dist/XM4 Firmware Tool.app"
