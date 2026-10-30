import threading

import pytest
from xm4_optimizer.firmware import KnownFirmware

from xm4gui.engine import flash
from xm4gui.engine.events import Cancelled, Reporter

MAC = "00:11:22:33:44:55"
PARTITION_REPLY = bytes.fromhex("0000010000510000f05f00")


class FakeSocket:
    def __init__(self):
        self.reads = 0
        self.sent = []

    def recv(self, _size):
        self.reads += 1
        return b"\x01" if self.reads <= 2 else b""

    def sendall(self, data):
        self.sent.append(bytes(data))

    def settimeout(self, _timeout):
        pass

    def close(self):
        pass


@pytest.fixture
def fake_device(monkeypatch):
    sockets = []
    requests = []

    def make_socket(*_a, **_kw):
        sockets.append(FakeSocket())
        return sockets[-1]

    class Race:
        def __init__(self, _sock):
            pass

        def request(self, command, payload=b"", **_kwargs):
            requests.append((command, bytes(payload)))
            return PARTITION_REPLY if command == flash.CMD_PARTITION_INFO else b"\x00"

    monkeypatch.setattr(flash, "create_rfcomm_socket", make_socket)
    monkeypatch.setattr(flash, "RaceClient", Race)
    monkeypatch.setattr(flash, "identify_firmware", lambda _data: KnownFirmware("MDRID294300", "WH-1000XM4", "test", 512))
    return sockets, requests


def test_partition_reply_and_fota_write_addresses(fake_device):
    sockets, requests = fake_device
    events = []
    result = flash.flash_firmware(MAC, b"\x11" * 256 + b"\x22" * 256, Reporter(progress=events.append))

    assert result.pages_written == 2 and result.firmware.version == "test"
    assert (flash.CMD_START_TRANSACTION, b"") in requests
    assert (flash.CMD_WRITE_STATE, b"\x00\x02") in requests
    assert (flash.CMD_ERASE, bytes.fromhex("010010000000005100")) in requests
    pages = [payload for command, payload in requests if command == flash.CMD_PAGE_PROGRAM]
    assert pages[0][:7] == bytes([1, 1, flash.page_crc(b"\x11" * 256)]) + bytes.fromhex("00005100")
    assert pages[1][:7] == bytes([1, 1, flash.page_crc(b"\x22" * 256)]) + bytes.fromhex("00015100")
    assert pages[0][7:] == b"\x11" * 256 and pages[1][7:] == b"\x22" * 256
    assert requests[-1][0] == flash.CMD_COMMIT

    stages = [e.stage for e in events]
    assert stages == sorted(stages, key=["connect", "erase", "program", "verify", "commit"].index)
    assert events[-1].stage == "commit" and events[-1].done == 1
    assert sockets[0].sent[-1] == flash.MDR_FOTA_OFF


def test_blank_pages_are_skipped_but_counted(fake_device):
    _sockets, requests = fake_device
    events = []
    flash.flash_firmware(MAC, b"\xFF" * 256 + b"\x22" * 256, Reporter(progress=events.append))
    assert len([c for c, _ in requests if c == flash.CMD_PAGE_PROGRAM]) == 1
    assert [e.done for e in events if e.stage == "program"] == [1, 2]


def test_cancel_during_write_does_not_commit(fake_device):
    sockets, requests = fake_device
    cancel = threading.Event()

    def progress(p):
        if p.stage == "program":
            cancel.set()

    with pytest.raises(Cancelled):
        flash.flash_firmware(MAC, b"\x11" * 1024, Reporter(progress=progress, cancel=cancel))
    commands = [c for c, _ in requests]
    assert flash.CMD_COMMIT not in commands and flash.CMD_CHECK_INTEGRITY not in commands
    assert commands.count(flash.CMD_PAGE_PROGRAM) == 1
    assert sockets[0].sent[-1] == flash.MDR_FOTA_OFF


def test_cancel_after_verify_still_stops_before_commit(fake_device):
    _sockets, requests = fake_device
    cancel = threading.Event()

    def progress(p):
        if p.stage == "verify" and p.done == 1:
            cancel.set()

    with pytest.raises(Cancelled):
        flash.flash_firmware(MAC, b"\x11" * 256, Reporter(progress=progress, cancel=cancel))
    assert flash.CMD_COMMIT not in [c for c, _ in requests]
    assert (flash.CMD_WRITE_STATE, b"\x11\x02") not in requests


def test_unknown_image_is_refused_before_connecting(monkeypatch):
    def no_socket(*_a, **_kw):
        raise AssertionError("must not connect")

    monkeypatch.setattr(flash, "create_rfcomm_socket", no_socket)
    with pytest.raises(flash.FlashError, match="not a known official"):
        flash.flash_firmware(MAC, b"definitely not firmware")


def test_image_too_large_for_partition(fake_device, monkeypatch):
    small = bytes.fromhex("0000010000510000100000")  # 4 KB partition
    monkeypatch.setattr(flash.RaceClient, "request",
                        lambda self, c, p=b"", **kw: small if c == flash.CMD_PARTITION_INFO else b"\x00")
    with pytest.raises(flash.FlashError, match="does not fit"):
        flash.flash_firmware(MAC, b"\x11" * 8192)


def test_race_client_frames_and_device_cancel():
    class Sock(FakeSocket):
        def __init__(self, replies):
            super().__init__()
            self.replies = list(replies)

        def recv(self, _size):
            return self.replies.pop(0)

    ok = bytes([0x15, flash.KIND_RESPONSE, 3, 0]) + flash.CMD_QUERY_STATE.to_bytes(2, "little") + b"\x00"
    client = flash.RaceClient(Sock([ok[:3], ok[3:]]))
    assert client.request(flash.CMD_QUERY_STATE, b"\x00") == b"\x00"

    cancelled = bytes([0x15, flash.KIND_INDICATION, 5, 0]) + (0x1C03).to_bytes(2, "little") + b"\x00\x00\x07"
    client = flash.RaceClient(Sock([cancelled]))
    with pytest.raises(flash.FlashError, match="reason code 7"):
        client.request(flash.CMD_QUERY_STATE, b"\x00")
