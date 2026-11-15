"""
Script kích hoạt và xử lý sự cố vận hành cho Frutiger Aqua Smart Aquarium (Real-time Operations Demo).
Đồng bộ cả qua Backend API và file simulator_control.json tại thư mục gốc dự án.
"""

import os
import json
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BASE_URL = os.getenv("BACKEND_BASE_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}")

CONTROL_FILE = PROJECT_ROOT / "simulator_control.json"
BACKEND_CONTROL_URL = f"{BASE_URL}/api/simulator/control"
BACKEND_RESPOND_URL = f"{BASE_URL}/api/incident/respond"


def inject_fault(device_id: str = "AQUA-TANK-01"):
    reason = "FILTER_CLOG_AND_PH_SPIKE (Nghẹt lọc tuần hoàn & sốc pH bể cá)"
    cmd = {
        "device_id": device_id,
        "action": "INJECT_FAULT",
        "reason": reason,
    }
    CONTROL_FILE.write_text(json.dumps(cmd, ensure_ascii=False), encoding="utf-8")

    try:
        res = requests.post(BACKEND_CONTROL_URL, json=cmd, timeout=5)
        print(f"API Control Response: HTTP {res.status_code}")
    except Exception as e:
        print(f"Lưu ý: Không gọi được Backend API ({e}), đã ghi trạng thái vào {CONTROL_FILE.name}.")

    print("\n🚨 [SỰ CỐ BỂ CÁ ĐÃ ĐƯỢC KÍCH HOẠT!]")
    print(f"👉 Thiết bị: {device_id} (Bể Thủy Sinh Frutiger Aqua)")
    print("👉 Triệu chứng: Lọc tuần hoàn bị nghẹt cặn, lưu lượng sụt giảm < 0.5 LPM, pH vọt lên > 8.0!")
    print("👉 Hãy quan sát Datadog Monitor & Dashboard: Cảnh báo đỏ sẽ nổ trong vài giây tới!\n")


def resolve_fault(device_id: str = "AQUA-TANK-01"):
    cmd = {
        "device_id": device_id,
        "action": "RESOLVE",
    }
    CONTROL_FILE.write_text(json.dumps(cmd, ensure_ascii=False), encoding="utf-8")

    try:
        payload = {
            "device_id": device_id,
            "action": "REVERSE_FLUSH_AND_DOSING_PH_DOWN",
            "notes": "Hệ thống tự động xả ngược thông lọc bể cá và châm dung dịch cân bằng pH.",
        }
        res = requests.post(BACKEND_RESPOND_URL, json=payload, timeout=5)
        print("\n🛠️ [HÀNH ĐỘNG KHẮC PHỤC ĐÃ ĐƯỢC GỬI]")
        print(f"API Response: {res.json()}")
    except Exception as e:
        print(f"Lưu ý: Không gọi được Backend API ({e}), nhưng đã đặt lại trạng thái simulator.")

    print("\n✅ [HỆ THỐNG BỂ CÁ ĐANG HỒI PHỤC]")
    print("👉 Bộ lọc đã thông thoáng, lưu lượng bơm phục hồi ~4.5 LPM.")
    print("👉 Độ pH trở về vùng an toàn (~6.8).")
    print("👉 Datadog Monitor sẽ chuyển từ ALERT (Đỏ) sang OK (Xanh).\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Aquarium Incident CLI")
    parser.add_argument("--fault", action="store_true", help="Gây sự cố nghẹt lọc và sốc pH")
    parser.add_argument("--resolve", action="store_true", help="Khắc phục sự cố (Xả ngược và cân bằng pH)")
    parser.add_argument("--device", default="AQUA-TANK-01", help="ID bể cá thông minh")

    args = parser.parse_args()

    if args.fault:
        inject_fault(device_id=args.device)
    elif args.resolve:
        resolve_fault(device_id=args.device)
    else:
        print("Vui lòng chọn flag: --fault (gây lỗi) hoặc --resolve (khắc phục)")
