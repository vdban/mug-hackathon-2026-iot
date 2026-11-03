"""
IoT Sensor Simulator for Smart Hydroponics Fleet.
Mô phỏng dữ liệu cảm biến nông nghiệp công nghệ cao gửi định kỳ về Backend API.
Có hỗ trợ chế độ gây sự cố (Fault Injection) phục vụ kịch bản demo Hackathon.
"""

import time
import json
import random
import argparse
import requests
from datetime import datetime, timezone

BACKEND_URL = "http://127.0.0.1:8000/api/telemetry/ingest"

RACKS = [
    {"id": "HYDROPONIC-RACK-01", "zone": "Balcony 1F", "crop": "Lettuce", "type": "NFT-Vertical"},
    {"id": "HYDROPONIC-RACK-02", "zone": "Rooftop 3F", "crop": "Strawberries", "type": "Drip-Hydroponics"},
    {"id": "HYDROPONIC-RACK-03", "zone": "Indoor Kitchen", "crop": "Herbs", "type": "Aeroponics-Rack"}
]

state = {
    "HYDROPONIC-RACK-01": {"ph": 6.1, "ec": 960.0, "temp": 21.4, "level": 88.0, "flow": 4.5, "fault": None},
    "HYDROPONIC-RACK-02": {"ph": 5.9, "ec": 1120.0, "temp": 20.8, "level": 92.0, "flow": 4.2, "fault": None},
    "HYDROPONIC-RACK-03": {"ph": 6.2, "ec": 850.0, "temp": 22.1, "level": 80.0, "flow": 3.8, "fault": None}
}

CONTROL_FILE = "simulator_control.json"

def check_external_control():
    """Đọc lệnh điều khiển sự cố từ file simulator_control.json"""
    try:
        with open(CONTROL_FILE, "r") as f:
            cmd = json.load(f)
            target = cmd.get("device_id", "HYDROPONIC-RACK-01")
            action = cmd.get("action")

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

    for rack in RACKS:
        r_id = rack["id"]
        curr = state[r_id]

        # Xử lý sự cố nếu có cờ lỗi
        if curr["fault"] == "CLOG_AND_PH_DRIFT":
            # Tắc nghẽn ống hồi lưu: Lưu lượng tụt dốc, pH tăng kiềm hóa, mực nước giảm
            curr["flow"] = max(0.2, curr["flow"] - random.uniform(0.5, 0.8))
            curr["ph"] = min(8.3, curr["ph"] + random.uniform(0.25, 0.45))
            curr["level"] = max(15.0, curr["level"] - random.uniform(5.0, 9.0))
            curr["ec"] = max(500.0, curr["ec"] - random.uniform(30.0, 60.0))
        else:
            # Trạng thái bình thường hồi phục dần về mốc lý tưởng
            target_flow = 4.5 if r_id == "HYDROPONIC-RACK-01" else (4.2 if r_id == "HYDROPONIC-RACK-02" else 3.8)
            target_ph = 6.1 if r_id == "HYDROPONIC-RACK-01" else (5.9 if r_id == "HYDROPONIC-RACK-02" else 6.2)
            target_level = 88.0

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

            curr["ec"] = round(curr["ec"] + random.uniform(-10.0, 10.0), 0)

        curr["temp"] = round(21.4 + random.uniform(-0.3, 0.3), 1)

        point = {
            "ts": now.isoformat(),
            "sensor": {
                "id": r_id,
                "zone": rack["zone"],
                "crop": rack["crop"],
                "system_type": rack["type"]
            },
            "ph": round(curr["ph"], 2),
            "ec_ppm": round(curr["ec"], 0),
            "water_temp": round(curr["temp"], 1),
            "water_level_pct": round(curr["level"], 1),
            "pump_flow_lpm": round(curr["flow"], 2)
        }
        batch.append(point)

    return batch

def run_simulator(interval: float = 2.0):
    print("🌿 Smart Hydroponics Simulator bắt đầu chạy...")
    print(f"📡 Endpoint gửi dữ liệu: {BACKEND_URL}")
    print(f"⏱️  Tần suất gửi: mỗi {interval} giây\n")

    while True:
        try:
            batch = generate_telemetry_batch()
            res = requests.post(BACKEND_URL, json={"readings": batch}, timeout=5)

            r1_flow = state["HYDROPONIC-RACK-01"]["flow"]
            r1_ph = state["HYDROPONIC-RACK-01"]["ph"]
            r1_fault = state["HYDROPONIC-RACK-01"]["fault"]
            status_tag = f"🚨 [SỰ CỐ NGHẸT ỐNG & pH={r1_ph}]" if r1_fault else f"✅ [TỐI ƯU - Flow={r1_flow} LPM, pH={r1_ph}]"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Đã gửi {len(batch)} readings | Balcony Lettuce: {status_tag}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Không thể kết nối tới Backend API ({e}). Đang thử lại...")

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Hydroponics Telemetry Simulator")
    parser.add_argument("--interval", type=float, default=2.0, help="Thời gian giữa các lần gửi (giây)")
    args = parser.parse_args()
    run_simulator(interval=args.interval)
