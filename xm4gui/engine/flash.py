"""Official firmware flasher for the WH-1000XM4 over Bluetooth RFCOMM.

The protocol is ported unchanged from tools/flash_firmware.py of
randwardatake/wh1000xm4-anc-optimizer (GPL-3.0-or-later): Sony MDR on channel 11
switches the headset into FOTA mode, then Airoha RACE on channel 21 erases and
programs the FOTA partition, asks the device to check integrity and commits.
Only the reporting changed: progress and log callbacks instead of print, and a
cancel event honoured until the commit.
"""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

from xm4_optimizer.firmware import KnownFirmware, identify_firmware
from xm4_optimizer.transport.rfcomm_socket import create_rfcomm_socket

from .events import Progress, Reporter

MDR_CHANNEL = 11
RACE_CHANNEL = 21

HEAD = 0x15
CMD_START = 0x1C08
CMD_TRANSMIT_INTERVAL = 0x1C1C
CMD_PARTITION_INFO = 0x1C00
CMD_QUERY_STATE = 0x1C04
CMD_ACTIVE_FOTA = 0x1C19
CMD_START_TRANSACTION = 0x1C0A
CMD_WRITE_STATE = 0x1C06
CMD_ERASE = 0x0404
CMD_PAGE_PROGRAM = 0x0402
CMD_CHECK_INTEGRITY = 0x1C01
CMD_COMMIT = 0x1C02
CMD_CANCELLED_BY_DEVICE = 0x1C03

KIND_COMMAND = 0x5A
KIND_RESPONSE = 0x5B
KIND_INDICATION = 0x5D

COMPLETED_BY_INDICATION = {
    CMD_START,
    CMD_TRANSMIT_INTERVAL,
    CMD_ACTIVE_FOTA,
    CMD_ERASE,
    CMD_CHECK_INTEGRITY,
}

BLOCK_SIZE = 4096
PAGE_SIZE = 256

MDR_INIT = bytes.fromhex("3e010000000000013c")
MDR_FOTA_ON = bytes.fromhex("3e0e000000000444010200593c")
MDR_FOTA_OFF = bytes.fromhex("3e0e0100000004440102015b3c")


class FlashError(RuntimeError):
    pass


@dataclass(frozen=True)
class FlashResult:
    firmware: Optional[KnownFirmware]
    size: int
    pages_written: int
    seconds: float


def parse_partition_info(payload: bytes) -> tuple[int, int, int, int]:
    """Return (partition ID, storage type, start address, length) from 0x1C00."""
    if len(payload) < 11 or payload[0] != 0:
        raise ValueError(f"Invalid FOTA partition response: {payload.hex()}")
    partition_id = payload[1]
    storage_type = payload[2]
    start_address = int.from_bytes(payload[3:7], "little")
    length = int.from_bytes(payload[7:11], "little")
    if length == 0 or start_address % BLOCK_SIZE or length % BLOCK_SIZE:
        raise ValueError(f"Invalid FOTA partition bounds: {payload.hex()}")
    return partition_id, storage_type, start_address, length


def page_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    res = 0
    for i in range(8):
        if (crc >> i) & 1:
            res |= 1 << (7 - i)
    return res


