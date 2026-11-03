"""
Datadog Direct Integration Service (Agentless & Dual-Mode).
Gửi trực tiếp Metrics, Logs và Events lên Datadog Cloud qua HTTP API,
giúp Dashboard và Monitor trên Datadog hiển thị dữ liệu ngay lập tức mà không bắt buộc phải cài đặt Datadog Agent dưới máy.
"""

import os
import time
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger("datadog_service")

DD_API_KEY = os.getenv("DD_API_KEY", "")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_ENV = os.getenv("DD_ENV", "hackathon")
DD_SERVICE = os.getenv("DD_SERVICE", "smart-fridge-service")

def is_datadog_configured() -> bool:
    return bool(DD_API_KEY and "your_datadog" not in DD_API_KEY)

def send_metrics_to_datadog(points: List[Dict[str, Any]]):
    """
    Gửi chỉ số cảm biến (nhiệt độ, công suất, trạng thái cửa) lên Datadog Metrics API v1.
    """
    if not is_datadog_configured():
        return

    # URL theo region (US1, US5, EU, ...)
    url = f"https://api.{DD_SITE}/api/v1/series"
    headers = {
        "DD-API-KEY": DD_API_KEY,
        "Content-Type": "application/json"
    }

    now_ts = int(time.time())
    series = []

    for p in points:
        device_id = p["sensor"]["id"]
        comp = p["sensor"]["compartment"]
        tags = [
            f"device:{device_id}",
            f"compartment:{comp}",
            f"env:{DD_ENV}",
            f"service:{DD_SERVICE}"
        ]

        # Metric 1: Nhiệt độ
        series.append({
            "metric": "smartfridge.temperature",
            "points": [[now_ts, float(p["temperature"])]],
            "type": "gauge",
            "tags": tags
        })

        # Metric 2: Công suất máy nén (Watts)
        series.append({
            "metric": "smartfridge.power_watts",
            "points": [[now_ts, float(p["power_watts"])]],
            "type": "gauge",
            "tags": tags
        })

        # Metric 3: Trạng thái cửa mở (1 = mở, 0 = đóng)
        series.append({
            "metric": "smartfridge.door_open",
            "points": [[now_ts, 1.0 if p.get("door_open") else 0.0]],
            "type": "gauge",
            "tags": tags
        })

    try:
        res = requests.post(url, headers=headers, json={"series": series}, timeout=3)
        if res.status_code != 202:
            logger.debug(f"Datadog metrics intake response: {res.status_code}")
    except Exception as e:
        logger.debug(f"Không thể gửi metrics tới Datadog: {e}")

def send_log_to_datadog(message: str, status: str = "info", extra_tags: List[str] = None):
    """
    Gửi log sự kiện / cảnh báo trực tiếp lên Datadog Log Management API.
    """
    if not is_datadog_configured():
        return

    url = f"https://http-intake.logs.{DD_SITE}/api/v2/logs"
    headers = {
        "DD-API-KEY": DD_API_KEY,
        "Content-Type": "application/json"
    }

    tags = [f"env:{DD_ENV}", f"service:{DD_SERVICE}"]
    if extra_tags:
        tags.extend(extra_tags)

    payload = [{
        "ddsource": "python",
        "ddtags": ",".join(tags),
        "hostname": "iot-edge-server",
        "service": DD_SERVICE,
        "status": status,
        "message": message
    }]

    try:
        requests.post(url, headers=headers, json=payload, timeout=3)
    except Exception as e:
        logger.debug(f"Không thể gửi log tới Datadog: {e}")

def send_incident_event(title: str, text: str, alert_type: str = "warning"):
    """
    Gửi Event vào Datadog Event Stream (hiển thị trên Dashboard / Monitor).
    """
    if not is_datadog_configured():
        return

    url = f"https://api.{DD_SITE}/api/v1/events"
    headers = {
        "DD-API-KEY": DD_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "title": title,
        "text": text,
        "alert_type": alert_type,  # 'error', 'warning', 'info', 'success'
        "tags": [f"env:{DD_ENV}", f"service:{DD_SERVICE}"]
    }

    try:
        requests.post(url, headers=headers, json=payload, timeout=3)
    except Exception as e:
        logger.debug(f"Không thể gửi event tới Datadog: {e}")
