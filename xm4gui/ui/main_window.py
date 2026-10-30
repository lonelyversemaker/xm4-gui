"""Main window: headset status and the backup/flash workflow."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QToolButton,
    QVBoxLayout, QWidget,
)

from xm4_optimizer.firmware import KnownFirmware, identify_firmware

from ..engine import device
from ..engine.backup import backup_nvdm
from ..engine.events import Progress, Reporter, mask_mac
from ..engine.flash import FlashResult, flash_firmware
from ..engine.keepawake import KeepAwake
from .strings import format_duration, t
from .workers import Worker

MIN_BATTERY = 50
FLASH_STAGES = ["connect", "erase", "program", "verify", "commit", "reconnect"]
# Throughput measured on a real headset (~2.7 KB/s), used for the time estimate in the dialog.
EXPECTED_KB_PER_S = 2.7


def short_mac(mac: str) -> str:
    return mask_mac(mac)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("app_title"))
        self.setAcceptDrops(True)
        self.setMinimumWidth(560)

        self.devices: list[tuple[str, str]] = []
        self.status: Optional[device.HeadsetStatus] = None
        self.fw_path: Optional[Path] = None
        self.fw_bytes: Optional[bytes] = None
        self.fw_known: Optional[KnownFirmware] = None
        self.backup_done = False
        self.worker: Optional[Worker] = None
        self.busy: Optional[str] = None
        self.log_lines: list[str] = []

        central = QWidget()
        root = QVBoxLayout(central)
        root.addWidget(self._build_headset_box())
        root.addWidget(self._build_update_box())
        root.addWidget(self._build_log_box(), 1)
        self.setCentralWidget(central)

        self._update_controls()
        self.refresh()

    # ---------- layout ----------

    def _build_headset_box(self) -> QGroupBox:
        box = QGroupBox(t("headset"))
        lay = QVBoxLayout(box)
        row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_selected)
        self.refresh_btn = QPushButton(t("refresh"))
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.device_combo, 1)
        row.addWidget(self.refresh_btn)
        lay.addLayout(row)

        form = QFormLayout()
        self.fw_label = QLabel(t("unknown"))
        self.battery_label = QLabel(t("unknown"))
        form.addRow(t("firmware") + ":", self.fw_label)
        form.addRow(t("battery") + ":", self.battery_label)
        lay.addLayout(form)

        self.headset_msg = QLabel()
        self.headset_msg.setWordWrap(True)
        self.headset_msg.setStyleSheet("color: palette(placeholder-text);")
        self.headset_msg.setVisible(False)
        lay.addWidget(self.headset_msg)
        return box

    def _build_update_box(self) -> QGroupBox:
        box = QGroupBox(t("update"))
        lay = QVBoxLayout(box)

        self.backup_btn = QPushButton(t("backup"))
        self.backup_btn.setToolTip(t("backup_tip"))
        self.backup_btn.clicked.connect(self._start_backup)
        lay.addWidget(self.backup_btn)

        row = QHBoxLayout()
        self.choose_btn = QPushButton(t("choose_fw"))
        self.choose_btn.clicked.connect(self._choose_firmware)
        row.addWidget(self.choose_btn)
        hint = QLabel(t("drop_hint"))
        hint.setStyleSheet("color: palette(placeholder-text);")
        row.addWidget(hint, 1)
        lay.addLayout(row)

        where = QLabel(f'<a href="{t("where_fw_url")}">{t("where_fw")}</a>')
        where.setOpenExternalLinks(True)
        lay.addWidget(where)

        self.file_label = QLabel(t("fw_none"))
        self.file_label.setWordWrap(True)
        self.identity_label = QLabel()
        bold = QFont()
        bold.setBold(True)
        self.identity_label.setFont(bold)
        lay.addWidget(self.file_label)
        lay.addWidget(self.identity_label)

        self.checks: dict[str, QLabel] = {}
        for key in ("check_connected", "check_battery", "check_file", "check_version", "check_backup"):
            label = QLabel()
            self.checks[key] = label
            lay.addWidget(label)

        self.allow_unknown = QCheckBox(t("allow_unknown"))
        self.allow_unknown.setStyleSheet("color: #c0392b;")
        self.allow_unknown.clicked.connect(self._on_allow_unknown)
        lay.addWidget(self.allow_unknown)

        row = QHBoxLayout()
        self.flash_btn = QPushButton(t("flash"))
        self.flash_btn.setDefault(True)
        self.flash_btn.clicked.connect(self._start_flash)
        self.cancel_btn = QPushButton(t("cancel"))
        self.cancel_btn.clicked.connect(self._cancel)
        row.addWidget(self.flash_btn, 1)
        row.addWidget(self.cancel_btn)
        lay.addLayout(row)

        self.stage_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setTextVisible(False)
        self.eta_label = QLabel()
        self.eta_label.setStyleSheet("color: palette(placeholder-text);")
        lay.addWidget(self.stage_label)
        lay.addWidget(self.progress_bar)
        lay.addWidget(self.eta_label)
        self._reset_progress()
        return box

    def _build_log_box(self) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.log_toggle = QToolButton()
        self.log_toggle.setText(t("log"))
        self.log_toggle.setCheckable(True)
        self.log_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.log_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.log_toggle.toggled.connect(self._toggle_log)
        save = QPushButton(t("save_log"))
        save.clicked.connect(self._save_log)
        row.addWidget(self.log_toggle)
        row.addStretch(1)
        row.addWidget(save)
        lay.addLayout(row)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.log_view.setVisible(False)
        lay.addWidget(self.log_view, 1)
        return wrap

    # ---------- state ----------

    @property
    def mac(self) -> Optional[str]:
        idx = self.device_combo.currentIndex()
        return self.devices[idx][0] if 0 <= idx < len(self.devices) else None

    def _flash_blockers(self) -> list[str]:
        problems = []
        if self.status is None:
            problems.append("check_connected")
        elif self.status.battery < MIN_BATTERY:
            problems.append("check_battery")
        if self.fw_bytes is None or (self.fw_known is None and not self.allow_unknown.isChecked()):
            problems.append("check_file")
        return problems

    def _update_controls(self) -> None:
        idle = self.busy is None
        connected = self.status is not None
        self.refresh_btn.setEnabled(idle)
        self.device_combo.setEnabled(idle)
        self.backup_btn.setEnabled(idle and connected)
        self.choose_btn.setEnabled(idle)
        self.allow_unknown.setEnabled(idle)
        self.flash_btn.setEnabled(idle and not self._flash_blockers())
        self.cancel_btn.setVisible(self.busy in ("flash", "backup"))

        same_version = connected and self.fw_known is not None and self.fw_known.version == self.status.firmware
        marks = {
            "check_connected": (connected, True),
            "check_battery": (connected and self.status.battery >= MIN_BATTERY, True),
            "check_file": (self.fw_bytes is not None and (self.fw_known is not None or self.allow_unknown.isChecked()), True),
            "check_version": (not same_version, False),
            "check_backup": (self.backup_done, False),
        }
        for key, (ok, required) in marks.items():
            sign = "✓" if ok else ("✗" if required else "!")
            color = "#27ae60" if ok else ("#c0392b" if required else "#d68910")
            text = t(key, min=MIN_BATTERY) if key == "check_battery" else t(key)
            if key == "check_version" and same_version:
                text = t("check_same_version")
            self.checks[key].setText(f'<span style="color:{color}">{sign}</span> {text}')

    def _show_status(self) -> None:
        s = self.status
        if s is None:
            for label in (self.fw_label, self.battery_label):
                label.setText(t("unknown"))
            return
        self.fw_label.setText(s.firmware)
        self.battery_label.setText(f"{s.battery}%" + (f" ({t('charging')})" if s.charging else ""))

    # ---------- background work ----------

    def _run(self, kind: str, fn: Callable[[Reporter], object], on_success: Callable[[object], None],
             on_failure: Callable[[str], None], on_cancel: Optional[Callable[[], None]] = None) -> None:
        self.busy = kind
        worker = Worker(fn, self)
        worker.log.connect(self.append_log)
        worker.progress.connect(self._on_progress)
        worker.succeeded.connect(on_success)
        worker.failed.connect(on_failure)
        if on_cancel:
            worker.cancelled.connect(on_cancel)
        worker.finished.connect(self._on_worker_finished)
        self.worker = worker
        self._update_controls()
        worker.start()

    def _on_worker_finished(self) -> None:
        self.busy = None
        self.worker = None
        self._update_controls()

    def append_log(self, text: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        for line in text.splitlines() or [""]:
            entry = f"{stamp}  {line}"
            self.log_lines.append(entry)
            self.log_view.appendPlainText(mask_mac(entry))

    # ---------- headset ----------

    def refresh(self) -> None:
        if self.busy:
            return
        self._headset_message(t("searching"))
        self.status = None
        self._show_status()
        previous = self.mac

        def work(report: Reporter):
            devices = device.list_devices()
            report.log(f"Connected devices: {', '.join(f'{name} ({mac})' for mac, name in devices) or 'none'}")
            macs = [m for m, _ in devices]
            target = previous if previous in macs else next((m for m, n in devices if device.is_xm4_name(n)), None)
            status, error = None, None
            if target:
                try:
                    status = device.read_status(target)
                    report.log(f"Status: firmware {status.firmware}, battery {status.battery}%")
                except Exception as e:
                    error = str(e)
                    report.log(f"Status query failed: {e}")
            return devices, target, status, error

        self._run("status", work, self._on_refreshed, self._on_status_failed)

    def _on_refreshed(self, result) -> None:
        devices, target, status, error = result
        self.devices = devices
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for mac, name in devices:
            self.device_combo.addItem(f"{name}  ({short_mac(mac)})")
        if target:
            self.device_combo.setCurrentIndex([m for m, _ in devices].index(target))
        self.device_combo.blockSignals(False)
        self.status = status
        self._show_status()
        if not devices:
            self._headset_message(t("no_devices"))
        elif error:
            self._headset_message(t("status_failed", error=error))
        elif target is None:
            self._headset_message(t("not_xm4"))
        else:
            self._headset_message("")

    def _headset_message(self, text: str) -> None:
        self.headset_msg.setText(text)
        self.headset_msg.setVisible(bool(text))

    def _on_status_failed(self, error: str) -> None:
        self._headset_message(t("status_failed", error=error))

    def _on_device_selected(self, _index: int) -> None:
        mac = self.mac
        if mac is None or self.busy:
            return
        self.status = None
        self._show_status()

        def work(report: Reporter):
            return self.devices, mac, device.read_status(mac), None

        self._run("status", work, self._on_refreshed, self._on_status_failed)

    # ---------- backup ----------

    def _start_backup(self) -> None:
        mac = self.mac
        if mac is None or self.busy:
            return
        default = Path.home() / f"xm4_nvdm_{datetime.date.today():%Y%m%d}.bin"
        path, _ = QFileDialog.getSaveFileName(self, t("backup_save_title"), str(default), "NVDM (*.bin)")
        if not path:
            return

        def work(report: Reporter):
            with KeepAwake("Backing up headphone calibration"):
                return backup_nvdm(mac, Path(path), report)

        self._run("backup", work, self._on_backup_done, self._on_backup_failed, self._on_cancelled)

    def _on_backup_done(self, result) -> None:
        self._reset_progress()
        if result.magic_valid:
            self.backup_done = True
            QMessageBox.information(self, t("done"), t("backup_done", path=result.path))
        else:
            QMessageBox.warning(self, t("warning"), t("backup_bad_magic"))

    def _on_backup_failed(self, error: str) -> None:
        self._reset_progress()
        QMessageBox.critical(self, t("error"), t("backup_failed", error=error))

    # ---------- firmware ----------

    def _choose_firmware(self) -> None:
        start = str(self.fw_path.parent) if self.fw_path else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, t("choose_fw_title"), start, t("fw_filter"))
        if path:
            self.load_firmware(Path(path))

    def load_firmware(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError as e:
            QMessageBox.critical(self, t("error"), t("fw_read_failed", error=e))
            return
        self.fw_path = path
        self.fw_bytes = data
        self.fw_known = identify_firmware(data)
        self.file_label.setText(f"{path.name}  ({len(data):,} B)")
        if self.fw_known:
            self.identity_label.setText(t("fw_known", model=self.fw_known.model, version=self.fw_known.version))
            self.identity_label.setStyleSheet("color: #27ae60;")
        else:
            self.identity_label.setText(t("fw_unknown"))
            self.identity_label.setStyleSheet("color: #c0392b;")
        self.append_log(f"Selected {path} ({len(data):,} bytes): "
                        f"{'official ' + self.fw_known.version if self.fw_known else 'unknown image'}")
        self._update_controls()

    def _on_allow_unknown(self, checked: bool) -> None:
        if checked:
            answer = QMessageBox.warning(self, t("warning"), t("allow_unknown_confirm"),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                self.allow_unknown.setChecked(False)
        self._update_controls()

    def _start_flash(self) -> None:
        mac = self.mac
        if mac is None or self.busy or self._flash_blockers():
            return
        version = self.fw_known.version if self.fw_known else "?"
        minutes = max(1, round(len(self.fw_bytes) / 1024 / EXPECTED_KB_PER_S / 60))
        text = t("flash_confirm", version=version, minutes=minutes)
        if self.fw_known and self.status and self.fw_known.version == self.status.firmware:
            text += t("flash_same")
        if not self.backup_done:
            text += t("flash_no_backup")
        answer = QMessageBox.question(self, t("flash_confirm_title"), text,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return

        fw_bytes = self.fw_bytes
        allow_unknown = self.allow_unknown.isChecked()

        def work(report: Reporter):
            with KeepAwake():
                result = flash_firmware(mac, fw_bytes, report, allow_unknown=allow_unknown)
                report.progress(Progress("reconnect", 0, 1))
                report.log("Waiting for the headset to reboot and reconnect...")
                try:
                    status = device.wait_for_reconnect(mac, Reporter(log=report.log))
                    report.log(f"Reconnected: firmware {status.firmware}")
                    return result, status, None
                except Exception as e:
                    report.log(f"Reconnect failed: {e}")
                    return result, None, str(e)

        self._run("flash", work, self._on_flash_done, self._on_flash_failed, self._on_cancelled)

    def _on_flash_done(self, outcome) -> None:
        result, status, error = outcome
        self._reset_progress()
        self.status = status
        self._show_status()
        if status is not None:
            QMessageBox.information(self, t("done"), t("flash_done", version=status.firmware))
        else:
            QMessageBox.warning(self, t("warning"), t("flash_done_no_status", error=error))

    def _on_flash_failed(self, error: str) -> None:
        self._reset_progress()
        QMessageBox.critical(self, t("error"), t("flash_failed", error=error))
        self.status = None
        self._show_status()

    def _on_cancelled(self) -> None:
        self._reset_progress()
        QMessageBox.information(self, t("done"), t("cancelled"))

    def _cancel(self) -> None:
        if self.worker is None:
            return
        answer = QMessageBox.question(self, t("cancel"), t("cancel_confirm"),
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes and self.worker is not None:
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    # ---------- progress ----------

    def _reset_progress(self) -> None:
        self.stage_label.setText("")
        self.stage_label.setVisible(False)
        self.eta_label.setText("")
        self.eta_label.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setEnabled(True)

    def _on_progress(self, p: Progress) -> None:
        if self.busy not in ("flash", "backup"):
            return
        self.progress_bar.setVisible(True)
        self.stage_label.setVisible(True)
        self.eta_label.setVisible(True)
        if self.busy == "flash" and p.stage in FLASH_STAGES:
            n = FLASH_STAGES.index(p.stage) + 1
            self.stage_label.setText(t("step", n=n, total=len(FLASH_STAGES), name=t(f"stage_{p.stage}")))
        else:
            self.stage_label.setText(t(f"stage_{p.stage}"))
        if p.stage == "reconnect":
            self.progress_bar.setRange(0, 0)  # busy indicator
        else:
            self.progress_bar.setRange(0, 1000)
            self.progress_bar.setValue(int(p.fraction * 1000))
        # Past this point the update cannot be undone.
        if p.stage in ("commit", "reconnect"):
            self.cancel_btn.setEnabled(False)
        if p.bytes_per_s > 0 and p.total:
            unit = 4096 if p.stage == "backup" else 256
            left = (p.total - p.done) * unit / p.bytes_per_s
            self.eta_label.setText(t("eta", speed=p.bytes_per_s / 1024, left=format_duration(left)))
        else:
            self.eta_label.setText("")

    # ---------- log ----------

    def _toggle_log(self, shown: bool) -> None:
        self.log_view.setVisible(shown)
        self.log_toggle.setArrowType(Qt.ArrowType.DownArrow if shown else Qt.ArrowType.RightArrow)

    def _save_log(self) -> None:
        default = Path.home() / f"xm4_gui_{datetime.datetime.now():%Y%m%d_%H%M%S}.log"
        path, _ = QFileDialog.getSaveFileName(self, t("save_log_title"), str(default), "Log (*.log *.txt)")
        if path:
            Path(path).write_text(mask_mac("\n".join(self.log_lines)) + "\n", encoding="utf-8")

    # ---------- window events ----------

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if self.busy is None and len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.load_firmware(Path(event.mimeData().urls()[0].toLocalFile()))

    def closeEvent(self, event) -> None:
        if self.busy in ("flash", "backup"):
            QMessageBox.warning(self, t("warning"), t("busy_close"))
            event.ignore()
            return
        if self.worker is not None:
            self.worker.wait(5000)
        event.accept()
