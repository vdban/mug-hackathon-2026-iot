"""
Script kiểm tra kết nối với Datadog API.
Gửi 1 metric và 1 event thử nghiệm để xác nhận Datadog API Key hoạt động chính xác.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

DD_API_KEY = os.getenv("DD_API_KEY", "")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")

if not DD_API_KEY or "your_datadog" in DD_API_KEY:
    print("❌ Vui lòng điền DD_API_KEY hợp lệ trong file .env trước!")
    exit(1)

print(f"📡 Đang kiểm tra kết nối tới Datadog ({DD_SITE})...")

# 1. Gửi Metric thử nghiệm
metric_url = f"https://api.{DD_SITE}/api/v1/series"
now = int(time.time())
metric_payload = {
    "series": [
        {
            "metric": "smartfridge.test_ping",
            "points": [[now, 100]],
            "type": "gauge",
            "tags": ["env:hackathon", "test:connection_check"]
        }
    ]
}

res = requests.post(metric_url, headers={"DD-API-KEY": DD_API_KEY}, json=metric_payload, timeout=5)
if res.status_code == 202:
    print("✅ [METRIC API] Gửi metric thành công (HTTP 202)!")
else:
    print(f"❌ [METRIC API] Lỗi: HTTP {res.status_code} - {res.text}")

# 2. Gửi Event thử nghiệm
event_url = f"https://api.{DD_SITE}/api/v1/events"
event_payload = {
    "title": "🎉 Smart Fridge Datadog Connection Verified",
    "text": "Kết nối giữa ứng dụng Smart Fridge IoT và Datadog đã thiết lập thành công!",
    "alert_type": "success",
    "tags": ["env:hackathon", "source:setup_verification"]
}

res2 = requests.post(event_url, headers={"DD-API-KEY": DD_API_KEY}, json=event_payload, timeout=5)
if res2.status_code == 202:
    print("✅ [EVENT API] Gửi event thành công (HTTP 202)!")
    print(f"\n👉 Hãy vào https://app.{DD_SITE}/event/stream để xem Event vừa xuất hiện!")
else:
    print(f"❌ [EVENT API] Lỗi: HTTP {res2.status_code} - {res2.text}")
