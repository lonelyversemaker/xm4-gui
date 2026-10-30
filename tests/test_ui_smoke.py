import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("XM4GUI_LANG", "en")

import pytest
from xm4_optimizer.firmware import KnownFirmware

from xm4gui.engine import device
from xm4gui.engine.events import Progress
from xm4gui.ui import main_window
from xm4gui.ui.workers import Worker

MAC = "00:11:22:33:44:55"


def status(battery=80, firmware="2.5.0"):
    return device.HeadsetStatus(MAC, firmware, battery, False)


@pytest.fixture
def window(qtbot, monkeypatch):
    monkeypatch.setattr(device, "list_devices", lambda: [(MAC, "WH-1000XM4")])
    monkeypatch.setattr(device, "read_status", lambda mac: status())
    w = main_window.MainWindow()
    qtbot.addWidget(w)
    qtbot.waitUntil(lambda: w.busy is None and w.status is not None, timeout=5000)
    return w


def known_file(tmp_path, monkeypatch, version):
    monkeypatch.setattr(main_window, "identify_firmware",
                        lambda data: KnownFirmware("MDRID294300", "WH-1000XM4", version, len(data)) if data.startswith(b"OK") else None)
    path = tmp_path / "fw.bin"
    path.write_bytes(b"OK" + bytes(1000))
    return path


def test_status_is_shown(window):
    assert window.fw_label.text() == "2.5.0"
    assert window.battery_label.text() == "80%"
    assert "XX:XX:XX" in window.device_combo.currentText()


def test_flash_button_follows_file_identity(window, tmp_path, monkeypatch):
    assert not window.flash_btn.isEnabled()
    window.load_firmware(known_file(tmp_path, monkeypatch, "2.6.0"))
    assert window.flash_btn.isEnabled()
    assert "2.6.0" in window.identity_label.text()

    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"nope")
    window.load_firmware(bad)
    assert not window.flash_btn.isEnabled()
    assert "Unknown" in window.identity_label.text()


def test_low_battery_blocks_flash(window, tmp_path, monkeypatch):
    window.status = status(battery=30)
    window.load_firmware(known_file(tmp_path, monkeypatch, "2.6.0"))
    assert not window.flash_btn.isEnabled()
    assert "✗" in window.checks["check_battery"].text()


def test_same_version_is_only_a_warning(window, tmp_path, monkeypatch):
    window.load_firmware(known_file(tmp_path, monkeypatch, "2.5.0"))
    assert window.flash_btn.isEnabled()
    assert "!" in window.checks["check_version"].text()


def test_progress_disables_cancel_at_commit(window):
    window.busy = "flash"
    window._on_progress(Progress("program", 50, 100, 2700))
    assert window.progress_bar.value() == 500
    assert "Step 3/6" in window.stage_label.text()
    assert window.cancel_btn.isEnabled()
    window._on_progress(Progress("commit", 0, 1))
    assert not window.cancel_btn.isEnabled()
    window.busy = None


def test_worker_forwards_signals(qtbot):
    def fn(report):
        report.log("hello")
        report.progress(Progress("backup", 1, 2))
        return 42

    worker = Worker(fn)
    logs, progress = [], []
    worker.log.connect(logs.append)
    worker.progress.connect(progress.append)
    with qtbot.waitSignal(worker.succeeded, timeout=3000) as blocker:
        worker.start()
    worker.wait()
    assert blocker.args == [42]
    assert logs == ["hello"] and progress[0].done == 1


def test_worker_reports_failure(qtbot):
    worker = Worker(lambda report: 1 / 0)
    with qtbot.waitSignal(worker.failed, timeout=3000) as blocker:
        worker.start()
    worker.wait()
    assert "division" in blocker.args[0]
