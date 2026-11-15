"""
MongoDB Atlas Initial Setup Script for Smart Aquarium Operations (Frutiger Aqua Edition).
Tạo Time Series Collection, TTL Index, thiết bị bể cá mẫu và dọn database mẫu cũ.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)

MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DB_NAME = os.getenv("MONGODB_DATABASE", "smart_aquarium_iot").strip()
COLLECTION_NAME = "aquarium_telemetry"

if not MONGODB_URI or "xxxxx" in MONGODB_URI:
    print("❌ Lỗi: Vui lòng điền MONGODB_URI hợp lệ trong file .env trước khi chạy script!")
    exit(1)


def setup_database():
    print(f"Connecting to MongoDB Atlas: {DB_NAME}...")
    client = MongoClient(MONGODB_URI)

    # Dọn database thủy canh mẫu cũ nếu từng khởi tạo trước đó
    if DB_NAME != "smart_hydroponics_iot" and "smart_hydroponics_iot" in client.list_database_names():
        client.drop_database("smart_hydroponics_iot")
        print("🧹 Đã dọn database cũ 'smart_hydroponics_iot' trên MongoDB Atlas.")

    db = client[DB_NAME]

    # 1. Tạo Time Series Collection cho Bể Cá Thông Minh
    try:
        db.create_collection(
            COLLECTION_NAME,
            timeseries={
                "timeField": "ts",
                "metaField": "sensor",
                "granularity": "seconds",
            },
            expireAfterSeconds=604800,  # TTL 7 ngày
        )
        print(f"✅ Đã tạo Time Series Collection: '{COLLECTION_NAME}' (granularity=seconds, TTL=7 days)")
    except CollectionInvalid:
        print(f"ℹ️  Collection '{COLLECTION_NAME}' đã tồn tại sẵn.")

    # 2. Tạo Compound Index hỗ trợ truy vấn nhanh
    coll = db[COLLECTION_NAME]
    coll.create_index([("sensor.id", 1), ("ts", -1)])
    coll.create_index([("sensor.crop", 1), ("ts", -1)])
    print("✅ Đã tạo compound index: [('sensor.id', 1), ('ts', -1)] và [('sensor.crop', 1), ('ts', -1)]")

    # 3. Tạo collection thường lưu nhật ký sự cố & MTTR
    if "incidents" not in db.list_collection_names():
        db.create_collection("incidents")
        print("✅ Đã tạo Collection thường: 'incidents' (nhật ký xử lý sự cố bể cá)")

    # 4. Cập nhật danh sách 3 bể cá thông minh trong collection 'devices'
    if "devices" not in db.list_collection_names():
        db.create_collection("devices")
    sample_tanks = [
        {
            "id": "AQUA-TANK-01",
            "name": "Bể Thủy Sinh Frutiger Aqua",
            "zone": "Living Room 1F",
            "crop": "Neon Tetra & Guppy",
            "system": "Canister Bio-Filter",
            "status": "ONLINE",
        },
        {
            "id": "AQUA-TANK-02",
            "name": "Bể San Hô Reef Glow",
            "zone": "Studio 2F",
            "crop": "Clownfish & Coral",
            "system": "Sump Protein Skimmer",
            "status": "ONLINE",
        },
        {
            "id": "AQUA-TANK-03",
            "name": "Bể Cá Koi & Thủy Sinh Mini",
            "zone": "Balcony Lounge",
            "crop": "Mini Koi & Moss",
            "system": "Overflow UV Filter",
            "status": "ONLINE",
        },
    ]
    db.devices.delete_many({})
    db.devices.insert_many(sample_tanks)
    print(f"✅ Đã khởi tạo {len(sample_tanks)} bể cá thông minh trong collection 'devices'")

    # 5. Bơm 1 batch dữ liệu bể cá ban đầu nếu Time Series Collection đang trống
    if coll.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        initial_readings = [
            {
                "ts": now,
                "sensor": {
                    "id": "AQUA-TANK-01",
                    "zone": "Living Room 1F",
                    "crop": "Neon Tetra & Guppy",
                    "system_type": "Canister Bio-Filter",
                },
                "ph": 6.8,
                "ec_ppm": 320.0,
                "water_temp": 25.4,
                "water_level_pct": 90.0,
                "pump_flow_lpm": 4.5,
            },
            {
                "ts": now,
                "sensor": {
                    "id": "AQUA-TANK-02",
                    "zone": "Studio 2F",
                    "crop": "Clownfish & Coral",
                    "system_type": "Sump Protein Skimmer",
                },
                "ph": 7.1,
                "ec_ppm": 1050.0,
                "water_temp": 25.8,
                "water_level_pct": 88.0,
                "pump_flow_lpm": 4.2,
            },
            {
                "ts": now,
                "sensor": {
                    "id": "AQUA-TANK-03",
                    "zone": "Balcony Lounge",
                    "crop": "Mini Koi & Moss",
                    "system_type": "Overflow UV Filter",
                },
                "ph": 7.0,
                "ec_ppm": 410.0,
                "water_temp": 24.6,
                "water_level_pct": 92.0,
                "pump_flow_lpm": 4.8,
            },
        ]
        coll.insert_many(initial_readings)
        print("✅ Đã ghi 3 mẫu telemetry bể cá ban đầu vào 'aquarium_telemetry'")

    print("\n🎉 Khởi tạo cơ sở dữ liệu Bể Cá Thông Minh (smart_aquarium_iot) trên MongoDB Atlas hoàn tất!")


if __name__ == "__main__":
    setup_database()
