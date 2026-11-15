"""
IoT Sensor Simulator for Frutiger Aqua Smart Aquarium Fleet.
Mô phỏng dữ liệu cảm biến bể cá thông minh gửi định kỳ về Backend API.
Hỗ trợ chế độ gây sự cố (Fault Injection) đồng bộ qua Backend API (/api/simulator/state)
và file simulator_control.json phục vụ kịch bản demo Hackathon.
"""

import os
import time
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BASE_URL = os.getenv("BACKEND_BASE_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}")
BACKEND_URL = f"{BASE_URL}/api/telemetry/ingest"
STATE_URL = f"{BASE_URL}/api/simulator/state"

CONTROL_FILE = PROJECT_ROOT / "simulator_control.json"

TANKS = [
    {"id": "AQUA-TANK-01", "zone": "Living Room 1F", "crop": "Neon Tetra & Guppy", "type": "Canister Bio-Filter"},
    {"id": "AQUA-TANK-02", "zone": "Studio 2F", "crop": "Clownfish & Coral", "type": "Sump Protein Skimmer"},
    {"id": "AQUA-TANK-03", "zone": "Balcony Lounge", "crop": "Mini Koi & Moss", "type": "Overflow UV Filter"},
]

state = {
    "AQUA-TANK-01": {"ph": 6.8, "ec": 320.0, "temp": 25.4, "level": 90.0, "flow": 4.5, "fault": None},
    "AQUA-TANK-02": {"ph": 7.1, "ec": 1050.0, "temp": 25.8, "level": 88.0, "flow": 4.2, "fault": None},
    "AQUA-TANK-03": {"ph": 7.0, "ec": 410.0, "temp": 24.6, "level": 92.0, "flow": 4.8, "fault": None},
}


def check_external_control():
    """Đồng bộ trạng thái sự cố từ Backend API (ưu tiên) hoặc simulator_control.json."""
    try:
        res = requests.get(STATE_URL, timeout=1.5)
        if res.status_code == 200:
            faults = res.json().get("faults", {})
            for t_id in state:
                if t_id in faults:
                    state[t_id]["fault"] = faults[t_id]
            return
    except requests.exceptions.RequestException:
        pass

    try:
        with open(CONTROL_FILE, "r", encoding="utf-8") as f:
            cmd = json.load(f)
            target = cmd.get("device_id", "AQUA-TANK-01")
            action = cmd.get("action")
            if target in state:
                if action == "INJECT_FAULT":
                    state[target]["fault"] = "CLOG_AND_PH_DRIFT"
                elif action == "RESOLVE":
                    state[target]["fault"] = None
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def generate_telemetry_batch():
    check_external_control()
    batch = []
    now = datetime.now(timezone.utc)

    for tank in TANKS:
        t_id = tank["id"]
        curr = state[t_id]

        if curr["fault"] == "CLOG_AND_PH_DRIFT":
            # Tắc nghẽn lọc tuần hoàn: Lưu lượng tụt dốc, pH tăng kiềm hóa, mực nước giảm
            curr["flow"] = max(0.2, curr["flow"] - random.uniform(0.5, 0.8))
            curr["ph"] = min(8.3, curr["ph"] + random.uniform(0.25, 0.45))
            curr["level"] = max(15.0, curr["level"] - random.uniform(5.0, 9.0))
            curr["ec"] = min(1400.0, curr["ec"] + random.uniform(25.0, 50.0))
        else:
            target_flow = 4.5 if t_id == "AQUA-TANK-01" else (4.2 if t_id == "AQUA-TANK-02" else 4.8)
            target_ph = 6.8 if t_id == "AQUA-TANK-01" else (7.1 if t_id == "AQUA-TANK-02" else 7.0)
            target_level = 90.0 if t_id == "AQUA-TANK-01" else (88.0 if t_id == "AQUA-TANK-02" else 92.0)
            target_ec = 320.0 if t_id == "AQUA-TANK-01" else (1050.0 if t_id == "AQUA-TANK-02" else 410.0)

            if curr["flow"] < target_flow:
                curr["flow"] = min(target_flow, curr["flow"] + 0.6)
            else:
                curr["flow"] = round(target_flow + random.uniform(-0.15, 0.15), 2)

            if curr["ph"] > target_ph:
                curr["ph"] = max(target_ph, curr["ph"] - 0.35)
            else:
                curr["ph"] = round(target_ph + random.uniform(-0.08, 0.08), 2)

            if curr["level"] < target_level:
                curr["level"] = min(target_level, curr["level"] + 7.0)
            else:
                curr["level"] = round(target_level + random.uniform(-1.0, 1.0), 1)

            if curr["ec"] > target_ec + 25:
                curr["ec"] = max(target_ec, curr["ec"] - 40.0)
            else:
                curr["ec"] = round(target_ec + random.uniform(-10.0, 10.0), 0)

        base_temp = 25.4 if t_id == "AQUA-TANK-01" else (25.8 if t_id == "AQUA-TANK-02" else 24.6)
        curr["temp"] = round(base_temp + random.uniform(-0.3, 0.3), 1)

        point = {
            "ts": now.isoformat(),
            "sensor": {
                "id": t_id,
                "zone": tank["zone"],
                "crop": tank["crop"],
                "system_type": tank["type"],
            },
            "ph": round(curr["ph"], 2),
            "ec_ppm": round(curr["ec"], 0),
            "water_temp": round(curr["temp"], 1),
            "water_level_pct": round(curr["level"], 1),
            "pump_flow_lpm": round(curr["flow"], 2),
        }
        batch.append(point)

    return batch


def run_simulator(interval: float = 2.0):
    print("🐠 Frutiger Aqua Smart Aquarium Simulator bắt đầu chạy...")
    print(f"📡 Endpoint gửi dữ liệu: {BACKEND_URL}")
    print(f"⏱️  Tần suất gửi: mỗi {interval} giây\n")

    while True:
        try:
            batch = generate_telemetry_batch()
            res = requests.post(BACKEND_URL, json={"readings": batch}, timeout=5)

            t1_flow = round(state["AQUA-TANK-01"]["flow"], 2)
            t1_ph = round(state["AQUA-TANK-01"]["ph"], 2)
            t1_fault = state["AQUA-TANK-01"]["fault"]
            status_tag = (
                f"🚨 [SỰ CỐ NGHẸT LỌC & SỐC pH={t1_ph}]"
                if t1_fault
                else f"✅ [TỐI ƯU - Flow={t1_flow} LPM, pH={t1_ph}]"
            )
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] HTTP {res.status_code} | "
                f"Gửi {len(batch)} readings | Aqua Tank-01: {status_tag}"
            )

        except requests.exceptions.RequestException as e:
            print(f"❌ Không thể kết nối tới Backend API ({e}). Đang thử lại...")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frutiger Aqua Smart Aquarium Telemetry Simulator")
    parser.add_argument("--interval", type=float, default=2.0, help="Thời gian giữa các lần gửi (giây)")
    args = parser.parse_args()
    run_simulator(interval=args.interval)
