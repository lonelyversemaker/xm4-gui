# PyInstaller spec: pyinstaller packaging/xm4gui.spec (run from the repo root via build_macos.sh / build_linux.sh)
import os
import sys

block_cipher = None
root = os.path.abspath(os.path.join(SPECPATH, ".."))
bridge = os.environ.get("XM4_PREBUILT_BRIDGE")
# xm4_optimizer may be an editable install, which PyInstaller cannot discover on its own.
import xm4_optimizer
from PyInstaller.utils.hooks import collect_submodules
xm4_root = os.path.dirname(os.path.dirname(xm4_optimizer.__file__))
icon = os.path.join(root, "xm4gui", "ui", "resources", "icon.png")

a = Analysis(
    [os.path.join(root, "packaging", "launcher.py")],
    pathex=[root, xm4_root],
    binaries=[(bridge, ".")] if bridge else [],
    datas=[(icon, "xm4gui/ui/resources")],
    hiddenimports=["xm4gui.ui.main_window"] + collect_submodules("xm4_optimizer"),
    excludes=["tkinter", "numpy.f2py", "PySide6.Qt3DCore", "PySide6.QtWebEngineCore", "PySide6.QtQuick", "PySide6.QtQml"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="xm4gui", console=False, icon=icon)
coll = COLLECT(exe, a.binaries, a.datas, name="xm4gui")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="XM4 Firmware Tool.app",
        icon=icon,
        bundle_identifier="io.github.lonelyversemaker.xm4gui",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "NSBluetoothAlwaysUsageDescription": "XM4 Firmware Tool talks to your Sony WH-1000XM4 over Bluetooth to read its status, back up its calibration and install firmware.",
            "NSHighResolutionCapable": True,
        },
    )
