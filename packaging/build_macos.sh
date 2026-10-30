#!/bin/sh
# Builds "dist/XM4 Firmware Tool.app". The RFCOMM helper is compiled here, so users
# of the app do not need the Xcode Command Line Tools.
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON:-.venv/bin/python}"

SRC_DIR=$("$PY" -c 'import xm4_optimizer.transport.macos_bridge as m; print(m.SOURCE_DIR)')
mkdir -p build
# Target an older macOS than the build host; the bundled Python sets the real floor.
swiftc -O -target "$(uname -m)-apple-macos12.0" "$SRC_DIR/rfcomm_bridge.swift" -o build/rfcomm_bridge \
  -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker "$SRC_DIR/Info.plist"

XM4_PREBUILT_BRIDGE="$PWD/build/rfcomm_bridge" "$PY" -m PyInstaller --noconfirm --clean \
  --distpath dist --workpath build/pyinstaller packaging/xm4gui.spec

# Ad-hoc signature so the bundle and the helper run locally; not notarized.
codesign --force --deep --sign - "dist/XM4 Firmware Tool.app"
echo "Built dist/XM4 Firmware Tool.app"
