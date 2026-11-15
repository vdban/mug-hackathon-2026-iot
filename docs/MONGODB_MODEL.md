# Kiến trúc Dữ liệu & Data Model trên MongoDB: Smart Aquarium

Tài liệu này mô tả chi tiết cách mô hình hóa dữ liệu, tối ưu lưu trữ và thiết kế Aggregation Pipelines trên **MongoDB Atlas (`smart_aquarium_iot`)** phục vụ bài toán giám sát và xử lý sự cố bể cá thông minh.

---

## 1. Thiết kế Data Model: "One Reading, Three Parts"

Mỗi bản ghi telemetry gửi từ Wokwi ESP32 hoặc Simulator được lưu vào Time Series Collection `aquarium_telemetry` theo chuẩn 3 phần trong [backend/app/models.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/backend/app/models.py):

```json
{
  "ts": ISODate("2026-11-15T15:30:00Z"),
  "sensor": {
    "id": "AQUA-TANK-01",
    "zone": "Living Room 1F",
    "crop": "Neon Tetra & Guppy",
    "system_type": "Canister Bio-Filter"
  },
  "ph": 6.82,
  "ec_ppm": 400.0,
  "water_temp": 25.0,
  "water_level_pct": 88.5,
  "pump_flow_lpm": 4.50
}
```

* **`timeField` (`ts`):** Kiểu `datetime` (ISODate UTC), phục vụ phân vùng thời gian và quét bucket.
* **`metaField` (`sensor`):** Siêu dữ liệu bất biến theo thiết bị (`id`, `zone`, `crop`, `system_type`) giúp MongoDB gom chính xác toàn bộ chuỗi đọc của cùng một bể cá vào chung một khối bucket nén trên đĩa.
* **`measurements`:** 5 trường số biến thiên liên tục (`ph`, `ec_ppm`, `water_temp`, `water_level_pct`, `pump_flow_lpm`).

---

## 2. Time Series Collection, TTL (`expireAfterSeconds`) & Indexes

Khởi tạo tự động qua [scripts/setup_mongo.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/scripts/setup_mongo.py):

```javascript
db.createCollection("aquarium_telemetry", {
  timeseries: {
    timeField: "ts",
    metaField: "sensor",
    granularity: "seconds"
  },
  expireAfterSeconds: 604800 // TTL tự động xóa bucket quá 7 ngày
});

db.aquarium_telemetry.createIndex({ "sensor.id": 1, "ts": -1 });
db.aquarium_telemetry.createIndex({ "sensor.crop": 1, "ts": -1 });
```

* **`granularity: "seconds"`:** Phù hợp tần suất lấy mẫu mỗi 2 giây từ ESP32 Wokwi, tối ưu dung lượng nén và khả năng skip bucket.
* **`expireAfterSeconds: 604800`:** Quản lý vòng đời dữ liệu tự động trên Atlas Free Tier M0 (giữ cửa sổ 7 ngày gần nhất mà không cần job xóa thủ công).

### Collections Vận hành Bổ trợ
1. **`devices`:** Lưu thông tin định danh & cấu hình 3 bể mẫu (`AQUA-TANK-01`, `AQUA-TANK-02`, `AQUA-TANK-03`).
2. **`incidents`:** Lưu nhật ký sự cố gắn chặt quy trình vận hành:
   * Khi phát hiện lỗi (`pump_flow_lpm < 1.0` hoặc `ph > 7.6` hoặc `ph < 5.0`), mở 1 document `status: "ACTIVE"` với `detected_at`, `trigger_reading`, `dd_trace_id`.
   * Khi xử lý qua `/api/incident/respond` hoặc Datadog Webhook, cập nhật `status: "RESOLVED"`, `resolved_at`, `action`, và tự động tính `mttr_seconds`.

---

## 3. Aggregation Pipelines Phục vụ Vận hành ([backend/app/analytics.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/backend/app/analytics.py))

### 3.1 Lấy Trạng thái Mới nhất từng Bể (`GET /api/telemetry/latest`)
* Bắt đầu bằng `$match` trên `ts` để skip bucket cũ $\rightarrow$ `$sort: { ts: -1 }` $\rightarrow$ `$group` theo `sensor.id` với `$first`.

### 3.2 Tổng hợp Sinh hóa theo Từng giờ với `$dateTrunc` (`GET /api/analytics/hourly`)
* Nhóm dữ liệu theo giờ Việt Nam (`timezone: "Asia/Ho_Chi_Minh"`), tính `avgPh`, `minPh`, `maxPh`, `avgEcPpm`, `avgFlowLpm`, `avgWaterLevelPct` và `totalReadings`, hiển thị trực tiếp tại bảng thống kê trên `/data`.

### 3.3 Phân tích Xu hướng bằng Window Function `$setWindowFields` (`GET /api/analytics/trend`)
```javascript
[
  { $match: { "sensor.id": "AQUA-TANK-01", "ts": { $gte: startTime } } },
  { $sort: { "ts": 1 } },
  {
    $setWindowFields: {
      sortBy: { ts: 1 },
      output: {
        movingAvgFlow: { $avg: "$pump_flow_lpm", window: { documents: [-4, 0] } },
        movingAvgPh: { $avg: "$ph", window: { documents: [-4, 0] } }
      }
    }
  }
]
```
* Tính trung bình trượt 5 mẫu gần nhất (`[-4, 0]`) cho lưu lượng lọc và độ pH, giúp kỹ thuật viên phân biệt **nhiễu cảm biến tức thời** với **xu hướng tắc lọc thật sự** trên biểu đồ Chart.js tại `/data`.
