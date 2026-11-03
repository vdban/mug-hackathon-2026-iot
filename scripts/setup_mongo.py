"""
MongoDB Atlas Initial Setup Script for Smart Hydroponics Farm Project.
Tạo Time Series Collection và cấu hình TTL Index theo đúng chuẩn Workshop MongoDB.
"""

import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DATABASE", "smart_hydroponics_iot")
COLLECTION_NAME = "hydroponic_telemetry"

if not MONGODB_URI or "xxxxx" in MONGODB_URI:
    print("❌ Lỗi: Vui lòng điền MONGODB_URI hợp lệ trong file .env trước khi chạy script!")
    exit(1)

def setup_database():
    print(f"Connecting to MongoDB Atlas: {DB_NAME}...")
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    # 1. Tạo Time Series Collection
    try:
        db.create_collection(
            COLLECTION_NAME,
            timeseries={
                "timeField": "ts",          # Bắt buộc: trường lưu datetime
                "metaField": "sensor",      # Bắt buộc: { id, zone, crop, system_type }
                "granularity": "seconds"    # 'seconds' vì sensor gửi mỗi 2 giây
            },
            expireAfterSeconds=604800       # TTL 7 ngày (Slide 23)
        )
        print(f"✅ Đã tạo Time Series Collection: '{COLLECTION_NAME}' (granularity=seconds, TTL=7 days)")
    except CollectionInvalid:
        print(f"ℹ️  Collection '{COLLECTION_NAME}' đã tồn tại sẵn.")

    # 2. Tạo Compound Index hỗ trợ truy vấn nhanh (Slide 20)
    coll = db[COLLECTION_NAME]
    coll.create_index([("sensor.id", 1), ("ts", -1)])
    coll.create_index([("sensor.crop", 1), ("ts", -1)])
    print("✅ Đã tạo compound index: [('sensor.id', 1), ('ts', -1)] và [('sensor.crop', 1), ('ts', -1)]")

    # 3. Tạo collection thường lưu metadata và lịch sử sự cố
    if "incidents" not in db.list_collection_names():
        db.create_collection("incidents")
        print("✅ Đã tạo Collection thường: 'incidents' (nhật ký xử lý sự cố)")

    if "devices" not in db.list_collection_names():
        db.create_collection("devices")
        sample_racks = [
            {"id": "HYDROPONIC-RACK-01", "name": "Giàn Xà lách Ban công", "zone": "Balcony 1F", "crop": "Lettuce", "system": "NFT-Vertical", "status": "ONLINE"},
            {"id": "HYDROPONIC-RACK-02", "name": "Giàn Dâu tây Sân thượng", "zone": "Rooftop 3F", "crop": "Strawberries", "system": "Drip-Hydroponics", "status": "ONLINE"},
            {"id": "HYDROPONIC-RACK-03", "name": "Giàn Rau mầm Bếp", "zone": "Indoor Kitchen", "crop": "Herbs", "system": "Aeroponics-Rack", "status": "ONLINE"}
        ]
        db.devices.insert_many(sample_racks)
        print(f"✅ Đã khởi tạo {len(sample_racks)} giàn thủy canh mẫu trong collection 'devices'")

    print("\n🎉 Khởi tạo cơ sở dữ liệu MongoDB Atlas hoàn tất thành công!")

if __name__ == "__main__":
    setup_database()
