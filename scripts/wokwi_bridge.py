"""
Wokwi Serial Bridge (RFC2217 TCP port 4000) <-> FastAPI Backend (port 8000).

Allows bidirectional control and live telemetry between Wokwi VS Code Free
(where Wokwi virtual Wi-Fi host.wokwi.internal requires a Wokwi Club plan)
and the Frutiger Aqua Web Control Center -> MongoDB Atlas + Datadog.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time

import requests


TELEMETRY_PREFIX = "@@TELEMETRY@@"
HUMAN_LINE_RE = re.compile(
    r"pH:\s*([\d.]+)\s*\|\s*TDS:\s*([\d.]+)\s*ppm\s*\|\s*Nhiệt độ:\s*([-\d.]+)\s*°C\s*\|\s*Mực nước:\s*([\d.]+)%\s*\|\s*Lưu lượng lọc:\s*([\d.]+)"
)
DEFAULT_WOKWI_HOST = os.getenv("WOKWI_HOST", "127.0.0.1")
DEFAULT_WOKWI_PORT = int(os.getenv("WOKWI_PORT", "4000"))
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TANK_ID = "AQUA-TANK-01"


class Rfc2217StreamDecoder:
    """Strip Telnet/RFC2217 IAC (0xFF) negotiation sequences from TCP UART data."""

    def __init__(self) -> None:
        self._state = "data"

    def feed(self, chunk: bytes) -> bytes:
        out = bytearray()
        for byte in chunk:
            if self._state == "data":
                if byte == 0xFF:
                    self._state = "iac"
                else:
                    out.append(byte)
            elif self._state == "iac":
                if byte == 0xFF:
                    out.append(0xFF)
                    self._state = "data"
                elif byte == 0xFA:  # SB (Subnegotiation Begin)
                    self._state = "sb"
                elif byte in (0xFB, 0xFC, 0xFD, 0xFE):  # WILL/WONT/DO/DONT
                    self._state = "opt"
                else:
                    self._state = "data"
            elif self._state == "opt":
                self._state = "data"
            elif self._state == "sb":
                if byte == 0xFF:
                    self._state = "sb_iac"
            elif self._state == "sb_iac":
                if byte == 0xF0:  # SE (Subnegotiation End)
                    self._state = "data"
                elif byte != 0xFF:
                    self._state = "sb"
        return bytes(out)


def fetch_control_command(session: requests.Session, backend_url: str) -> str | None:
    """Poll FastAPI simulator state and build the Serial CMD line for ESP32."""
    try:
        resp = session.get(f"{backend_url}/api/simulator/state", timeout=2.0)
        resp.raise_for_status()
        state = resp.json()
        fault_active = bool(state.get("faults", {}).get(TANK_ID))
        bubbler_on = bool(state.get("actuators", {}).get("bubbler_on", True))
        return f"CMD:FAULT={1 if fault_active else 0},BUBBLER={1 if bubbler_on else 0}\n"
    except requests.RequestException as exc:
        print(f"[WARN] Không lấy được lệnh từ Backend ({backend_url}): {exc}", flush=True)
        return None


def parse_telemetry_line(line: str) -> dict | None:
    """Parse either human-readable [BỂ CÁ TANK-01] lines or legacy @@TELEMETRY@@ JSON."""
    idx = line.find(TELEMETRY_PREFIX)
    if idx >= 0:
        raw_json = line[idx + len(TELEMETRY_PREFIX) :].strip()
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            print(f"[WARN] JSON từ ESP32 bị lỗi: {exc} | line={raw_json[:120]}", flush=True)
            return None

    match = HUMAN_LINE_RE.search(line)
    if not match:
        return None

    ph, ec_ppm, water_temp, water_level_pct, pump_flow_lpm = (float(v) for v in match.groups())
    return {
        "readings": [
            {
                "sensor": {
                    "id": TANK_ID,
                    "zone": "Living Room 1F",
                    "crop": "Neon Tetra & Guppy",
                    "system_type": "Canister Bio-Filter",
                },
                "ph": ph,
                "ec_ppm": round(ec_ppm),
                "water_temp": water_temp,
                "water_level_pct": water_level_pct,
                "pump_flow_lpm": pump_flow_lpm,
            }
        ]
    }


def forward_telemetry(session: requests.Session, backend_url: str, payload: dict) -> None:
    """POST parsed telemetry payload to FastAPI ingest endpoint."""
    readings = payload.get("readings", [])
    reading = readings[0] if readings else {}
    ph = float(reading.get("ph", 6.5))
    flow = float(reading.get("pump_flow_lpm", 4.5))
    is_critical = flow < 1.0 or ph > 7.6 or ph < 5.0
    status_label = "🔴 CẢNH BÁO!" if is_critical else "🟢 BÌNH THƯỜNG"

    try:
        resp = session.post(f"{backend_url}/api/telemetry/ingest", json=payload, timeout=3.0)
        print(
            f"✅ [Đã gửi lên Web, MongoDB & Datadog | HTTP {resp.status_code}] "
            f"Trạng thái: {status_label} | pH: {ph:.2f} | "
            f"TDS: {reading.get('ec_ppm')} ppm | Nhiệt độ: {reading.get('water_temp')}°C | "
            f"Mực nước: {reading.get('water_level_pct')}% | Bơm lọc: {flow:.2f} L/phút",
            flush=True,
        )
    except requests.RequestException as exc:
        print(f"[ERROR] Không gửi được dữ liệu lên Backend ({backend_url}): {exc}", flush=True)


def run_bridge_session(
    session: requests.Session, host: str, port: int, backend_url: str
) -> None:
    """Connect once to Wokwi RFC2217 server and relay serial <-> backend until disconnect."""
    with socket.create_connection((host, port), timeout=3.0) as sock:
        sock.settimeout(0.25)
        decoder = Rfc2217StreamDecoder()
        text_buffer = ""
        last_cmd_poll = 0.0
        last_sent_cmd = ""
        print(f"[OK] Đã kết nối cầu nối Wokwi tại {host}:{port} <-> Backend {backend_url}", flush=True)

        while True:
            now = time.monotonic()
            if now - last_cmd_poll >= 1.5:
                last_cmd_poll = now
                cmd = fetch_control_command(session, backend_url)
                if cmd is not None:
                    sock.sendall(cmd.encode("ascii"))
                    if cmd != last_sent_cmd:
                        last_sent_cmd = cmd
                        print(f"[Web -> Wokwi] Đồng bộ lệnh xuống ESP32: {cmd.strip()}", flush=True)

            try:
                chunk = sock.recv(4096)
            except TimeoutError:
                continue
            except socket.timeout:
                continue

            if not chunk:
                raise ConnectionResetError("Wokwi simulation đã ngắt kết nối.")

            clean_bytes = decoder.feed(chunk)
            if not clean_bytes:
                continue
            text_buffer += clean_bytes.decode("utf-8", errors="replace")

            while "\n" in text_buffer:
                raw_line, text_buffer = text_buffer.split("\n", 1)
                line = raw_line.strip("\r\n")
                if not line:
                    continue
                payload = parse_telemetry_line(line)
                if payload is not None:
                    forward_telemetry(session, backend_url, payload)
                else:
                    print(f"[ESP32] {line}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge Wokwi Serial (RFC2217) to FastAPI Backend.")
    parser.add_argument("--host", default=DEFAULT_WOKWI_HOST, help="Wokwi RFC2217 host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_WOKWI_PORT, help="Wokwi RFC2217 port (default: 4000)")
    parser.add_argument("--backend", default=DEFAULT_BACKEND_URL, help="FastAPI base URL (default: http://127.0.0.1:8000)")
    args = parser.parse_args()

    backend_url = args.backend.rstrip("/")
    print("=== Frutiger Aqua Wokwi Serial Bridge ===", flush=True)
    print(f"Wokwi TCP : {args.host}:{args.port}", flush=True)
    print(f"Backend   : {backend_url}", flush=True)

    with requests.Session() as session:
        waiting_logged = False
        while True:
            try:
                waiting_logged = False
                run_bridge_session(session, args.host, args.port, backend_url)
            except (ConnectionRefusedError, ConnectionResetError, OSError) as exc:
                if not waiting_logged:
                    print(
                        f"[WAIT] Đang chờ Wokwi Simulator mở cổng {args.host}:{args.port} "
                        f"({exc}). Hãy bấm Start Simulation trong VS Code...",
                        flush=True,
                    )
                    waiting_logged = True
                time.sleep(1.5)
            except KeyboardInterrupt:
                print("\nĐã dừng cầu nối Wokwi.", flush=True)
                return 0


if __name__ == "__main__":
    sys.exit(main())
