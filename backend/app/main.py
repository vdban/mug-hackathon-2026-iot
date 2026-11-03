import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pymongo.errors import BulkWriteError

from app.database import get_database, check_db_health
from app.models import TelemetryBatch, IncidentActionRequest
from app.analytics import get_hourly_summary_pipeline, get_trend_and_anomalies_pipeline
from app.datadog_service import (
    is_datadog_configured,
    send_metrics_to_datadog,
    send_log_to_datadog,
    send_incident_event
)

# Setup logging chuẩn Datadog Log Injection
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger("smart_hydroponics_api")

app = FastAPI(
    title="Smart Hydroponics Farm Real-time Operations API",
    description="Backend API kết hợp MongoDB Time Series và Datadog Observability cho Nông nghiệp Đô thị Thông minh",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COLLECTION_NAME = "hydroponic_telemetry"

@app.get("/", response_class=FileResponse)
def serve_dashboard():
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "Smart Hydroponics Farm API running. Visit /docs for Swagger."}

@app.get("/health")
def health_check():
    db_status = check_db_health()
    dd_ready = is_datadog_configured()
    return {
        "status": "healthy" if db_status["status"] == "connected" else "degraded",
        "database": db_status,
        "datadog_connected": dd_ready,
        "service": os.getenv("DD_SERVICE", "smart-hydroponics-service"),
        "timestamp": datetime.now(timezone.utc)
    }

@app.post("/api/telemetry/ingest", status_code=status.HTTP_201_CREATED)
def ingest_telemetry(batch: TelemetryBatch):
    """
    Ingest batch dữ liệu cảm biến thủy canh:
    1. Ghi vào MongoDB Time Series Collection (insertMany ordered=False)
    2. Đẩy chỉ số thời gian thực lên Datadog Metrics API
    3. Tự động kiểm tra cảnh báo nghẹt ống / kiềm hóa dung dịch và bắn Event/Log lên Datadog
    """
    if not batch.readings:
        raise HTTPException(status_code=400, detail="Batch rỗng")

    db = get_database()
    coll = db[COLLECTION_NAME]

    docs = [item.model_dump() for item in batch.readings]
    inserted_count = 0

    # 1. Lưu vào MongoDB Time Series
    try:
        result = coll.insert_many(docs, ordered=False)
        inserted_count = len(result.inserted_ids)
    except BulkWriteError as bwe:
        inserted_count = bwe.details.get("nInserted", 0)
        logger.warning(f"BulkWriteWarning: Chỉ ghi thành công {inserted_count}/{len(docs)} bản ghi")

    # 2. Đẩy Metrics trực tiếp lên Datadog
    send_metrics_to_datadog(docs)

    # 3. Kiểm tra ngưỡng nguy hiểm: Lưu lượng bơm < 1.0 LPM (tắc ống) hoặc pH > 7.5 (khóa hấp thụ dinh dưỡng)
    for r in batch.readings:
        is_clogged = r.pump_flow_lpm < 1.0
        is_ph_drift = r.ph > 7.6 or r.ph < 5.0

        if is_clogged or is_ph_drift:
            alert_type = "TẮC NGHẼN ỐNG HỒI LƯU" if is_clogged else "KIỀM HÓA DUNG DỊCH (KHÓA DINH DƯỠNG)"
            alert_msg = (
                f"[FARM_ALERT] Giàn {r.sensor.id} ({r.sensor.crop} - {r.sensor.zone}): {alert_type}! "
                f"Lưu lượng={r.pump_flow_lpm} LPM, pH={r.ph}, Mực nước={r.water_level_pct}%, EC={r.ec_ppm} ppm"
            )
            logger.error(alert_msg)

            # Bắn Log và Event trực tiếp sang Datadog
            send_log_to_datadog(
                alert_msg,
                status="error",
                extra_tags=[f"rack_id:{r.sensor.id}", f"crop:{r.sensor.crop}"]
            )
            send_incident_event(
                title=f"Cảnh báo: {r.sensor.id} ({alert_type})",
                text=alert_msg,
                alert_type="error"
            )

    return {
        "status": "success",
        "inserted_mongo": inserted_count,
        "sent_datadog": is_datadog_configured(),
        "total": len(docs)
    }

@app.get("/api/analytics/hourly")
def get_hourly_analytics(rack_id: str = None, hours: int = 24):
    """
    Chạy Aggregation Pipeline tính toán chỉ số trung bình theo từng giờ của các giàn
    """
    db = get_database()
    pipeline = get_hourly_summary_pipeline(rack_id=rack_id, hours=hours)
    results = list(db[COLLECTION_NAME].aggregate(pipeline))
    return {
        "query_hours": hours,
        "rack_id": rack_id,
        "count": len(results),
        "data": results
    }

@app.get("/api/analytics/trend")
def get_trend_analytics(rack_id: str = "HYDROPONIC-RACK-01", minutes: int = 30):
    """
    Chạy Window Functions ($setWindowFields) tính moving average lưu lượng và pH 5 mẫu gần nhất
    """
    db = get_database()
    pipeline = get_trend_and_anomalies_pipeline(rack_id=rack_id, minutes=minutes)
    results = list(db[COLLECTION_NAME].aggregate(pipeline))
    return {
        "rack_id": rack_id,
        "window_minutes": minutes,
        "data": results
    }

@app.post("/api/incident/respond")
def respond_incident(req: IncidentActionRequest):
    """
    Endpoint phản ứng khắc phục sự cố (Respond - Bước 3 trong đề bài).
    Hành động: Tự động xả ngược đường ống (REVERSE_FLUSH) / Bơm cân bằng pH (DOSING_PH_DOWN).
    """
    db = get_database()
    incident_record = {
        "device_id": req.device_id,
        "action": req.action,
        "notes": req.notes,
        "resolved_at": datetime.now(timezone.utc),
        "status": "RESOLVED"
    }
    db.incidents.insert_one(incident_record)
    
    resolve_msg = (
        f"[INCIDENT_RESOLVED] Đã thực thi hành động khắc phục cho {req.device_id}: {req.action}. "
        f"Lưu lượng bơm và độ pH đang phục hồi về vùng lý tưởng."
    )
    logger.info(resolve_msg)

    # Gửi tín hiệu giải quyết sự cố lên Datadog
    send_log_to_datadog(resolve_msg, status="info", extra_tags=[f"rack_id:{req.device_id}"])
    send_incident_event(
        title=f"Đã xử lý sự cố: {req.device_id}",
        text=resolve_msg,
        alert_type="success"
    )

    return {
        "status": "remediated",
        "action_taken": req.action,
        "device_id": req.device_id,
        "message": f"Sự cố đã được khắc phục: {req.action}. Hệ sinh thái thủy canh đang trở lại bình thường."
    }

@app.get("/api/incidents")
def list_incidents(limit: int = 20):
    db = get_database()
    incidents = list(db.incidents.find({}, {"_id": 0}).sort("resolved_at", -1).limit(limit))
    return {"incidents": incidents}
