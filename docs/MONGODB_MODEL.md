# MongoDB Data Architecture & Aggregation Pipelines

Tài liệu này chi tiết hóa cách thiết kế và triển khai MongoDB bám sát toàn bộ hướng dẫn trong buổi **Workshop "Time Series in MongoDB"** của MongoDB User Group Vietnam.

---

## 1. Thiết kế Data Model: One Reading, Three Parts (Slide 5)

Mỗi bản ghi telemetry cảm biến tuân thủ cấu trúc chuẩn 3 phần:

```json
{
  "ts": ISODate("2026-11-03T08:00:00Z"),
  "sensor": {
    "id": "FRIDGE-KITCHEN-01",
    "compartment": "fridge",
    "model": "Inverter Pro 550L"
  },
  "temperature": 4.2,
  "humidity": 65.0,
  "door_open": false,
  "power_watts": 62.5
}
```

* **`timeField` (`ts`):** Sử dụng kiểu `ISODate` chuẩn của MongoDB (Date object trong Python/Node.js), tuyệt đối không lưu dạng chuỗi string (Slide 26).
* **`metaField` (`sensor`):** Định danh nguồn phát sinh dữ liệu gồm `id` tủ lạnh, `compartment` (ngăn đông/mát) và `model`. Các trường này hiếm khi thay đổi, giúp MongoDB gom nhóm chính xác các bản ghi của cùng một sensor vào cùng một bucket lưu trữ (Slide 11).
* **`measurements`:** Các thông số đo biến thiên liên tục: `temperature`, `humidity`, `door_open`, `power_watts`.

---

## 2. Cấu hình Time Series Collection (Slide 10)

```javascript
db.createCollection("fridge_telemetry", {
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

Tạo compound index phục vụ chính xác các bộ lọc trong nghiệp vụ giám sát:

```javascript
db.fridge_telemetry.createIndex({ "sensor.id": 1, "ts": -1 });
db.fridge_telemetry.createIndex({ "sensor.compartment": 1, "ts": -1 });
```

Nhờ có index trên `metaField` và `timeField`, MongoDB có thể đọc trực tiếp metadata của bucket (`control.min` và `control.max`) và bỏ qua (skip) toàn bộ các bucket không thỏa mãn điều kiện thời gian mà không cần đọc nội dung bên trong.

---

## 4. Aggregation Pipelines (Slides 16–19)

### 4.1 Pipeline Phân tích Trung bình theo Giờ (Hourly Summary)
Phục vụ báo cáo tiêu thụ điện năng và nhiệt độ trung bình:

```javascript
[
  // Stage 1: $match ĐẦU TIÊN để skip bucket và tận dụng Index (Slide 16)
  {
    $match: {
      "ts": { $gte: ISODate("2026-11-02T00:00:00Z") }
    }
  },
  // Stage 2: $group gom theo giờ với timezone Việt Nam (Slide 18)
  {
    $group: {
      _id: {
        device: "$sensor.id",
        compartment: "$sensor.compartment",
        hour: {
          $dateTrunc: {
            date: "$ts",
            unit: "hour",
            timezone: "Asia/Ho_Chi_Minh"
          }
        }
      },
      avgTemp: { $avg: "$temperature" },
      minTemp: { $min: "$temperature" },
      maxTemp: { $max: "$temperature" },
      avgPower: { $avg: "$power_watts" },
      doorOpenCount: { $sum: { $cond: ["$door_open", 1, 0] } },
      totalReadings: { $count: {} }
    }
  },
  // Stage 3: Sắp xếp theo thứ tự thời gian
  { $sort: { "_id.hour": 1 } },
  // Stage 4: Làm tròn và format kết quả
  {
    $project: {
      _id: 0,
      device: "$_id.device",
      compartment: "$_id.compartment",
      hour: "$_id.hour",
      avgTemperature: { $round: ["$avgTemp", 1] },
      minTemperature: { $round: ["$minTemp", 1] },
      maxTemperature: { $round: ["$maxTemp", 1] },
      avgPowerWatts: { $round: ["$avgPower", 1] },
      doorOpenPercent: {
        $round: [
          { $multiply: [{ $divide: ["$doorOpenCount", "$totalReadings"] }, 100] },
          1
        ]
      }
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
      "sensor.id": "FRIDGE-KITCHEN-01",
      "sensor.compartment": "fridge",
      "ts": { $gte: ISODate("2026-11-03T07:30:00Z") }
    }
  },
  { $sort: { "ts": 1 } },
  {
    $setWindowFields: {
      sortBy: { ts: 1 },
      output: {
        movingAvgTemp: {
          $avg: "$temperature",
          window: { documents: [-4, 0] }
        }
      }
    }
  }
]
```
Kỹ thuật này cho phép hệ thống nhận biết nhiệt độ đang có xu hướng dốc lên liên tục ngay cả khi chưa chạm ngưỡng nguy hiểm, giúp cảnh báo sớm cho người dùng.
