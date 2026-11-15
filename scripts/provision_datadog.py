"""
Script tự động tạo Datadog Dashboard và Monitors từ các file JSON trong thư mục datadog/.
Yêu cầu cả DD_API_KEY và DD_APP_KEY (Application Key) trong file .env.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATADOG_DIR = PROJECT_ROOT / "datadog"

load_dotenv(PROJECT_ROOT / ".env", override=True)

DD_API_KEY = os.getenv("DD_API_KEY", "").strip()
DD_APP_KEY = os.getenv("DD_APP_KEY", "").strip()
DD_SITE = os.getenv("DD_SITE", "datadoghq.com").strip()

PH_FALLBACK_MONITOR: Dict[str, Any] = {
    "name": "[P1] Smart Hydroponics - Alkaline pH Lockout (pH > 7.6)",
    "type": "metric alert",
    "query": "avg(last_1m):avg:smartfarm.ph{*} by {rack_id} > 7.6",
    "message": (
        "🚨 [CRITICAL] Thiết bị {{rack_id.name}} có độ pH kiềm hóa vượt ngưỡng 7.6 "
        "(nguy cơ khóa dinh dưỡng & sốc cá/cây)!\n\n"
        "Mở Dashboard để điều tra và kích hoạt xử lý tại /api/incident/respond."
    ),
    "tags": [
        "env:hackathon",
        "service:smart-hydroponics-service",
        "domain:agritech",
    ],
    "options": {
        "thresholds": {
            "critical": 7.6,
            "warning": 7.2,
        },
        "notify_no_data": False,
        "require_full_window": False,
        "notify_audit": False,
        "include_tags": True,
    },
    "priority": 1,
}


def _fetch_existing_monitors(headers: Dict[str, str]) -> Dict[str, Any]:
    """Lấy danh sách Monitor hiện có trên Datadog theo tên để tránh tạo trùng."""
    try:
        resp = requests.get(f"https://api.{DD_SITE}/api/v1/monitor", headers=headers, timeout=10)
        if resp.status_code == 200 and isinstance(resp.json(), list):
            return {m.get("name"): m.get("id") for m in resp.json() if m.get("name")}
    except Exception as exc:
        print(f"⚠️  Không thể kiểm tra Monitor hiện có: {exc}")
    return {}


def _ensure_monitor(
    headers: Dict[str, str],
    mon_payload: Dict[str, Any],
    label: str,
    existing_monitors: Dict[str, Any],
) -> str:
    """Tạo Monitor nếu chưa tồn tại; trả về trạng thái created/exists/logs_disabled/error."""
    mon_name = mon_payload.get("name", "")
    if mon_name in existing_monitors:
        print(f"ℹ️  Monitor đã tồn tại ({label}): ID {existing_monitors[mon_name]} ({mon_name})")
        return "exists"

    r_mon = requests.post(
        f"https://api.{DD_SITE}/api/v1/monitor",
        headers=headers,
        json=mon_payload,
        timeout=10,
    )
    if r_mon.status_code in (200, 201):
        mon_id = r_mon.json().get("id")
        existing_monitors[mon_name] = mon_id
        print(f"✅ Đã tạo Monitor ({label}): ID {mon_id}")
        return "created"

    if r_mon.status_code == 400 and "Track logs is not yet enabled" in r_mon.text:
        return "logs_disabled"

    print(f"⚠️  Không tạo được Monitor ({label}): HTTP {r_mon.status_code} - {r_mon.text}")
    return "error"


def main():
    if not DD_API_KEY or "your_datadog" in DD_API_KEY:
        print("❌ Thiếu DD_API_KEY hợp lệ trong .env")
        raise SystemExit(1)
    if not DD_APP_KEY or "your_datadog" in DD_APP_KEY:
        print("❌ Thiếu DD_APP_KEY trong .env (tạo tại Datadog -> Organization Settings -> Application Keys).")
        print("ℹ️  Bạn vẫn có thể import thủ công các file JSON trong thư mục datadog/ trên giao diện Datadog.")
        raise SystemExit(1)

    headers = {
        "DD-API-KEY": DD_API_KEY,
        "DD-APPLICATION-KEY": DD_APP_KEY,
        "Content-Type": "application/json",
    }

    # 1. Tạo Dashboard
    dash_path = DATADOG_DIR / "dashboard.json"
    dash_payload = json.loads(dash_path.read_text(encoding="utf-8"))
    r_dash = requests.post(f"https://api.{DD_SITE}/api/v1/dashboard", headers=headers, json=dash_payload, timeout=10)
    if r_dash.status_code in (200, 201):
        print(f"✅ Đã tạo Datadog Dashboard: https://app.{DD_SITE}{r_dash.json().get('url', '')}")
    else:
        print(f"⚠️  Không tạo được Dashboard: HTTP {r_dash.status_code} - {r_dash.text}")

    # 2. Tạo Monitors (idempotent theo tên)
    existing_monitors = _fetch_existing_monitors(headers)
    for mon_file in ["monitor_pipe_clog.json", "monitor_farm_alert_log.json"]:
        mon_path = DATADOG_DIR / mon_file
        mon_payload = json.loads(mon_path.read_text(encoding="utf-8"))
        status = _ensure_monitor(headers, mon_payload, mon_file, existing_monitors)
        if status == "logs_disabled":
            print(
                f"ℹ️  {mon_file}: Datadog Log Management chưa được kích hoạt trên tổ chức này "
                "(vào Datadog UI -> Logs -> Get Started để bật Log Management)."
            )
            _ensure_monitor(headers, PH_FALLBACK_MONITOR, "fallback-ph-monitor", existing_monitors)


if __name__ == "__main__":
    main()
