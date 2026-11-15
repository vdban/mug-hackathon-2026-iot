from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class SensorMeta(BaseModel):
    id: str = Field(..., description="ID của bể cá thông minh (ví dụ: AQUA-TANK-01)")
    zone: str = Field(..., description="Vị trí đặt bể ('Living Room 1F', 'Studio 2F', 'Balcony Lounge')")
    crop: str = Field(..., description="Hệ sinh thái cá & thủy sinh ('Neon Tetra & Guppy', 'Clownfish & Coral', 'Mini Koi & Moss')")
    system_type: Optional[str] = Field("Canister Bio-Filter", description="Kiểu hệ thống lọc bể cá")


class TelemetryPoint(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Thời điểm đo (ISODate)")
    sensor: SensorMeta
    ph: float = Field(..., ge=0.0, le=14.0, description="Độ pH nước bể cá (chuẩn an toàn 5.8 - 7.5)")
    ec_ppm: float = Field(..., ge=0.0, description="Độ tổng chất rắn hòa tan TDS/EC ppm")
    water_temp: float = Field(..., description="Nhiệt độ nước bể cá (°C)")
    water_level_pct: float = Field(..., ge=0.0, le=100.0, description="Mực nước bể cá (%)")
    pump_flow_lpm: float = Field(..., ge=0.0, description="Lưu lượng bơm lọc tuần hoàn (Lít/phút - chuẩn 3.5 - 5.0 LPM)")


class TelemetryBatch(BaseModel):
    readings: List[TelemetryPoint]


class IncidentActionRequest(BaseModel):
    device_id: str
    action: str = Field(..., description="Hành động xử lý: 'REVERSE_FLUSH_AND_DOSING_PH_DOWN', 'REVERSE_FLUSH', 'DOSING_PH_DOWN', 'REFILL_WATER'")
    notes: Optional[str] = "Kích hoạt xử lý tự động từ Frutiger Aqua Operations Controller"


class SimulatorControlRequest(BaseModel):
    device_id: str = Field(default="AQUA-TANK-01", description="ID bể cá mục tiêu")
    action: Literal["INJECT_FAULT", "RESOLVE", "FEED_FISH", "TOGGLE_BUBBLER"] = Field(
        ...,
        description="INJECT_FAULT để gây lỗi, RESOLVE để khôi phục, FEED_FISH cho cá ăn, TOGGLE_BUBBLER bật/tắt sục khí",
    )
    reason: Optional[str] = Field(default="FILTER_CLOG_AND_PH_SPIKE", description="Lý do điều khiển")


class DatadogWebhookPayload(BaseModel):
    """Schema linh hoạt tiếp nhận Webhook từ Datadog Monitor."""
    model_config = ConfigDict(extra="allow")

    alert_id: Optional[str] = None
    alert_title: Optional[str] = None
    alert_status: Optional[str] = None
    alert_transition: Optional[str] = None
    device_id: Optional[str] = None
    rack_id: Optional[str] = None
    tags: Optional[str] = None
    auto_remediate: bool = True
