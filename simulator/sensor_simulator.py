"""
IoT Sensor Simulator for Smart Fridge Fleet.
Mô phỏng dữ liệu telemetry gửi định kỳ về Backend API.
Có hỗ trợ chế độ gây sự cố (Fault Injection) để phục vụ kịch bản demo Hackathon.
"""

import time
import json
import random
import argparse
import requests
from datetime import datetime, timezone

BACKEND_URL = "http://127.0.0.1:8000/api/telemetry/ingest"

# Cấu hình danh sách thiết bị tủ lạnh và ngăn tủ
FRIDGES = [
    {"id": "FRIDGE-KITCHEN-01", "model": "Inverter Pro 550L"},
    {"id": "FRIDGE-LIVING-02", "model": "Compact 120L"},
    {"id": "FRIDGE-PANTRY-03", "model": "DeepFreezer 300L"}
]

# Trạng thái hiện tại của từng ngăn tủ
state = {
    "FRIDGE-KITCHEN-01": {
        "fridge": {"temp": 4.0, "humidity": 65.0, "door_open": False, "fault": None},
        "freezer": {"temp": -18.5, "humidity": 75.0, "door_open": False, "fault": None}
    },
    "FRIDGE-LIVING-02": {
        "fridge": {"temp": 3.8, "humidity": 60.0, "door_open": False, "fault": None},
        "freezer": {"temp": -19.0, "humidity": 72.0, "door_open": False, "fault": None}
    },
    "FRIDGE-PANTRY-03": {
        "fridge": {"temp": 4.5, "humidity": 63.0, "door_open": False, "fault": None},
        "freezer": {"temp": -20.0, "humidity": 70.0, "door_open": False, "fault": None}
    }
}

CONTROL_FILE = "simulator_control.json"

def check_external_control():
    """Đọc lệnh điều khiển sự cố từ file simulator_control.json"""
    try:
        with open(CONTROL_FILE, "r") as f:
            cmd = json.load(f)
            target = cmd.get("device_id", "FRIDGE-KITCHEN-01")
            comp = cmd.get("compartment", "fridge")
            action = cmd.get("action")  # 'INJECT_FAULT' hoặc 'RESOLVE'

            if action == "INJECT_FAULT":
                state[target][comp]["fault"] = "DOOR_AJAR"
                state[target][comp]["door_open"] = True
            elif action == "RESOLVE":
                state[target][comp]["fault"] = None
                state[target][comp]["door_open"] = False
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def generate_telemetry_batch():
    check_external_control()
    batch = []
    now = datetime.now(timezone.utc)

    for fridge in FRIDGES:
        f_id = fridge["id"]
        for comp in ["fridge", "freezer"]:
            curr = state[f_id][comp]
            
            # Nếu đang có sự cố cửa mở quên đóng (DOOR_AJAR)
            if curr["fault"] == "DOOR_AJAR":
                # Nhiệt độ tăng dốc đứng từ 4°C lên 18°C
                curr["temp"] = min(22.0, curr["temp"] + random.uniform(0.8, 1.5))
                curr["humidity"] = min(90.0, curr["humidity"] + random.uniform(1.0, 2.0))
                power = random.uniform(140.0, 180.0) # Máy nén gồng hết công suất
                door_open = True
            else:
                # Trạng thái bình thường: nhiệt độ dao động nhẹ quanh mức chuẩn
                target_base = 4.0 if comp == "fridge" else -18.5
                if curr["temp"] > target_base:
                    curr["temp"] = max(target_base, curr["temp"] - random.uniform(0.5, 1.0))
                else:
                    curr["temp"] = round(target_base + random.uniform(-0.4, 0.4), 2)
                
                curr["humidity"] = round(65.0 + random.uniform(-2.0, 2.0), 1)
                power = round(random.uniform(50.0, 75.0), 1)
                door_open = False

            point = {
                "ts": now.isoformat(),
                "sensor": {
                    "id": f_id,
                    "compartment": comp,
                    "model": fridge["model"]
                },
                "temperature": round(curr["temp"], 2),
                "humidity": round(curr["humidity"], 1),
                "door_open": door_open,
                "power_watts": power
            }
            batch.append(point)

    return batch

def run_simulator(interval: float = 2.0):
    print("🚀 IoT Fridge Simulator bắt đầu chạy...")
    print(f"📡 Endpoint gửi dữ liệu: {BACKEND_URL}")
    print(f"⏱️  Tần suất gửi: mỗi {interval} giây\n")

    while True:
        try:
            batch = generate_telemetry_batch()
            res = requests.post(BACKEND_URL, json={"readings": batch}, timeout=5)
            
            # In log tóm tắt ra console
            k_temp = state["FRIDGE-KITCHEN-01"]["fridge"]["temp"]
            k_fault = state["FRIDGE-KITCHEN-01"]["fridge"]["fault"]
            status_tag = f"⚠️ [SỰ CỐ CỬA MỞ - {k_temp}°C]" if k_fault else f"✅ [Bình thường - {k_temp}°C]"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Đã gửi {len(batch)} readings | Kitchen Fridge: {status_tag}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Không thể kết nối tới Backend API ({e}). Đang thử lại...")

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Fridge Telemetry Simulator")
    parser.add_argument("--interval", type=float, default=2.0, help="Thời gian giữa các lần gửi (giây)")
    args = parser.parse_args()
    run_simulator(interval=args.interval)
