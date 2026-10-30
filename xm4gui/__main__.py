"""Entry point: python -m xm4gui"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _use_bundled_bridge() -> None:
    """In a packaged macOS app, point xm4_optimizer at the prebuilt RFCOMM helper."""
    if sys.platform != "darwin" or os.environ.get("XM4_BRIDGE_BIN"):
        return
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for candidate in (base / "rfcomm_bridge", base.parent / "Resources" / "rfcomm_bridge"):
        if candidate.is_file():
            os.environ["XM4_BRIDGE_BIN"] = str(candidate)
            return


def main() -> int:
    _use_bundled_bridge()
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .ui.main_window import MainWindow
    from .ui.strings import t

    app = QApplication(sys.argv)
    app.setApplicationName(t("app_title"))
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "ui" / "resources" / "icon.png")))
    window = MainWindow()
    window.resize(620, 760)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
