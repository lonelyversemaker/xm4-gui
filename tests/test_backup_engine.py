import hashlib
import struct
import threading

import pytest

from xm4gui.engine import backup
from xm4gui.engine.events import Cancelled, Reporter

MAC = "00:11:22:33:44:55"


class FakeRace:
    """Answers pipelined RACE page reads with 270-byte frames holding a deterministic pattern."""

    def __init__(self, error_at=None):
        self.pending = bytearray()
        self.error_at = error_at

    def settimeout(self, _t):
        pass

    def sendall(self, data):
        for off in range(0, len(data), 12):
            addr = struct.unpack_from("<I", data, off + 8)[0]
            code = 1 if addr == self.error_at else 0
            self.pending += bytes([0x05, 0x5B, 0x0A, 0x01, 0x03, 0x04, code]) + bytes(7) + page(addr)

    def recv(self, size):
        out, self.pending = bytes(self.pending[:size]), self.pending[size:]
        return out

    def close(self):
        pass


class FakeMdr:
    def __init__(self):
        self.sent = []

    def recv(self, _size):
        return b"\x00"

    def sendall(self, data):
        self.sent.append(bytes(data))

    def close(self):
        pass


def page(addr):
    head = b"NVDM" if addr == 0 else b""
    return (head + bytes([(addr >> 8) & 0xFF]) * 256)[:256]


@pytest.fixture
def sockets(monkeypatch):
    made = {}

    def factory(_mac, channel, timeout_s=5.0):
        made[channel] = FakeMdr() if channel == backup.MDR_CHANNEL else made.get("race") or FakeRace()
        return made[channel]

    monkeypatch.setattr(backup, "create_rfcomm_socket", factory)
    return made


def test_backup_writes_file_and_sidecar(sockets, tmp_path):
    events = []
    out = tmp_path / "nvdm.bin"
    result = backup.backup_nvdm(MAC, out, Reporter(progress=events.append), peb_count=3)

    data = out.read_bytes()
    assert len(data) == 3 * backup.PEB_SIZE == result.size
    assert data == b"".join(page(a) for a in range(0, 3 * backup.PEB_SIZE, backup.PAGE_SIZE))
    assert result.magic_valid
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    assert (tmp_path / "nvdm.bin.sha256").read_text() == f"{result.sha256}  nvdm.bin\n"
    assert [e.done for e in events if e.stage == "backup"] == [1, 2, 3]
    assert sockets[backup.MDR_CHANNEL].sent[-1] == backup.MDR_FOTA_OFF


def test_read_error_is_reported(sockets, monkeypatch):
    sockets["race"] = FakeRace(error_at=backup.PEB_SIZE + 2 * backup.PAGE_SIZE)
    with pytest.raises(backup.BackupError, match="block 1 page 2"):
        backup.read_nvdm(MAC, peb_count=2)


def test_cancel_stops_without_writing(sockets, tmp_path):
    cancel = threading.Event()

    def progress(p):
        if p.stage == "backup":
            cancel.set()

    out = tmp_path / "nvdm.bin"
    with pytest.raises(Cancelled):
        backup.backup_nvdm(MAC, out, Reporter(progress=progress, cancel=cancel), peb_count=4)
    assert not out.exists()
    assert sockets[backup.MDR_CHANNEL].sent[-1] == backup.MDR_FOTA_OFF
