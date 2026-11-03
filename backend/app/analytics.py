"""
MongoDB Aggregation Pipelines for Real-time Analytics & Anomaly Detection.
Tuân thủ toàn bộ kỹ thuật trong Workshop của MongoDB (Slides 16-20):
- Bắt đầu với $match trên metaField và timeField để skip buckets.
- Sử dụng $dateTrunc với timezone 'Asia/Ho_Chi_Minh'.
- Sử dụng $setWindowFields tính moving average (trung bình trượt).
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

def get_hourly_summary_pipeline(device_id: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Aggregation Pipeline tính nhiệt độ trung bình, min, max theo từng giờ.
    (Slide 18 trong workshop)
    """
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    match_stage: Dict[str, Any] = {
        "ts": {"$gte": start_time}
    }
    if device_id:
        match_stage["sensor.id"] = device_id

    pipeline = [
        # 1. $match stage đầu tiên để tận dụng index và skip bucket (Slide 16)
        {"$match": match_stage},

        # 2. $group gom theo từng giờ với múi giờ Việt Nam
        {
            "$group": {
                "_id": {
                    "device": "$sensor.id",
                    "compartment": "$sensor.compartment",
                    "hour": {
                        "$dateTrunc": {
                            "date": "$ts",
                            "unit": "hour",
                            "timezone": "Asia/Ho_Chi_Minh"
                        }
                    }
                },
                "avgTemp": {"$avg": "$temperature"},
                "minTemp": {"$min": "$temperature"},
                "maxTemp": {"$max": "$temperature"},
                "avgPower": {"$avg": "$power_watts"},
                "doorOpenSamples": {
                    "$sum": {"$cond": ["$door_open", 1, 0]}
                },
                "totalSamples": {"$count": {}}
            }
        },

        # 3. $sort sắp xếp thời gian tăng dần
        {"$sort": {"_id.hour": 1}},

        # 4. $project định dạng lại kết quả sạch đẹp
        {
            "$project": {
                "_id": 0,
                "device": "$_id.device",
                "compartment": "$_id.compartment",
                "hour": "$_id.hour",
                "avgTemperature": {"$round": ["$avgTemp", 1]},
                "minTemperature": {"$round": ["$minTemp", 1]},
                "maxTemperature": {"$round": ["$maxTemp", 1]},
                "avgPowerWatts": {"$round": ["$avgPower", 1]},
                "doorOpenRatePercent": {
                    "$round": [
                        {"$multiply": [{"$divide": ["$doorOpenSamples", "$totalSamples"]}, 100]},
                        1
                    ]
                },
                "totalReadings": "$totalSamples"
            }
        }
    ]
    return pipeline


def get_trend_and_anomalies_pipeline(device_id: str, compartment: str = "fridge", minutes: int = 30) -> List[Dict[str, Any]]:
    """
    Sử dụng $setWindowFields (Slide 19) để tính Moving Average của nhiệt độ trong 5 mẫu gần nhất
    nhằm phát hiện sớm xu hướng tăng nhiệt đột biến trước khi chạm ngưỡng báo động.
    """
    start_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    pipeline = [
        {
            "$match": {
                "sensor.id": device_id,
                "sensor.compartment": compartment,
                "ts": {"$gte": start_time}
            }
        },
        {"$sort": {"ts": 1}},
        {
            "$setWindowFields": {
                "sortBy": {"ts": 1},
                "output": {
                    "movingAvgTemp": {
                        "$avg": "$temperature",
                        "window": {
                            "documents": [-4, 0]  # Trung bình trượt của 5 điểm dữ liệu liên tiếp
                        }
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "ts": 1,
                "temperature": 1,
                "movingAvgTemp": {"$round": ["$movingAvgTemp", 2]},
                "door_open": 1,
                "power_watts": 1
            }
        }
    ]
    return pipeline
