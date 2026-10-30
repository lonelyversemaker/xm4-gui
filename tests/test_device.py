import threading

import pytest
from xm4_optimizer.transport.sony_control import BatteryState

from xm4gui.engine import device
from xm4gui.engine.events import Cancelled, Reporter, mask_mac

MAC = "00:11:22:33:44:55"


class FakeClient:
    version = "2.5.0"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def get_firmware_version(self):
        return self.version

    def get_battery(self):
        return BatteryState(70, False)



@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(device.SonyControlClient, "connect", classmethod(lambda cls, mac: FakeClient()))
    return FakeClient


def test_list_devices_puts_xm4_first(monkeypatch):
    monkeypatch.setattr(device.rfcomm_socket, "list_connected_devices",
                        lambda: [("AA:BB:CC:00:00:01", "Mouse"), (MAC, "WH-1000XM4")])
    assert device.list_devices()[0] == (MAC, "WH-1000XM4")


def test_read_status(client):
    status = device.read_status(MAC)
    assert (status.firmware, status.battery, status.charging) == ("2.5.0", 70, False)


def test_wait_for_reconnect(client, monkeypatch):
    answers = iter([False, False, True])
    monkeypatch.setattr(device.rfcomm_socket, "is_device_connected", lambda _mac: next(answers))
    status = device.wait_for_reconnect(MAC, timeout_s=5, interval_s=0.01, initial_delay_s=0)
    assert status.firmware == "2.5.0"


def test_wait_for_reconnect_times_out(monkeypatch):
    monkeypatch.setattr(device.rfcomm_socket, "is_device_connected", lambda _mac: False)
    with pytest.raises(TimeoutError):
        device.wait_for_reconnect(MAC, timeout_s=0.05, interval_s=0.01, initial_delay_s=0)


def test_wait_for_reconnect_can_be_cancelled(monkeypatch):
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        device.wait_for_reconnect(MAC, Reporter(cancel=cancel), initial_delay_s=10)


def test_mask_mac():
    assert mask_mac("connect AC:80:0A:2E:45:80 ch 11") == "connect AC:80:0A:XX:XX:XX ch 11"
