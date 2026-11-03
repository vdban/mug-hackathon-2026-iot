from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field

class SensorMeta(BaseModel):
    id: str = Field(..., description="ID của giàn thủy canh (ví dụ: HYDROPONIC-RACK-01)")
    zone: str = Field(..., description="Khu vực đặt giàn ('Balcony 1F', 'Rooftop', 'Indoor Kitchen')")
    crop: str = Field(..., description="Loại cây trồng ('Lettuce', 'Strawberries', 'Herbs')")
    system_type: Optional[str] = Field("NFT-Vertical", description="Kiểu hệ thống: NFT, DWC, Aeroponics")

class TelemetryPoint(BaseModel):
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Thời điểm đo (ISODate)")
    sensor: SensorMeta
    ph: float = Field(..., description="Độ pH dung dịch dinh dưỡng (chuẩn 5.8 - 6.5)")
    ec_ppm: float = Field(..., description="Độ dẫn điện / nồng độ dinh dưỡng ppm (chuẩn 800 - 1200 ppm)")
    water_temp: float = Field(..., description="Nhiệt độ nước dinh dưỡng (°C)")
    water_level_pct: float = Field(..., description="Mực nước bồn chứa (%)")
    pump_flow_lpm: float = Field(..., description="Lưu lượng bơm tuần hoàn (Lít/phút - chuẩn 3.5 - 5.0 LPM)")

class TelemetryBatch(BaseModel):
    readings: List[TelemetryPoint]

class IncidentActionRequest(BaseModel):
    device_id: str
    action: str = Field(..., description="Hành động xử lý: 'REVERSE_FLUSH', 'DOSING_PH_DOWN', 'REFILL_WATER'")
    notes: Optional[str] = "Kích hoạt xử lý tự động từ Farm Operations Controller"
