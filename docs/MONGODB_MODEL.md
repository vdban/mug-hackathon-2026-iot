# MongoDB Data Architecture & Aggregation Pipelines: Smart Hydroponics

Tài liệu này chi tiết hóa cách thiết kế và triển khai MongoDB bám sát toàn bộ hướng dẫn trong buổi **Workshop "Time Series in MongoDB"** của MongoDB User Group Vietnam.

---

## 1. Thiết kế Data Model: One Reading, Three Parts (Slide 5)

Mỗi bản ghi telemetry cảm biến thủy canh tuân thủ cấu trúc chuẩn 3 phần:

```json
{
  "ts": ISODate("2026-11-04T08:00:00Z"),
  "sensor": {
    "id": "HYDROPONIC-RACK-01",
    "zone": "Balcony 1F",
    "crop": "Lettuce",
    "system_type": "NFT-Vertical"
  },
  "ph": 6.12,
  "ec_ppm": 960.0,
  "water_temp": 21.4,
  "water_level_pct": 88.0,
  "pump_flow_lpm": 4.52
}
```

* **`timeField` (`ts`):** Kiểu `ISODate` chuẩn của MongoDB (Date object trong Python), tuyệt đối không lưu dạng chuỗi string (Slide 26).
* **`metaField` (`sensor`):** Định danh nguồn phát sinh dữ liệu gồm `id`, `zone`, `crop`, và `system_type`. Giúp MongoDB gom nhóm chính xác các bản ghi của cùng một giàn vào cùng một bucket lưu trữ (Slide 11).
* **`measurements`:** Các thông số đo biến thiên liên tục: `ph`, `ec_ppm`, `water_temp`, `water_level_pct`, `pump_flow_lpm`.

---

## 2. Cấu hình Time Series Collection (Slide 10)

```javascript
db.createCollection("hydroponic_telemetry", {
  timeseries: {
    timeField: "ts",
    metaField: "sensor",
    granularity: "seconds"
  },
  expireAfterSeconds: 604800 // TTL: 7 ngày (604800 giây)
})
```

* **`granularity: "seconds"`:** Thiết bị gửi dữ liệu mỗi 2 giây $\to$ cấu hình granularity là `"seconds"` giúp MongoDB định kích thước bucket bao phủ tối đa 1 giờ dữ liệu, tối ưu hóa tỷ lệ nén và tốc độ quét (Slide 12).
* **`expireAfterSeconds: 604800`:** Tự động thu hồi và xóa sạch các bucket cũ hơn 7 ngày ngầm dưới nền, giúp tiết kiệm dung lượng lưu trữ trên Atlas M0 mà không cần viết cron job dọn dẹp (Slide 23).

---

## 3. Tối ưu hóa Truy vấn & Chỉ mục (Indexes) (Slide 20)

Tạo compound index phục vụ chính xác các bộ lọc trong nghiệp vụ giám sát nông nghiệp:

```javascript
db.hydroponic_telemetry.createIndex({ "sensor.id": 1, "ts": -1 });
db.hydroponic_telemetry.createIndex({ "sensor.crop": 1, "ts": -1 });
```

---

## 4. Aggregation Pipelines (Slides 16–19)

### 4.1 Pipeline Phân tích Trung bình theo Giờ (Hourly Summary)
Phục vụ báo cáo nồng độ dinh dưỡng và lưu lượng nước theo từng giờ:

```javascript
[
  // Stage 1: $match ĐẦU TIÊN để skip bucket và tận dụng Index (Slide 16)
  {
    $match: {
      "ts": { $gte: ISODate("2026-11-03T00:00:00Z") }
    }
  },
  // Stage 2: $group gom theo giờ với timezone Việt Nam (Slide 18)
  {
    $group: {
      _id: {
        rack: "$sensor.id",
        crop: "$sensor.crop",
        zone: "$sensor.zone",
        hour: {
          $dateTrunc: {
            date: "$ts",
            unit: "hour",
            timezone: "Asia/Ho_Chi_Minh"
          }
        }
      },
      avgPh: { $avg: "$ph" },
      minPh: { $min: "$ph" },
      maxPh: { $max: "$ph" },
      avgEc: { $avg: "$ec_ppm" },
      avgFlow: { $avg: "$pump_flow_lpm" },
      avgWaterLevel: { $avg: "$water_level_pct" },
      totalReadings: { $count: {} }
    }
  },
  // Stage 3: Sắp xếp theo thứ tự thời gian
  { $sort: { "_id.hour": 1 } },
  // Stage 4: Làm tròn và format kết quả
  {
    $project: {
      _id: 0,
      rack: "$_id.rack",
      crop: "$_id.crop",
      zone: "$_id.zone",
      hour: "$_id.hour",
      avgPh: { $round: ["$avgPh", 2] },
      minPh: { $round: ["$minPh", 2] },
      maxPh: { $round: ["$maxPh", 2] },
      avgEcPpm: { $round: ["$avgEc", 0] },
      avgFlowLpm: { $round: ["$avgFlow", 2] },
      avgWaterLevelPct: { $round: ["$avgWaterLevel", 1] },
      totalReadings: 1
    }
  }
]
```

### 4.2 Pipeline Phân tích Xu hướng Bằng Window Functions (Slide 19)
Sử dụng toán tử `$setWindowFields` để tính **Moving Average (trung bình trượt)** của 5 mẫu liên tiếp:

```javascript
[
  {
    $match: {
      "sensor.id": "HYDROPONIC-RACK-01",
      "ts": { $gte: ISODate("2026-11-04T07:30:00Z") }
    }
  },
  { $sort: { "ts": 1 } },
  {
    $setWindowFields: {
      sortBy: { ts: 1 },
      output: {
        movingAvgFlow: {
          $avg: "$pump_flow_lpm",
          window: { documents: [-4, 0] }
        },
        movingAvgPh: {
          $avg: "$ph",
          window: { documents: [-4, 0] }
        }
      }
    }
  }
]
```
Kỹ thuật này cho phép hệ thống nhận biết lưu lượng tuần hoàn đang giảm dốc đứng hoặc pH đang kiềm hóa trước khi rễ cây bị nghẹt thở hoàn toàn.
