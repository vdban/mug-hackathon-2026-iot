"""
Datadog Direct Integration Service for Smart Hydroponics Farm.
Gửi trực tiếp Metrics, Logs và Events lên Datadog Cloud qua HTTP API.
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
DD_SERVICE = os.getenv("DD_SERVICE", "smart-hydroponics-service")

def is_datadog_configured() -> bool:
    return bool(DD_API_KEY and "your_datadog" not in DD_API_KEY)

def send_metrics_to_datadog(points: List[Dict[str, Any]]):
    """
    Gửi chỉ số cảm biến nông nghiệp (pH, EC, Nhiệt độ nước, Mực nước, Lưu lượng bơm) lên Datadog.
    """
    if not is_datadog_configured():
        return

    url = f"https://api.{DD_SITE}/api/v1/series"
    headers = {
        "DD-API-KEY": DD_API_KEY,
        "Content-Type": "application/json"
    }

    now_ts = int(time.time())
    series = []

    for p in points:
        rack_id = p["sensor"]["id"]
        crop = p["sensor"]["crop"]
        zone = p["sensor"]["zone"]
        tags = [
            f"rack_id:{rack_id}",
            f"crop:{crop}",
            f"zone:{zone}",
            f"env:{DD_ENV}",
            f"service:{DD_SERVICE}"
        ]

        # 1. pH
        series.append({
            "metric": "smartfarm.ph",
            "points": [[now_ts, float(p["ph"])]],
            "type": "gauge",
            "tags": tags
        })
        # 2. EC (ppm)
        series.append({
            "metric": "smartfarm.ec_ppm",
            "points": [[now_ts, float(p["ec_ppm"])]],
            "type": "gauge",
            "tags": tags
        })
        # 3. Water Temp (°C)
        series.append({
            "metric": "smartfarm.water_temp",
            "points": [[now_ts, float(p["water_temp"])]],
            "type": "gauge",
            "tags": tags
        })
        # 4. Water Level (%)
        series.append({
            "metric": "smartfarm.water_level_pct",
            "points": [[now_ts, float(p["water_level_pct"])]],
            "type": "gauge",
            "tags": tags
        })
        # 5. Pump Flow (LPM)
        series.append({
            "metric": "smartfarm.pump_flow_lpm",
            "points": [[now_ts, float(p["pump_flow_lpm"])]],
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
    Gửi log cảnh báo trực tiếp lên Datadog Log Management.
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
        "hostname": "iot-agritech-gateway",
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
    Gửi Event vào Datadog Event Stream.
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
        "alert_type": alert_type,
        "tags": [f"env:{DD_ENV}", f"service:{DD_SERVICE}"]
    }

    try:
        requests.post(url, headers=headers, json=payload, timeout=3)
    except Exception as e:
        logger.debug(f"Không thể gửi event tới Datadog: {e}")