class RaceClient:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buf = bytearray()

    def send_cmd(self, cmd_id: int, payload: bytes = b"", head: int = HEAD):
        length = 2 + len(payload)
        pkt = bytearray([head, KIND_COMMAND, length & 0xFF, (length >> 8) & 0xFF])
        pkt.extend([cmd_id & 0xFF, (cmd_id >> 8) & 0xFF])
        pkt.extend(payload)
        self.sock.sendall(pkt)

    def read_packet(self, timeout=5.0):
        self.sock.settimeout(timeout)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if len(self.buf) >= 4:
                length = self.buf[2] | (self.buf[3] << 8)
                if len(self.buf) >= 4 + length:
                    raw = self.buf[: 4 + length]
                    self.buf = self.buf[4 + length :]
                    pkt_id = raw[4] | (raw[5] << 8)
                    return raw[0], raw[1], pkt_id, bytes(raw[6:])
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionResetError("Socket closed by remote device")
            self.buf.extend(chunk)
        raise TimeoutError("Timeout waiting for RACE packet")

    def request(self, cmd_id: int, payload: bytes = b"", head: int = HEAD, timeout=5.0):
        self.send_cmd(cmd_id, payload, head)
        target_kind = KIND_INDICATION if cmd_id in COMPLETED_BY_INDICATION else KIND_RESPONSE
        start_time = time.time()
        while time.time() - start_time < timeout:
            _head, kind, pkt_id, res_payload = self.read_packet(timeout)
            if pkt_id == CMD_CANCELLED_BY_DEVICE:
                reason = res_payload[2] if len(res_payload) > 2 else "unknown"
                raise FlashError(f"Headphones cancelled the update (reason code {reason})")
            if pkt_id != cmd_id:
                continue
            if kind == KIND_RESPONSE and len(res_payload) > 0 and res_payload[0] != 0:
                raise FlashError(f"RACE error for cmd 0x{cmd_id:04x}: status 0x{res_payload[0]:02x}")
            if kind == target_kind:
                return res_payload
        raise TimeoutError(f"Timed out waiting for reply to 0x{cmd_id:04x}")


def mdr_worker(s_mdr: socket.socket, stop_event: threading.Event):
    """Acknowledges MDR packets so the headset stays in FOTA mode."""
    s_mdr.settimeout(1.0)
    while not stop_event.is_set():
        try:
            data = s_mdr.recv(1024)
            if not data:
                break
            for i in range(len(data)):
                if data[i] == 0x3E and i + 2 < len(data) and data[i + 1] in (0x0C, 0x0E, 0x00):
                    seq = data[i + 2]
                    ack_seq = 1 - (seq & 1)
                    s_mdr.sendall(bytes([0x3E, 0x01, ack_seq, 0, 0, 0, 0, 1 + ack_seq, 0x3C]))
        except (socket.timeout, TimeoutError):
            continue
        except Exception:
            break


def check_image(fw_bytes: bytes, allow_unknown: bool = False) -> Optional[KnownFirmware]:
    """Returns the identified official image, or raises unless unknown images are allowed."""
    known = identify_firmware(fw_bytes)
    if known is None and not allow_unknown:
        raise FlashError("This file is not a known official WH-1000XM4 firmware image")
    return known


