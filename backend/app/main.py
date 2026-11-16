import os
import re
import json
import time
import socket
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pymongo.errors import BulkWriteError, PyMongoError

from app.database import get_database, check_db_health
from app.models import (
    TelemetryBatch,
    IncidentActionRequest,
    SimulatorControlRequest,
    DatadogWebhookPayload,
)
from app.analytics import (
    get_latest_telemetry_pipeline,
    get_hourly_summary_pipeline,
    get_trend_and_anomalies_pipeline,
)
from app.datadog_service import (
    is_datadog_configured,
    get_current_trace_context,
    send_metrics_to_datadog,
    send_mttr_metric_to_datadog,
    send_log_to_datadog,
    send_incident_event,
)
from app.firebase_service import (
    is_firebase_configured,
    sync_state_to_firebase,
)


class DatadogTraceFilter(logging.Filter):
    """Tự động gắn dd.trace_id và dd.span_id vào Python logs khi chạy với ddtrace."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_current_trace_context()
        record.dd_trace_id = ctx.get("trace_id", "0")
        record.dd_span_id = ctx.get("span_id", "0")
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] [dd.trace_id=%(dd_trace_id)s dd.span_id=%(dd_span_id)s] %(message)s",
)
logger = logging.getLogger("smart_hydroponics_api")
for _handler in logging.getLogger().handlers:
    _handler.addFilter(DatadogTraceFilter())
logger.addFilter(DatadogTraceFilter())

_WOKWI_HOST = os.getenv("WOKWI_HOST", "127.0.0.1")
_WOKWI_PORT = int(os.getenv("WOKWI_PORT", "4000"))
_WOKWI_TANK_ID = "AQUA-TANK-01"
_TELEMETRY_PREFIX = "@@TELEMETRY@@"
_HUMAN_TELEMETRY_RE = re.compile(
    r"pH:\s*([\d.]+)\s*\|\s*TDS:\s*([\d.]+)\s*ppm\s*\|\s*Nhiệt độ:\s*([-\d.]+)\s*°C\s*\|\s*Mực nước:\s*([\d.]+)%\s*\|\s*Lưu lượng lọc:\s*([\d.]+)"
)


class _Rfc2217StreamDecoder:
    """Loại bỏ byte điều khiển Telnet/RFC2217 (0xFF) khỏi luồng UART TCP từ Wokwi."""

    def __init__(self) -> None:
        self._state = "data"

    def feed(self, chunk: bytes) -> bytes:
        out = bytearray()
        for byte in chunk:
            if self._state == "data":
                if byte == 0xFF:
                    self._state = "iac"
                else:
                    out.append(byte)
            elif self._state == "iac":
                if byte == 0xFF:
                    out.append(0xFF)
                    self._state = "data"
                elif byte == 0xFA:
                    self._state = "sb"
                elif byte in (0xFB, 0xFC, 0xFD, 0xFE):
                    self._state = "opt"
                else:
                    self._state = "data"
            elif self._state == "opt":
                self._state = "data"
            elif self._state == "sb":
                if byte == 0xFF:
                    self._state = "sb_iac"
            elif self._state == "sb_iac":
                if byte == 0xF0:
                    self._state = "data"
                elif byte != 0xFF:
                    self._state = "sb"
        return bytes(out)


def _parse_wokwi_serial_line(line: str) -> Optional[Dict[str, Any]]:
    idx = line.find(_TELEMETRY_PREFIX)
    if idx >= 0:
        raw_json = line[idx + len(_TELEMETRY_PREFIX) :].strip()
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return None

    match = _HUMAN_TELEMETRY_RE.search(line)
    if not match:
        return None

    ph, ec_ppm, water_temp, water_level_pct, pump_flow_lpm = (float(v) for v in match.groups())
    return {
        "readings": [
            {
                "sensor": {
                    "id": _WOKWI_TANK_ID,
                    "zone": "Living Room 1F",
                    "crop": "Neon Tetra & Guppy",
                    "system_type": "Canister Bio-Filter",
                },
                "ph": ph,
                "ec_ppm": round(ec_ppm),
                "water_temp": water_temp,
                "water_level_pct": water_level_pct,
                "pump_flow_lpm": pump_flow_lpm,
            }
        ]
    }


def _run_wokwi_bridge_session(stop_event: threading.Event) -> None:
    with socket.create_connection((_WOKWI_HOST, _WOKWI_PORT), timeout=2.0) as sock:
        sock.settimeout(0.25)
        decoder = _Rfc2217StreamDecoder()
        text_buffer = ""
        last_cmd_poll = 0.0
        last_sent_cmd = ""
        logger.info(
            "[WOKWI AUTO-BRIDGE] Đã kết nối tự động Wokwi %s:%s <-> Backend/MongoDB/Datadog",
            _WOKWI_HOST,
            _WOKWI_PORT,
        )

        while not stop_event.is_set():
            now = time.monotonic()
            fault_active = bool(_simulator_faults.get(_WOKWI_TANK_ID))
            bubbler_on = bool(_aquarium_actuators.get("bubbler_on", True))
            cmd = f"CMD:FAULT={1 if fault_active else 0},BUBBLER={1 if bubbler_on else 0}\n"
            if cmd != last_sent_cmd or (now - last_cmd_poll >= 1.5):
                last_cmd_poll = now
                sock.sendall(cmd.encode("ascii"))
                if cmd != last_sent_cmd:
                    last_sent_cmd = cmd
                    logger.info("[WOKWI AUTO-BRIDGE] Đồng bộ lệnh Web -> ESP32: %s", cmd.strip())

            try:
                chunk = sock.recv(4096)
            except (TimeoutError, socket.timeout):
                continue

            if not chunk:
                raise ConnectionResetError("Wokwi simulation đã ngắt kết nối.")

            clean_bytes = decoder.feed(chunk)
            if not clean_bytes:
                continue
            text_buffer += clean_bytes.decode("utf-8", errors="replace")

            while "\n" in text_buffer:
                raw_line, text_buffer = text_buffer.split("\n", 1)
                line = raw_line.strip("\r\n")
                if not line:
                    continue
                payload = _parse_wokwi_serial_line(line)
                if payload is None:
                    continue
                try:
                    batch = TelemetryBatch(**payload)
                    ingest_telemetry(batch)
                    r = batch.readings[0]
                    logger.info(
                        "[WOKWI AUTO-BRIDGE] Wokwi -> MongoDB & Datadog OK | pH=%.2f TDS=%s Temp=%s°C Lvl=%s%% Flow=%.2f LPM",
                        r.ph,
                        r.ec_ppm,
                        r.water_temp,
                        r.water_level_pct,
                        r.pump_flow_lpm,
                    )
                except Exception as exc:
                    logger.warning("[WOKWI AUTO-BRIDGE] Lỗi xử lý telemetry từ Wokwi: %s", exc)


def _wokwi_auto_bridge_worker(stop_event: threading.Event) -> None:
    waiting_logged = False
    while not stop_event.is_set():
        try:
            waiting_logged = False
            _run_wokwi_bridge_session(stop_event)
        except OSError:
            if not waiting_logged:
                logger.info(
                    "[WOKWI AUTO-BRIDGE] Đang chờ Wokwi mở cổng %s:%s (chỉ cần bấm Start Simulation)...",
                    _WOKWI_HOST,
                    _WOKWI_PORT,
                )
                waiting_logged = True
            stop_event.wait(1.5)
        except Exception as exc:
            logger.warning("[WOKWI AUTO-BRIDGE] Lỗi cầu nối: %s", exc)
            stop_event.wait(1.5)


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI):
    stop_event = threading.Event()
    bridge_thread: Optional[threading.Thread] = None
    if os.getenv("WOKWI_AUTO_BRIDGE", "1") != "0" and not os.getenv("RENDER"):
        bridge_thread = threading.Thread(
            target=_wokwi_auto_bridge_worker,
            args=(stop_event,),
            name="wokwi-auto-bridge",
            daemon=True,
        )
        bridge_thread.start()
    else:
        logger.info("[CLOUD MODE] Running on cloud environment — Wokwi local serial bridge disabled.")
    try:
        yield
    finally:
        stop_event.set()
        if bridge_thread is not None and bridge_thread.is_alive():
            bridge_thread.join(timeout=1.5)


app = FastAPI(
    title="Frutiger Aqua Smart Aquarium Real-time Operations API",
    description="Backend API kết hợp MongoDB Time Series và Datadog Observability cho Hệ thống Bể Cá Thông Minh",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTION_NAME = "aquarium_telemetry"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROL_FILE = PROJECT_ROOT / "simulator_control.json"

# Trạng thái điều khiển fault & actuator bể cá đồng bộ giữa Web UI, CLI, Simulator, Wokwi và Firebase
_simulator_faults: Dict[str, Optional[str]] = {}
_aquarium_actuators: Dict[str, Any] = {
    "bubbler_on": True,
    "last_fed_at": None,
    "filter_mode": "NORMAL",
}


def _set_simulator_fault(device_id: str, action: str, reason: str = "") -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    if action == "INJECT_FAULT":
        _simulator_faults[device_id] = "CLOG_AND_PH_DRIFT"
        _aquarium_actuators["filter_mode"] = "CLOGGED"
    elif action == "RESOLVE":
        _simulator_faults[device_id] = None
        _aquarium_actuators["filter_mode"] = "NORMAL"
    elif action == "FEED_FISH":
        _aquarium_actuators["last_fed_at"] = now_iso
    elif action == "TOGGLE_BUBBLER":
        _aquarium_actuators["bubbler_on"] = not _aquarium_actuators["bubbler_on"]

    cmd = {
        "device_id": device_id,
        "action": action,
        "reason": reason,
        "updated_at": now_iso,
        "actuators": dict(_aquarium_actuators),
    }
    if action in ("INJECT_FAULT", "RESOLVE"):
        try:
            CONTROL_FILE.write_text(json.dumps(cmd, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.debug("Không ghi được file simulator_control.json: %s", exc)
    return cmd


def _resolve_device_incident(
    db: Any,
    device_id: str,
    action: str,
    notes: Optional[str],
    trace_ctx: Dict[str, str],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    _set_simulator_fault(device_id, "RESOLVE", reason=action)

    mttr_seconds: Optional[float] = None
    active_inc = db.incidents.find_one({"device_id": device_id, "status": "ACTIVE"})
    if isinstance(active_inc, dict) and active_inc.get("detected_at"):
        detected_at = active_inc["detected_at"]
        if isinstance(detected_at, datetime):
            if detected_at.tzinfo is None:
                detected_at = detected_at.replace(tzinfo=timezone.utc)
            mttr_seconds = round(max(0.0, (now - detected_at).total_seconds()), 2)
        db.incidents.update_one(
            {"_id": active_inc["_id"]},
            {
                "$set": {
                    "status": "RESOLVED",
                    "action": action,
                    "notes": notes,
                    "resolved_at": now,
                    "mttr_seconds": mttr_seconds,
                }
            },
        )
    else:
        db.incidents.insert_one(
            {
                "device_id": device_id,
                "action": action,
                "notes": notes,
                "detected_at": now,
                "resolved_at": now,
                "mttr_seconds": 0.0,
                "status": "RESOLVED",
            }
        )

    mttr_info = f" (MTTR={mttr_seconds}s)" if mttr_seconds is not None else ""
    resolve_msg = (
        f"[INCIDENT_RESOLVED] Đã thực thi hành động khắc phục cho {device_id}: {action}{mttr_info}. "
        "Lưu lượng bơm và độ pH đang phục hồi về vùng lý tưởng."
    )
    logger.info(resolve_msg)

    send_log_to_datadog(
        resolve_msg,
        status="info",
        extra_tags=[f"rack_id:{device_id}"],
        trace_ctx=trace_ctx,
    )
    send_incident_event(
        title=f"Đã xử lý sự cố: {device_id}",
        text=resolve_msg,
        alert_type="success",
        extra_tags=[f"rack_id:{device_id}"],
    )
    if mttr_seconds is not None:
        send_mttr_metric_to_datadog(device_id=device_id, mttr_seconds=mttr_seconds)

    sync_state_to_firebase(
        "aquarium/control",
        {
            "faults": dict(_simulator_faults),
            "actuators": dict(_aquarium_actuators),
            "last_resolution": {
                "device_id": device_id,
                "action": action,
                "mttr_seconds": mttr_seconds,
                "resolved_at": now.isoformat(),
            },
        },
    )

    return {
        "status": "remediated",
        "action_taken": action,
        "device_id": device_id,
        "mttr_seconds": mttr_seconds,
        "message": f"Sự cố đã được khắc phục: {action}. Hệ sinh thái bể cá đang trở lại bình thường.",
    }


@app.get("/")
def serve_dashboard():
    static_file = Path(__file__).resolve().parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return JSONResponse({"message": "Smart Hydroponics Farm API running. Visit /docs for Swagger."})


@app.get("/data")
@app.get("/data.html")
def serve_data_page():
    static_file = Path(__file__).resolve().parent / "static" / "data.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return JSONResponse({"message": "Smart Aquarium Data page not found."})


@app.get("/slides")
@app.get("/slides.html")
def serve_slides_page():
    static_file = Path(__file__).resolve().parent / "static" / "slides.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return JSONResponse({"message": "Slides presentation not found."})


@app.get("/health")
def health_check():
    db_status = check_db_health()
    dd_ready = is_datadog_configured()
    fb_ready = is_firebase_configured()
    return {
        "status": "healthy" if db_status["status"] == "connected" else "degraded",
        "database": db_status,
        "datadog_connected": dd_ready,
        "firebase_connected": fb_ready,
        "service": os.getenv("DD_SERVICE", "smart-hydroponics-service"),
        "timestamp": datetime.now(timezone.utc),
    }


@app.post("/api/telemetry/ingest", status_code=status.HTTP_201_CREATED)
def ingest_telemetry(batch: TelemetryBatch):
    """
    Ingest batch dữ liệu cảm biến thủy canh:
    1. Ghi vào MongoDB Time Series Collection (insert_many ordered=False)
    2. Đẩy chỉ số thời gian thực + ingest latency lên Datadog Metrics API
    3. Tự động phát hiện nghẹt ống / kiềm hóa dung dịch, ghi incident ACTIVE và bắn Log/Event sang Datadog
    """
    if not batch.readings:
        raise HTTPException(status_code=400, detail="Batch rỗng")

    trace_ctx = get_current_trace_context()

    try:
        db = get_database()
        coll = db[COLLECTION_NAME]
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Lỗi kết nối MongoDB: {exc}")

    docs = [item.model_dump() for item in batch.readings]
    insert_docs = [dict(d) for d in docs]
    inserted_count = 0

    # 1. Lưu vào MongoDB Time Series và đo latency
    t0 = time.perf_counter()
    try:
        result = coll.insert_many(insert_docs, ordered=False)
        inserted_count = len(result.inserted_ids)
    except BulkWriteError as bwe:
        inserted_count = bwe.details.get("nInserted", 0)
        logger.warning("BulkWriteWarning: Chỉ ghi thành công %s/%s bản ghi", inserted_count, len(docs))
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Không thể ghi vào MongoDB Time Series: {exc}")
    ingest_latency_ms = (time.perf_counter() - t0) * 1000.0

    # 2. Kiểm tra ngưỡng nguy hiểm & ghi nhận sự cố (Detect)
    alert_count = 0
    for r in batch.readings:
        is_clogged = r.pump_flow_lpm < 1.0
        is_ph_drift = r.ph > 7.6 or r.ph < 5.0

        if is_clogged or is_ph_drift:
            alert_count += 1
            alert_type = (
                "TẮC NGHẼN LỌC TUẦN HOÀN"
                if is_clogged
                else "SỐC KIỀM HÓA pH NƯỚC BỂ CÁ"
            )
            alert_msg = (
                f"[AQUA_ALERT] Bể {r.sensor.id} ({r.sensor.crop} - {r.sensor.zone}): {alert_type}! "
                f"Lưu lượng={r.pump_flow_lpm} LPM, pH={r.ph}, Mực nước={r.water_level_pct}%, TDS={r.ec_ppm} ppm"
            )
            logger.error(alert_msg)

            # Ghi nhận sự cố ACTIVE vào MongoDB nếu chưa có sự cố mở cho giàn này
            try:
                existing = db.incidents.find_one({"device_id": r.sensor.id, "status": "ACTIVE"})
                if not isinstance(existing, dict):
                    db.incidents.insert_one(
                        {
                            "device_id": r.sensor.id,
                            "crop": r.sensor.crop,
                            "zone": r.sensor.zone,
                            "alert_type": alert_type,
                            "severity": "P1",
                            "status": "ACTIVE",
                            "detected_at": datetime.now(timezone.utc),
                            "trigger_reading": {
                                "pump_flow_lpm": r.pump_flow_lpm,
                                "ph": r.ph,
                                "water_level_pct": r.water_level_pct,
                                "ec_ppm": r.ec_ppm,
                            },
                            "dd_trace_id": trace_ctx.get("trace_id"),
                        }
                    )
            except PyMongoError as exc:
                logger.warning("Không thể ghi incident ACTIVE vào MongoDB: %s", exc)

            # Bắn Log (kèm trace_id) và Event trực tiếp sang Datadog
            send_log_to_datadog(
                alert_msg,
                status="error",
                extra_tags=[f"rack_id:{r.sensor.id}", f"crop:{r.sensor.crop}"],
                trace_ctx=trace_ctx,
            )
            send_incident_event(
                title=f"Cảnh báo: {r.sensor.id} ({alert_type})",
                text=alert_msg,
                alert_type="error",
                extra_tags=[f"rack_id:{r.sensor.id}", f"crop:{r.sensor.crop}"],
            )

    # 3. Đẩy Metrics (sensor + ingest latency + alert count) sang Datadog
    send_metrics_to_datadog(
        docs,
        ingest_latency_ms=ingest_latency_ms,
        alert_count=alert_count,
    )

    # 4. Đồng bộ snapshot mới nhất sang Firebase Realtime Database (nếu được cấu hình)
    latest_by_rack: Dict[str, Any] = {}
    for d in docs:
        sid = d["sensor"]["id"]
        ts_val = d["ts"].isoformat() if isinstance(d.get("ts"), datetime) else str(d.get("ts", ""))
        latest_by_rack[sid] = {
            "ts": ts_val,
            "sensor": d["sensor"],
            "ph": d["ph"],
            "ec_ppm": d["ec_ppm"],
            "water_temp": d["water_temp"],
            "water_level_pct": d["water_level_pct"],
            "pump_flow_lpm": d["pump_flow_lpm"],
        }
    sync_state_to_firebase(
        "aquarium/latest",
        {
            "racks": latest_by_rack,
            "alerts_triggered": alert_count,
            "actuators": dict(_aquarium_actuators),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "status": "success",
        "inserted_mongo": inserted_count,
        "ingest_latency_ms": round(ingest_latency_ms, 2),
        "alerts_triggered": alert_count,
        "sent_datadog": is_datadog_configured(),
        "total": len(docs),
    }


@app.get("/api/telemetry/latest")
def get_latest_telemetry(minutes: int = 120):
    """
    Lấy bản ghi telemetry thật mới nhất của từng giàn từ MongoDB Time Series Collection.
    """
    try:
        db = get_database()
        pipeline = get_latest_telemetry_pipeline(minutes=minutes)
        results = list(db[COLLECTION_NAME].aggregate(pipeline))
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Lỗi truy vấn MongoDB: {exc}")

    return {
        "count": len(results),
        "racks": results,
        "simulator_faults": _simulator_faults,
        "actuators": dict(_aquarium_actuators),
        "timestamp": datetime.now(timezone.utc),
    }


@app.get("/api/analytics/hourly")
def get_hourly_analytics(rack_id: Optional[str] = None, hours: int = 24):
    """
    Chạy Aggregation Pipeline tính toán chỉ số trung bình theo từng giờ của các giàn.
    """
    try:
        db = get_database()
        pipeline = get_hourly_summary_pipeline(rack_id=rack_id, hours=hours)
        results = list(db[COLLECTION_NAME].aggregate(pipeline))
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Lỗi truy vấn MongoDB Aggregation: {exc}")

    return {
        "query_hours": hours,
        "rack_id": rack_id,
        "count": len(results),
        "data": results,
    }


@app.get("/api/analytics/trend")
def get_trend_analytics(rack_id: str = "AQUA-TANK-01", minutes: int = 30):
    """
    Chạy Window Functions ($setWindowFields) tính moving average lưu lượng và pH 5 mẫu gần nhất.
    """
    try:
        db = get_database()
        pipeline = get_trend_and_anomalies_pipeline(rack_id=rack_id, minutes=minutes)
        results = list(db[COLLECTION_NAME].aggregate(pipeline))
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Lỗi truy vấn MongoDB Window Fields: {exc}")

    return {
        "rack_id": rack_id,
        "window_minutes": minutes,
        "count": len(results),
        "data": results,
    }


@app.get("/api/simulator/state")
def get_simulator_state():
    """Trả về trạng thái fault và actuator hiện tại để Edge Simulator / Wokwi đồng bộ với Web UI."""
    return {"faults": _simulator_faults, "actuators": dict(_aquarium_actuators)}


@app.post("/api/simulator/control")
def control_simulator(req: SimulatorControlRequest):
    """
    Điều khiển trạng thái lỗi và actuator bể cá từ Web UI, Firebase hoặc CLI.
    Khi INJECT_FAULT: Simulator/Wokwi thật sẽ giảm lưu lượng & tăng pH -> MongoDB -> Datadog Alert nổ thật.
    """
    cmd = _set_simulator_fault(req.device_id, req.action, req.reason or "")
    trace_ctx = get_current_trace_context()

    if req.action == "INJECT_FAULT":
        msg = f"[FAULT_INJECTED] Kích hoạt mô phỏng sự cố trên {req.device_id}: {req.reason}"
        logger.warning(msg)
        send_log_to_datadog(msg, status="warn", extra_tags=[f"rack_id:{req.device_id}"], trace_ctx=trace_ctx)
    elif req.action == "FEED_FISH":
        msg = f"[AQUARIUM_ACTION] Kích hoạt cho cá ăn tự động tại {req.device_id}"
        logger.info(msg)
        send_log_to_datadog(msg, status="info", extra_tags=[f"rack_id:{req.device_id}", "action:feed_fish"], trace_ctx=trace_ctx)
        send_incident_event(
            title=f"Cho cá ăn tự động: {req.device_id}",
            text=msg,
            alert_type="info",
            extra_tags=[f"rack_id:{req.device_id}"],
        )
    elif req.action == "TOGGLE_BUBBLER":
        state_str = "ON" if _aquarium_actuators["bubbler_on"] else "OFF"
        msg = f"[AQUARIUM_ACTION] Chuyển trạng thái sục khí Oxy (Bubbler) thành {state_str} cho {req.device_id}"
        logger.info(msg)
        send_log_to_datadog(msg, status="info", extra_tags=[f"rack_id:{req.device_id}", f"bubbler:{state_str}"], trace_ctx=trace_ctx)
    else:
        msg = f"[FAULT_CLEARED] Đã tắt chế độ lỗi trên {req.device_id}"
        logger.info(msg)

    sync_state_to_firebase(
        "aquarium/control",
        {
            "faults": dict(_simulator_faults),
            "actuators": dict(_aquarium_actuators),
            "last_command": cmd,
        },
    )

    return {
        "status": "ok",
        "command": cmd,
        "faults": _simulator_faults,
        "actuators": dict(_aquarium_actuators),
    }


@app.post("/api/incident/respond")
def respond_incident(req: IncidentActionRequest):
    """
    Endpoint phản ứng khắc phục sự cố (Respond - Bước 3 trong đề bài).
    Tắt fault trên simulator, cập nhật incident ACTIVE -> RESOLVED trong MongoDB và tính MTTR.
    """
    trace_ctx = get_current_trace_context()
    try:
        db = get_database()
        return _resolve_device_incident(
            db=db,
            device_id=req.device_id,
            action=req.action,
            notes=req.notes,
            trace_ctx=trace_ctx,
        )
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Lỗi lưu hành động khắc phục vào MongoDB: {exc}")


@app.post("/api/webhooks/datadog")
def receive_datadog_webhook(payload: DatadogWebhookPayload):
    """
    Webhook nhận cảnh báo tự động từ Datadog Monitor (DDMon -> ResAPI trong kiến trúc).
    Khi Monitor chuyển trạng thái Triggered, có thể tự động kích hoạt quy trình khắc phục sự cố.
    """
    trace_ctx = get_current_trace_context()
    device_id = payload.device_id or payload.rack_id
    if not device_id and payload.tags:
        for tag in payload.tags.split(","):
            tag = tag.strip()
            if tag.startswith("rack_id:"):
                device_id = tag.split(":", 1)[1]
                break
    device_id = device_id or "AQUA-TANK-01"

    transition = (payload.alert_transition or payload.alert_status or "").lower()
    webhook_msg = (
        f"[DATADOG_WEBHOOK] Nhận webhook từ Monitor '{payload.alert_title or 'Farm Alert'}' "
        f"(transition={payload.alert_transition}, device={device_id})"
    )
    logger.info(webhook_msg)
    send_log_to_datadog(
        webhook_msg,
        status="info",
        extra_tags=[f"rack_id:{device_id}", "source:datadog_webhook"],
        trace_ctx=trace_ctx,
    )

    remediation = None
    if payload.auto_remediate and ("triggered" in transition or "alert" in transition):
        try:
            db = get_database()
            remediation = _resolve_device_incident(
                db=db,
                device_id=device_id,
                action="AUTO_WEBHOOK_REVERSE_FLUSH_AND_PH_DOWN",
                notes=f"Tự động kích hoạt từ Datadog Monitor Webhook ({payload.alert_title or 'N/A'})",
                trace_ctx=trace_ctx,
            )
        except PyMongoError as exc:
            raise HTTPException(status_code=503, detail=f"Lỗi MongoDB khi xử lý webhook: {exc}")

    return {
        "status": "received",
        "device_id": device_id,
        "transition": payload.alert_transition,
        "remediation": remediation,
    }


@app.get("/api/incidents")
def list_incidents(limit: int = 20):
    try:
        db = get_database()
        incidents = list(
            db.incidents.find({}, {"_id": 0})
            .sort([("detected_at", -1), ("resolved_at", -1)])
            .limit(limit)
        )
        return {"count": len(incidents), "incidents": incidents}
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail=f"Lỗi truy vấn incidents từ MongoDB: {exc}")
