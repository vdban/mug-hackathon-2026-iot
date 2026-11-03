"""
MongoDB Aggregation Pipelines for Smart Hydroponics Analytics & Anomaly Detection.
Tuân thủ toàn bộ kỹ thuật trong Workshop của MongoDB (Slides 16-20):
- Bắt đầu với $match trên metaField và timeField để skip buckets.
- Sử dụng $dateTrunc với timezone 'Asia/Ho_Chi_Minh'.
- Sử dụng $setWindowFields tính moving average (trung bình trượt) lưu lượng bơm và độ pH.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

def get_hourly_summary_pipeline(rack_id: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
    """
    Aggregation Pipeline tính chỉ số trung bình theo từng giờ của các giàn thủy canh.
    (Slide 18 trong workshop)
    """
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    match_stage: Dict[str, Any] = {
        "ts": {"$gte": start_time}
    }
    if rack_id:
        match_stage["sensor.id"] = rack_id

    pipeline = [
        # 1. $match stage đầu tiên để tận dụng index và skip bucket (Slide 16)
        {"$match": match_stage},

        # 2. $group gom theo từng giờ với múi giờ Việt Nam
        {
            "$group": {
                "_id": {
                    "rack": "$sensor.id",
                    "crop": "$sensor.crop",
                    "zone": "$sensor.zone",
                    "hour": {
                        "$dateTrunc": {
                            "date": "$ts",
                            "unit": "hour",
                            "timezone": "Asia/Ho_Chi_Minh"
                        }
                    }
                },
                "avgPh": {"$avg": "$ph"},
                "minPh": {"$min": "$ph"},
                "maxPh": {"$max": "$ph"},
                "avgEc": {"$avg": "$ec_ppm"},
                "avgFlow": {"$avg": "$pump_flow_lpm"},
                "avgWaterLevel": {"$avg": "$water_level_pct"},
                "totalSamples": {"$count": {}}
            }
        },

        # 3. $sort sắp xếp thời gian tăng dần
        {"$sort": {"_id.hour": 1}},

        # 4. $project định dạng lại kết quả
        {
            "$project": {
                "_id": 0,
                "rack": "$_id.rack",
                "crop": "$_id.crop",
                "zone": "$_id.zone",
                "hour": "$_id.hour",
                "avgPh": {"$round": ["$avgPh", 2]},
                "minPh": {"$round": ["$minPh", 2]},
                "maxPh": {"$round": ["$maxPh", 2]},
                "avgEcPpm": {"$round": ["$avgEc", 0]},
                "avgFlowLpm": {"$round": ["$avgFlow", 2]},
                "avgWaterLevelPct": {"$round": ["$avgWaterLevel", 1]},
                "totalReadings": "$totalSamples"
            }
        }
    ]
    return pipeline


def get_trend_and_anomalies_pipeline(rack_id: str, minutes: int = 30) -> List[Dict[str, Any]]:
    """
    Sử dụng $setWindowFields (Slide 19) để tính Moving Average của Lưu lượng Bơm (LPM) và pH
    trong 5 mẫu gần nhất nhằm bắt sớm hiện tượng tắc nghẽn ống hồi lưu và kiềm hóa dung dịch.
    """
    start_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    pipeline = [
        {
            "$match": {
                "sensor.id": rack_id,
                "ts": {"$gte": start_time}
            }
        },
        {"$sort": {"ts": 1}},
        {
            "$setWindowFields": {
                "sortBy": {"ts": 1},
                "output": {
                    "movingAvgFlow": {
                        "$avg": "$pump_flow_lpm",
                        "window": {
                            "documents": [-4, 0]  # Trung bình trượt 5 mẫu
                        }
                    },
                    "movingAvgPh": {
                        "$avg": "$ph",
                        "window": {
                            "documents": [-4, 0]
                        }
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "ts": 1,
                "ph": 1,
                "movingAvgPh": {"$round": ["$movingAvgPh", 2]},
                "pump_flow_lpm": 1,
                "movingAvgFlowLpm": {"$round": ["$movingAvgFlow", 2]},
                "water_level_pct": 1,
                "ec_ppm": 1
            }
        }
    ]
    return pipeline
