"""
Datadog Direct Integration Service for Smart Hydroponics Farm.
Gửi Metrics, Logs (kèm dd.trace_id / dd.span_id correlation) và Events lên Datadog Cloud qua HTTP API
theo cơ chế non-blocking để không làm tăng latency của ingestion API.
"""

import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH, override=True)

logger = logging.getLogger("datadog_service")
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="dd-intake")


def _get_config() -> Dict[str, str]:
    load_dotenv(_ENV_PATH, override=True)
    return {
        "api_key": os.getenv("DD_API_KEY", "").strip(),
        "site": os.getenv("DD_SITE", "datadoghq.com").strip(),
        "env": os.getenv("DD_ENV", "hackathon").strip(),
        "service": os.getenv("DD_SERVICE", "smart-hydroponics-service").strip(),
    }


def is_datadog_configured() -> bool:
    api_key = _get_config()["api_key"]
    return bool(api_key and "your_datadog" not in api_key)


def get_current_trace_context() -> Dict[str, str]:
    """Lấy trace_id và span_id hiện tại từ ddtrace (nếu đang chạy với APM)."""
    try:
        from ddtrace import tracer
        span = tracer.current_span()
        if span is not None:
            return {
                "trace_id": str(span.trace_id),
                "span_id": str(span.span_id),
            }
    except Exception:
        pass
    return {}


def _to_unix_ts(ts_val: Any, fallback_ts: int) -> int:
    if isinstance(ts_val, datetime):
        return int(ts_val.timestamp())
    return fallback_ts


def _post_json(url: str, api_key: str, payload: Any, label: str) -> None:
    try:
        res = requests.post(
            url,
            headers={"DD-API-KEY": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=3,
        )
        if res.status_code not in (200, 202):
            logger.debug("Datadog %s intake response: %s %s", label, res.status_code, res.text[:200])
    except Exception as exc:
        logger.debug("Không thể gửi %s tới Datadog: %s", label, exc)


def _dispatch(url: str, api_key: str, payload: Any, label: str, async_send: bool = True) -> None:
    if async_send:
        _EXECUTOR.submit(_post_json, url, api_key, payload, label)
    else:
        _post_json(url, api_key, payload, label)


def send_metrics_to_datadog(
    points: List[Dict[str, Any]],
    ingest_latency_ms: Optional[float] = None,
    alert_count: int = 0,
    async_send: bool = True,
) -> None:
    """
    Gửi chỉ số cảm biến nông nghiệp (pH, EC, Nhiệt độ nước, Mực nước, Lưu lượng bơm)
    cùng chỉ số hiệu năng ingest latency và số cảnh báo lên Datadog.
    """
    if not is_datadog_configured():
        return

    cfg = _get_config()
    url = f"https://api.{cfg['site']}/api/v1/series"
    now_ts = int(time.time())
    series = []

    for p in points:
        rack_id = p["sensor"]["id"]
        crop = p["sensor"]["crop"]
        zone = p["sensor"]["zone"]
        point_ts = _to_unix_ts(p.get("ts"), now_ts)
        tags = [
            f"rack_id:{rack_id}",
            f"crop:{crop}",
            f"zone:{zone}",
            f"env:{cfg['env']}",
            f"service:{cfg['service']}",
        ]

        series.extend([
            {"metric": "smartfarm.ph", "points": [[point_ts, float(p["ph"])]], "type": "gauge", "tags": tags},
            {"metric": "smartfarm.ec_ppm", "points": [[point_ts, float(p["ec_ppm"])]], "type": "gauge", "tags": tags},
            {"metric": "smartfarm.water_temp", "points": [[point_ts, float(p["water_temp"])]], "type": "gauge", "tags": tags},
            {"metric": "smartfarm.water_level_pct", "points": [[point_ts, float(p["water_level_pct"])]], "type": "gauge", "tags": tags},
            {"metric": "smartfarm.pump_flow_lpm", "points": [[point_ts, float(p["pump_flow_lpm"])]], "type": "gauge", "tags": tags},
        ])

    service_tags = [f"env:{cfg['env']}", f"service:{cfg['service']}"]
    if ingest_latency_ms is not None:
        series.append({
            "metric": "smartfarm.ingest.latency_ms",
            "points": [[now_ts, round(float(ingest_latency_ms), 2)]],
            "type": "gauge",
            "tags": service_tags,
        })
    if alert_count > 0:
        series.append({
            "metric": "smartfarm.alerts.count",
            "points": [[now_ts, int(alert_count)]],
            "type": "count",
            "tags": service_tags,
        })

    _dispatch(url, cfg["api_key"], {"series": series}, "metrics", async_send=async_send)


def send_mttr_metric_to_datadog(device_id: str, mttr_seconds: float, async_send: bool = True) -> None:
    """Gửi chỉ số Mean Time To Resolution (giây) lên Datadog khi sự cố được khắc phục."""
    if not is_datadog_configured():
        return

    cfg = _get_config()
    url = f"https://api.{cfg['site']}/api/v1/series"
    now_ts = int(time.time())
    payload = {
        "series": [{
            "metric": "smartfarm.incidents.mttr_seconds",
            "points": [[now_ts, round(float(mttr_seconds), 2)]],
            "type": "gauge",
            "tags": [
                f"rack_id:{device_id}",
                f"env:{cfg['env']}",
                f"service:{cfg['service']}",
            ],
        }]
    }
    _dispatch(url, cfg["api_key"], payload, "mttr-metric", async_send=async_send)


def send_log_to_datadog(
    message: str,
    status: str = "info",
    extra_tags: Optional[List[str]] = None,
    trace_ctx: Optional[Dict[str, str]] = None,
    async_send: bool = True,
) -> None:
    """
    Gửi log trực tiếp lên Datadog Log Management, tự động đính kèm dd.trace_id và dd.span_id
    để liên kết 1-click giữa Log và Trace trên Datadog UI.
    """
    if not is_datadog_configured():
        return

    cfg = _get_config()
    url = f"https://http-intake.logs.{cfg['site']}/api/v2/logs"

    tags = [f"env:{cfg['env']}", f"service:{cfg['service']}"]
    if extra_tags:
        tags.extend(extra_tags)

    ctx = trace_ctx if trace_ctx is not None else get_current_trace_context()
    entry: Dict[str, Any] = {
        "ddsource": "python",
        "ddtags": ",".join(tags),
        "hostname": "iot-agritech-gateway",
        "service": cfg["service"],
        "status": status,
        "message": message,
    }
    if ctx.get("trace_id"):
        entry["dd"] = {
            "trace_id": ctx["trace_id"],
            "span_id": ctx.get("span_id", ""),
        }

    _dispatch(url, cfg["api_key"], [entry], "logs", async_send=async_send)


def send_incident_event(
    title: str,
    text: str,
    alert_type: str = "warning",
    extra_tags: Optional[List[str]] = None,
    async_send: bool = True,
) -> None:
    """Gửi Event vào Datadog Event Stream."""
    if not is_datadog_configured():
        return

    cfg = _get_config()
    url = f"https://api.{cfg['site']}/api/v1/events"
    tags = [f"env:{cfg['env']}", f"service:{cfg['service']}"]
    if extra_tags:
        tags.extend(extra_tags)

    payload = {
        "title": title,
        "text": text,
        "alert_type": alert_type,
        "tags": tags,
    }
    _dispatch(url, cfg["api_key"], payload, "events", async_send=async_send)
