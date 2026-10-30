"""Progress reporting and cancellation shared by the long-running operations."""

from __future__ import annotations

from dataclasses import dataclass
import re
import threading
from typing import Callable, Optional


@dataclass(frozen=True)
class Progress:
    stage: str          # "connect", "erase", "program", "verify", "commit", "backup", "reconnect"
    done: int
    total: int
    bytes_per_s: float = 0.0

    @property
    def fraction(self) -> float:
        return self.done / self.total if self.total else 0.0


class Cancelled(Exception):
    """The user cancelled the operation before anything irreversible happened."""


ProgressFn = Callable[[Progress], None]
LogFn = Callable[[str], None]


def _noop(_arg: object) -> None:
    pass


class Reporter:
    """Bundles the callbacks so engine code can call report.log(...) without None checks."""

    def __init__(self, progress: Optional[ProgressFn] = None, log: Optional[LogFn] = None,
                 cancel: Optional[threading.Event] = None) -> None:
        self.progress = progress or _noop
        self.log = log or _noop
        self.cancel = cancel or threading.Event()

    def check_cancel(self) -> None:
        if self.cancel.is_set():
            raise Cancelled("Operation cancelled")


_MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){2})(?::[0-9A-Fa-f]{2}){3}\b")


def mask_mac(text: str) -> str:
    """Keeps the vendor prefix of every MAC address and hides the device part."""
    return _MAC_RE.sub(lambda m: m.group(1) + ":XX:XX:XX", text)
