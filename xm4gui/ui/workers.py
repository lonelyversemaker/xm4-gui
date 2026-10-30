"""Runs engine functions on a background thread and forwards their callbacks as Qt signals."""

from __future__ import annotations

import threading
import traceback
from typing import Callable

from PySide6.QtCore import QThread, Signal

from ..engine.events import Cancelled, Progress, Reporter


class Worker(QThread):
    progress = Signal(object)   # Progress
    log = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, fn: Callable[[Reporter], object], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        report = Reporter(self._emit_progress, self.log.emit, self.cancel_event)
        try:
            result = self._fn(report)
        except Cancelled:
            self.log.emit("Cancelled by user")
            self.cancelled.emit()
        except Exception as e:
            self.log.emit(traceback.format_exc().rstrip())
            self.failed.emit(str(e) or type(e).__name__)
        else:
            self.succeeded.emit(result)

    def _emit_progress(self, progress: Progress) -> None:
        self.progress.emit(progress)
