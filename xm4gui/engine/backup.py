"""NVDM calibration backup for the WH-1000XM4.

Ported from tools/backup_nvdm.py of randwardatake/wh1000xm4-anc-optimizer
(GPL-3.0-or-later). The 512 KB Airoha NVDM store (per-unit acoustic trims, ANC
coefficients and pairing records) is read page by page over RACE after the MDR
FOTA handshake. The file is private: it contains pairing keys.
"""

from __future__ import annotations

import hashlib
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from xm4_optimizer.transport.rfcomm_socket import create_rfcomm_socket

from .events import Progress, Reporter
from .flash import MDR_CHANNEL, MDR_FOTA_OFF, MDR_FOTA_ON, MDR_INIT, RACE_CHANNEL

TOTAL_PEBS = 128
PAGES_PER_PEB = 16
PAGE_SIZE = 256
PEB_SIZE = PAGES_PER_PEB * PAGE_SIZE  # 4096 bytes
TOTAL_SIZE = TOTAL_PEBS * PEB_SIZE    # 524,288 bytes
FRAME_SIZE = 270                      # RACE read reply: 14 header bytes + 256 data bytes


class BackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupResult:
    path: Path
    size: int
    sha256: str
    magic_valid: bool
    seconds: float


def read_nvdm(bd_addr: str, report: Optional[Reporter] = None, peb_count: int = TOTAL_PEBS) -> bytes:
    report = report or Reporter()
    log = report.log
    report.check_cancel()
    report.progress(Progress("connect", 0, 1))
    log(f"Connecting to MDR on RFCOMM channel {MDR_CHANNEL}...")
    s_mdr = None
    s_race = None
    try:
        try:
            s_mdr = create_rfcomm_socket(bd_addr, MDR_CHANNEL, timeout_s=5.0)
            try:
                s_mdr.recv(1024)
            except Exception:
                pass
            s_mdr.sendall(MDR_INIT)
            s_mdr.sendall(MDR_FOTA_ON)
            try:
                s_mdr.recv(1024)
            except Exception:
                pass
            log("Headset switched to update mode.")
        except Exception as e:
            log(f"Warning: MDR handshake failed ({e}); trying RACE directly")

        log(f"Connecting to RACE on RFCOMM channel {RACE_CHANNEL}...")
        s_race = create_rfcomm_socket(bd_addr, RACE_CHANNEL, timeout_s=4.0)
        report.progress(Progress("connect", 1, 1))

        dump = bytearray()
        t0 = time.time()
        for peb_idx in range(peb_count):
            report.check_cancel()
            # Pipeline 16 page reads for this 4 KB block
            batch = bytearray()
            for pg in range(PAGES_PER_PEB):
                addr = peb_idx * PEB_SIZE + pg * PAGE_SIZE
                payload = struct.pack("<BBI", 1, 1, addr)  # storage=1 (NVDM), count=1, addr
                batch.extend(struct.pack("<BBHH", 0x05, 0x5A, 2 + len(payload), 0x0403) + payload)
            s_race.sendall(batch)

            resp = bytearray()
            expected = PAGES_PER_PEB * FRAME_SIZE
            while len(resp) < expected:
                chunk = s_race.recv(expected - len(resp))
                if not chunk:
                    raise ConnectionResetError("RACE connection closed by headset")
                resp.extend(chunk)

            for pg in range(PAGES_PER_PEB):
                frame = resp[pg * FRAME_SIZE : (pg + 1) * FRAME_SIZE]
                if frame[6] != 0:
                    raise BackupError(f"RACE read error at block {peb_idx} page {pg}: code 0x{frame[6]:02X}")
                dump.extend(frame[14:FRAME_SIZE])

            elapsed = max(time.time() - t0, 0.001)
            report.progress(Progress("backup", peb_idx + 1, peb_count, len(dump) / elapsed))
        log(f"Read {len(dump) // 1024} KB in {time.time() - t0:.1f}s")
        return bytes(dump)
    finally:
        if s_race is not None:
            try:
                s_race.close()
            except Exception:
                pass
        if s_mdr is not None:
            try:
                s_mdr.sendall(MDR_FOTA_OFF)
                s_mdr.close()
            except Exception:
                pass


def backup_nvdm(bd_addr: str, output_path: Path, report: Optional[Reporter] = None,
                peb_count: int = TOTAL_PEBS) -> BackupResult:
    """Dumps NVDM to output_path and writes a .sha256 file next to it."""
    report = report or Reporter()
    t0 = time.time()
    data = read_nvdm(bd_addr, report, peb_count)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    sha256 = hashlib.sha256(data).hexdigest()
    output_path.with_name(output_path.name + ".sha256").write_text(f"{sha256}  {output_path.name}\n", encoding="utf-8")
    magic_valid = data[:4] == b"NVDM"
    report.log(f"Saved {output_path} (SHA-256 {sha256}); header {'NVDM' if magic_valid else 'UNKNOWN'}")
    return BackupResult(output_path, len(data), sha256, magic_valid, time.time() - t0)
