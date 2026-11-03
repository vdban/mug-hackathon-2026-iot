from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

class SensorMeta(BaseModel):
    id: str = Field(..., description="ID của tủ lạnh (ví dụ: FRIDGE-KITCHEN-01)")
    compartment: str = Field(..., description="Ngăn tủ ('fridge' hoặc 'freezer')")
    model: Optional[str] = Field("SmartInverter-V2", description="Model thiết bị")

class TelemetryPoint(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Thời điểm đo (ISODate)")
    sensor: SensorMeta
    temperature: float = Field(..., description="Nhiệt độ hiện tại (°C)")
    humidity: float = Field(..., description="Độ ẩm (%)")
    door_open: bool = Field(False, description="Trạng thái cửa mở (True/False)")
    power_watts: float = Field(..., description="Công suất máy nén (Watts)")

class TelemetryBatch(BaseModel):
    readings: List[TelemetryPoint]

class IncidentActionRequest(BaseModel):
    device_id: str
    compartment: str
    action: str = Field(..., description="Hành động xử lý: 'CLOSE_DOOR', 'EMERGENCY_COOLING', 'MUTE_BUZZER'")
    notes: Optional[str] = "Thực hiện xử lý tự động qua API"
