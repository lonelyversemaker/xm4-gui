"""Headset discovery and status."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from xm4_optimizer.transport import rfcomm_socket
from xm4_optimizer.transport.sony_control import SonyControlClient

from .events import Reporter

XM4_NAME_HINTS = ("WH-1000XM4", "LE_WH-1000XM4")


@dataclass(frozen=True)
class HeadsetStatus:
    mac: str
    firmware: str
    battery: int
    charging: bool


def list_devices() -> List[Tuple[str, str]]:
    """Connected Bluetooth devices as (MAC, name), the WH-1000XM4 first."""
    devices = rfcomm_socket.list_connected_devices()
    return sorted(devices, key=lambda d: not is_xm4_name(d[1]))


def is_xm4_name(name: str) -> bool:
    return any(hint in name for hint in XM4_NAME_HINTS)


def read_status(mac: str) -> HeadsetStatus:
    with SonyControlClient.connect(mac) as client:
        firmware = client.get_firmware_version()
        battery = client.get_battery()
    return HeadsetStatus(mac, firmware, battery.level, battery.charging)


def wait_for_reconnect(mac: str, report: Optional[Reporter] = None, timeout_s: float = 180.0,
                       interval_s: float = 5.0, initial_delay_s: float = 10.0) -> HeadsetStatus:
    """Polls until the headset is back after a firmware commit and returns its status."""
    report = report or Reporter()
    deadline = time.monotonic() + timeout_s
    _sleep(initial_delay_s, report)
    last_error: Exception = TimeoutError("headset did not reconnect")
    while time.monotonic() < deadline:
        try:
            if rfcomm_socket.is_device_connected(mac):
                return read_status(mac)
        except Exception as e:  # still rebooting
            last_error = e
        _sleep(interval_s, report)
    raise TimeoutError(f"Headset did not reconnect within {timeout_s:.0f}s ({last_error})")


def _sleep(seconds: float, report: Reporter) -> None:
    if report.cancel.wait(seconds):
        report.check_cancel()