def flash_firmware(bd_addr: str, fw_bytes: bytes, report: Optional[Reporter] = None,
                   allow_unknown: bool = False) -> FlashResult:
    """Uploads a signed Sony firmware image and commits it. Blocks for several minutes."""
    report = report or Reporter()
    log = report.log
    fw_len = len(fw_bytes)
    known = check_image(fw_bytes, allow_unknown)
    if known is not None:
        log(f"Identified: official {known.model} ({known.model_id}) firmware {known.version}, {fw_len:,} bytes")
    else:
        log(f"WARNING: unknown firmware image ({fw_len:,} bytes), flashing because the override is enabled")

    report.check_cancel()
    report.progress(Progress("connect", 0, 1))
    log(f"Connecting to MDR on RFCOMM channel {MDR_CHANNEL}...")
    s_mdr = create_rfcomm_socket(bd_addr, MDR_CHANNEL, timeout_s=5.0)
    s_race = None
    stop_event = threading.Event()
    try:
        s_mdr.recv(1024)
        s_mdr.sendall(MDR_INIT)
        log("Switching the headset to FOTA update mode...")
        s_mdr.sendall(MDR_FOTA_ON)
        s_mdr.recv(1024)
        threading.Thread(target=mdr_worker, args=(s_mdr, stop_event), daemon=True).start()

        log(f"Connecting to RACE on RFCOMM channel {RACE_CHANNEL}...")
        s_race = create_rfcomm_socket(bd_addr, RACE_CHANNEL, timeout_s=5.0)
        race = RaceClient(s_race)

        log("Starting FOTA session...")
        race.request(CMD_START, bytes([0x01]))
        try:
            race.request(CMD_TRANSMIT_INTERVAL, bytes([0x01, 0x00]), timeout=2.0)
        except Exception:
            pass

        part_info = race.request(CMD_PARTITION_INFO, bytes([0x00]))
        partition_id, storage, base, part_len = parse_partition_info(part_info)
        log(f"FOTA partition: id={partition_id} storage={storage} address=0x{base:08X} length=0x{part_len:X}")
        if fw_len > part_len:
            raise FlashError(f"Firmware ({fw_len} bytes) does not fit the FOTA partition ({part_len} bytes)")
        report.progress(Progress("connect", 1, 1))

        race.request(CMD_QUERY_STATE, bytes([0x00]))
        race.request(CMD_ACTIVE_FOTA, bytes([0x00]))
        race.request(CMD_START_TRANSACTION)
        race.request(CMD_WRITE_STATE, (0x0200).to_bytes(2, "little"))

        # Erase: storage, u32 block length, u32 absolute address, one 4 KB block per command
        total_blocks = (fw_len + BLOCK_SIZE - 1) // BLOCK_SIZE
        log(f"Erasing {total_blocks} blocks ({total_blocks * 4} KB) of the FOTA partition...")
        for b_idx in range(total_blocks):
            report.check_cancel()
            b_addr = base + b_idx * BLOCK_SIZE
            erase_payload = bytearray([storage])
            erase_payload.extend(BLOCK_SIZE.to_bytes(4, "little"))
            erase_payload.extend(b_addr.to_bytes(4, "little"))
            race.request(CMD_ERASE, erase_payload, timeout=10.0)
            report.progress(Progress("erase", b_idx + 1, total_blocks))

        race.request(CMD_WRITE_STATE, (0x0201).to_bytes(2, "little"))
        race.request(CMD_WRITE_STATE, (0x0210).to_bytes(2, "little"))

        # Program: storage, 1 page, crc8, u32 absolute address, 256 data bytes
        total_pages = (fw_len + PAGE_SIZE - 1) // PAGE_SIZE
        log(f"Writing {total_pages:,} pages ({fw_len / 1024:.1f} KB)...")
        t0 = time.time()
        written_pages = 0
        for p_idx in range(total_pages):
            report.check_cancel()
            p_addr = p_idx * PAGE_SIZE
            chunk = fw_bytes[p_addr : p_addr + PAGE_SIZE]
            if len(chunk) < PAGE_SIZE:
                chunk = chunk.ljust(PAGE_SIZE, b"\xFF")
            if chunk != b"\xFF" * PAGE_SIZE:
                prog_payload = bytearray([storage, 1, page_crc(chunk)])
                prog_payload.extend((base + p_addr).to_bytes(4, "little"))
                prog_payload.extend(chunk)
                for attempt in range(3):
                    try:
                        race.request(CMD_PAGE_PROGRAM, prog_payload, timeout=8.0)
                        break
                    except TimeoutError:
                        if attempt == 2:
                            raise
                        time.sleep(0.05)
                written_pages += 1
            elapsed = max(time.time() - t0, 0.001)
            report.progress(Progress("program", p_idx + 1, total_pages, (p_idx + 1) * PAGE_SIZE / elapsed))
        seconds = time.time() - t0
        log(f"Written in {seconds:.1f}s ({fw_len / 1024 / max(seconds, 0.001):.1f} KB/s)")

        report.check_cancel()
        report.progress(Progress("verify", 0, 1))
        log("Asking the headset to check firmware integrity...")
        race.request(CMD_CHECK_INTEGRITY, bytes([0x01, 0x00, storage]), timeout=20.0)
        log("Integrity check passed.")
        report.progress(Progress("verify", 1, 1))

        # Last point where cancelling leaves the running firmware untouched.
        report.check_cancel()
        race.request(CMD_WRITE_STATE, (0x0211).to_bytes(2, "little"))
        report.progress(Progress("commit", 0, 1))
        log("Committing firmware update...")
        try:
            race.request(CMD_COMMIT, bytes([0x00]), timeout=5.0)
        except (ConnectionResetError, TimeoutError, BrokenPipeError, OSError):
            log("Headset is rebooting.")
        report.progress(Progress("commit", 1, 1))
        log("Commit accepted; the headset will reconnect with the new firmware.")
        return FlashResult(known, fw_len, written_pages, seconds)
    finally:
        stop_event.set()
        if s_race is not None:
            try:
                s_race.close()
            except Exception:
                pass
        try:
            s_mdr.sendall(MDR_FOTA_OFF)
            s_mdr.close()
        except Exception:
            pass
