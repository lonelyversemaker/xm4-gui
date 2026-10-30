"""Keeps the computer from sleeping while a backup or flash is running."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Optional


class KeepAwake:
    """Context manager; does nothing when no inhibitor tool is available."""

    def __init__(self, reason: str = "Updating headphone firmware") -> None:
        self.reason = reason
        self._proc: Optional[subprocess.Popen] = None

    def _command(self) -> Optional[list]:
        pid = str(os.getpid())
        if sys.platform == "darwin" and shutil.which("caffeinate"):
            return ["caffeinate", "-ims", "-w", pid]
        if sys.platform.startswith("linux") and shutil.which("systemd-inhibit"):
            return ["systemd-inhibit", "--what=sleep:idle", "--who=XM4 GUI", f"--why={self.reason}",
                    "--mode=block", "sleep", "infinity"]
        return None

    def __enter__(self) -> "KeepAwake":
        cmd = self._command()
        if cmd:
            try:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                self._proc = None
        return self

    def __exit__(self, *exc: object) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
