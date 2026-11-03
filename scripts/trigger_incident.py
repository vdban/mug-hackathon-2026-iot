"""
Script kích hoạt và xử lý sự cố vận hành cho Smart Hydroponics Farm (Real-time Operations Demo).
"""

import sys
import json
import argparse
import requests

CONTROL_FILE = "simulator_control.json"
BACKEND_RESPOND_URL = "http://127.0.0.1:8000/api/incident/respond"

def inject_fault(device_id="HYDROPONIC-RACK-01"):
    cmd = {
        "device_id": device_id,
        "action": "INJECT_FAULT",
        "reason": "PIPE_CLOG_AND_NUTRIENT_LOCKOUT (Nghẹt rễ cây & kiềm hóa pH)"
    }
    with open(CONTROL_FILE, "w") as f:
        json.dump(cmd, f)
    print("\n🚨 [SỰ CỐ NÔNG NGHIỆP ĐÃ ĐƯỢC KÍCH HOẠT!]")
    print(f"👉 Thiết bị: {device_id} (Giàn Xà lách Ban công)")
    print("👉 Triệu chứng: Đường ống tuần hoàn bị nghẹt cặn rễ, lưu lượng sụt giảm < 0.5 LPM, pH kiềm hóa vọt lên > 8.0!")
    print("👉 Hãy quan sát Datadog Monitor & Dashboard: Cảnh báo đỏ sẽ nổ trong vài giây tới!\n")

def resolve_fault(device_id="HYDROPONIC-RACK-01"):
    # 1. Báo simulator ngắt fault
    cmd = {
        "device_id": device_id,
        "action": "RESOLVE"
    }
    with open(CONTROL_FILE, "w") as f:
        json.dump(cmd, f)

    # 2. Gửi request sang Backend API ghi nhận hành động xử lý (Respond phase)
    try:
        payload = {
            "device_id": device_id,
            "action": "REVERSE_FLUSH_AND_DOSING_PH_DOWN",
            "notes": "Hệ thống tự động xả ngược áp lực cao thông ống và châm dung dịch cân bằng pH."
        }
        res = requests.post(BACKEND_RESPOND_URL, json=payload, timeout=5)
        print("\n🛠️ [HÀNH ĐỘNG KHẮC PHỤC ĐÃ ĐƯỢC GỬI]")
        print(f"API Response: {res.json()}")
    except Exception as e:
        print(f"Lưu ý: Không gọi được Backend API ({e}), nhưng đã đặt lại trạng thái simulator.")

    print("\n✅ [HỆ THỐNG THỦY CANH ĐANG HỒI PHỤC]")
    print("👉 Đường ống đã thông thoáng, lưu lượng bơm phục hồi 4.5 LPM.")
    print("👉 Độ pH hạ dần về 6.1 (vùng lý tưởng cho xà lách hấp thụ dinh dưỡng).")
    print("👉 Datadog Monitor sẽ chuyển từ ALERT (Đỏ) sang OK (Xanh).\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Hydroponics Incident CLI")
    parser.add_argument("--fault", action="store_true", help="Gây sự cố nghẹt ống và kiềm hóa pH")
    parser.add_argument("--resolve", action="store_true", help="Khắc phục sự cố (Xả ngược và châm pH-Down)")
    parser.add_argument("--device", default="HYDROPONIC-RACK-01", help="ID giàn thủy canh")

    args = parser.parse_args()

    if args.fault:
        inject_fault(device_id=args.device)
    elif args.resolve:
        resolve_fault(device_id=args.device)
    else:
        print("Vui lòng chọn flag: --fault (gây lỗi) hoặc --resolve (khắc phục)")
