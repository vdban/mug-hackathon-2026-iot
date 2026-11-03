"""
MongoDB Atlas Initial Setup Script for Smart Fridge IoT Project.
Tạo Time Series Collection và cấu hình TTL Index theo đúng chuẩn Workshop MongoDB.
"""

import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DATABASE", "smart_fridge_iot")
COLLECTION_NAME = "fridge_telemetry"

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
                "metaField": "sensor",      # Bắt buộc theo best practice: { id, compartment, type }
                "granularity": "seconds"    # 'seconds' vì sensor gửi vài giây/lần
            },
            expireAfterSeconds=604800       # TTL 7 ngày: tự động dọn dẹp dữ liệu cũ (Slide 23)
        )
        print(f"✅ Đã tạo Time Series Collection: '{COLLECTION_NAME}' (granularity=seconds, TTL=7 days)")
    except CollectionInvalid:
        print(f"ℹ️  Collection '{COLLECTION_NAME}' đã tồn tại sẵn.")

    # 2. Tạo Index bổ trợ cho truy vấn nhanh (Slide 20: Add index that matches your filter)
    coll = db[COLLECTION_NAME]
    coll.create_index([("sensor.id", 1), ("ts", -1)])
    coll.create_index([("sensor.compartment", 1), ("ts", -1)])
    print("✅ Đã tạo compound index: [('sensor.id', 1), ('ts', -1)] và [('sensor.compartment', 1), ('ts', -1)]")

    # 3. Tạo collection thường lưu metadata và cảnh báo incidents (Slide 26: Records you edit go in a normal one)
    if "incidents" not in db.list_collection_names():
        db.create_collection("incidents")
        print("✅ Đã tạo Collection thường: 'incidents' (để lưu nhật ký xử lý sự cố)")

    if "devices" not in db.list_collection_names():
        db.create_collection("devices")
        # Khởi tạo thông tin 3 tủ lạnh mẫu
        sample_devices = [
            {"id": "FRIDGE-KITCHEN-01", "name": "Tủ lạnh Bếp chính", "location": "Kitchen 1F", "model": "Inverter Pro 550L", "status": "ONLINE"},
            {"id": "FRIDGE-LIVING-02", "name": "Tủ lạnh Mini Phòng khách", "location": "Living Room 1F", "model": "Compact 120L", "status": "ONLINE"},
            {"id": "FRIDGE-PANTRY-03", "name": "Tủ lạnh Đồ tươi Kho", "location": "Pantry 2F", "model": "DeepFreezer 300L", "status": "ONLINE"}
        ]
        db.devices.insert_many(sample_devices)
        print(f"✅ Đã khởi tạo {len(sample_devices)} thiết bị tủ lạnh mẫu trong collection 'devices'")

    print("\n🎉 Khởi tạo cơ sở dữ liệu MongoDB Atlas hoàn tất thành công!")

if __name__ == "__main__":
    setup_database()
