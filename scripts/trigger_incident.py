"""
Script kích hoạt và xử lý sự cố vận hành cho bài thi Hackathon (Real-time Operations Demo).
"""

import sys
import json
import argparse
import requests

CONTROL_FILE = "simulator_control.json"
BACKEND_RESPOND_URL = "http://127.0.0.1:8000/api/incident/respond"

def inject_fault(device_id="FRIDGE-KITCHEN-01", compartment="fridge"):
    cmd = {
        "device_id": device_id,
        "compartment": compartment,
        "action": "INJECT_FAULT",
        "reason": "DOOR_AJAR (Quên đóng cửa tủ lạnh)"
    }
    with open(CONTROL_FILE, "w") as f:
        json.dump(cmd, f)
    print("\n🚨 [SỰ CỐ ĐÃ ĐƯỢC KÍCH HOẠT!]")
    print(f"👉 Thiết bị: {device_id} ({compartment})")
    print("👉 Triệu chứng: Cửa tủ lạnh bị mở hé, nhiệt độ đang tăng vọt lên > 15°C.")
    print("👉 Hãy quan sát Datadog Monitor & Dashboard: Cảnh báo đỏ sẽ nổ trong vài giây tới!\n")

def resolve_fault(device_id="FRIDGE-KITCHEN-01", compartment="fridge"):
    # 1. Báo simulator ngắt fault
    cmd = {
        "device_id": device_id,
        "compartment": compartment,
        "action": "RESOLVE"
    }
    with open(CONTROL_FILE, "w") as f:
        json.dump(cmd, f)

    # 2. Gửi request sang Backend API ghi nhận hành động xử lý (Respond phase)
    try:
        payload = {
            "device_id": device_id,
            "compartment": compartment,
            "action": "CLOSE_DOOR_AND_BOOST_COOLING",
            "notes": "Hệ thống tự động kích hoạt chốt đóng cửa và tăng tốc độ làm lạnh khẩn cấp."
        }
        res = requests.post(BACKEND_RESPOND_URL, json=payload, timeout=5)
        print("\n🛠️ [HÀNH ĐỘNG KHẮC PHỤC ĐÃ ĐƯỢC GỬI]")
        print(f"API Response: {res.json()}")
    except Exception as e:
        print(f"Lưu ý: Không gọi được Backend API ({e}), nhưng đã đặt lại trạng thái simulator.")

    print("\n✅ [HỆ THỐNG ĐANG HỒI PHỤC]")
    print("👉 Cửa tủ lạnh đã được đóng lại.")
    print("👉 Nhiệt độ trên Datadog Dashboard sẽ hạ dần về 4°C và Monitor sẽ chuyển về trạng thái OK (Xanh).\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fault Injection & Remediation CLI")
    parser.add_argument("--fault", action="store_true", help="Gây sự cố quên đóng cửa tủ lạnh")
    parser.add_argument("--resolve", action="store_true", help="Khắc phục sự cố (Đóng cửa tủ & hạ nhiệt)")
    parser.add_argument("--device", default="FRIDGE-KITCHEN-01", help="ID thiết bị")
    
    args = parser.parse_args()

    if args.fault:
        inject_fault(device_id=args.device)
    elif args.resolve:
        resolve_fault(device_id=args.device)
    else:
        print("Vui lòng chọn flag: --fault (gây lỗi) hoặc --resolve (khắc phục)")
