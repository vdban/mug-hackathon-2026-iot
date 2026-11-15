# Kịch bản Trình diễn Sự cố Vận hành: Frutiger Aqua Smart Aquarium
### Chu trình 3 bước: Phát hiện (Detect) → Điều tra (Investigate) → Phản ứng (Respond)

---

## 🎬 Bối cảnh Sự cố Trình diễn
* **Đối tượng:** Bể thủy sinh `AQUA-TANK-01` (*Neon Tetra & Guppy*, khu vực `Living Room 1F`, dùng bộ lọc `Canister Bio-Filter`), mô phỏng trực tiếp bằng bo mạch ESP32 trên Wokwi (`wokwi/diagram.json`).
* **Tình huống lỗi:** Cặn hữu cơ và lá thủy sinh mục làm nghẹt đầu hút/lõi lọc sinh học khiến bơm tuần hoàn mất lưu lượng và nước trong bể bị kiềm hóa đột ngột.
* **Tác động vận hành:**
  * Lưu lượng lọc tụt dốc từ `4.50 LPM` xuống **`0.35 LPM`** (ngưỡng cảnh báo `< 1.0 LPM`).
  * Độ pH tăng vọt lên **`≥ 8.15`** (ngưỡng nguy hiểm `> 7.6` gây ngộ độc NH₃).
  * Mực nước tụt xuống `28%`.

---

## ⏱️ Diễn tiến 3 Bước Demo Trực tiếp

### BƯỚC 1: PHÁT HIỆN (DETECT) — "Nhận cảnh báo tức thì từ Phần cứng & Cloud"
1. **Trạng thái ổn định ban đầu:**
   * Trên Wokwi: Đèn xanh dương `Filter Pump` sáng, đèn xanh lá `Auto Flush / Oxy` sáng, OLED hiển thị `STATUS: [OPTIMAL]`.
   * Trên Web (`http://127.0.0.1:8000/`) & Trang Dữ liệu (`/data`): Hiển thị `Live: MongoDB (OK)` và `HỆ THỐNG ỔN ĐỊNH`.
2. **Kích hoạt sự cố:** Chọn **1 trong 3 cách**:
   * **Cách 1 (Phần cứng Wokwi):** Gạt công tắc `Fault Switch` trên mạch Wokwi sang phải.
   * **Cách 2 (Web UI):** Chọn `TANK-01` và bấm nút **🚨 Gây Sự Cố (Kẹt Lọc & Tăng pH)**.
   * **Cách 3 (CLI):** Chạy `python scripts/trigger_incident.py --fault --device AQUA-TANK-01`.
3. **Phản ứng tức thì (`< 0.2s`):**
   * **Wokwi ESP32:** Đèn đỏ `Critical Alarm` bật sáng, `Filter Pump` tắt, còi `Buzzer` kêu, OLED chuyển sang `STATUS: [CLOG ALERT!]`.
   * **MongoDB Atlas:** Tạo bản ghi `status: "ACTIVE"` trong `smart_aquarium_iot.incidents` lưu `trigger_reading` + `dd_trace_id`.
   * **Datadog:** Ghi log error `[AQUA_ALERT]`, bắn Event Stream, tăng `smartfarm.alerts.count` và kích hoạt Monitor P1 (`345173530` / `345174672`).

---

### BƯỚC 2: ĐIỀU TRA (INVESTIGATE) — "Truy vết nguyên nhân bằng Logs, Traces & MongoDB Window Functions"
1. **Truy vết trên Datadog:**
   * Mở Alert Monitor / Dashboard `n72-nmb-pp6` → xem dòng log `[AQUA_ALERT]` gắn tag `rack_id:AQUA-TANK-01`, `zone:Living Room 1F`, `dd.trace_id`.
   * Kiểm tra đồ thị `smartfarm.pump_flow_lpm` tụt `< 1.0 LPM` cùng lúc `smartfarm.ph` vượt `8.1` và `smartfarm.ingest.latency_ms` vẫn ổn định (loại trừ lỗi database chậm, khẳng định lỗi vật lý tại lọc bể).
2. **Đối chiếu trên Web (`/data`) & MongoDB Aggregation:**
   * Biểu đồ Chart.js tại `/data` (gọi `GET /api/analytics/trend?rack_id=AQUA-TANK-01`) chạy pipeline **`$setWindowFields`** 5 mẫu gần nhất, hiển thị rõ đường `movingAvgFlowLpm` rơi thẳng đứng và cảnh báo trong bảng **Nhật ký Sự cố (`incidents`)**.

---

### BƯỚC 3: PHẢN ỨNG (RESPOND) — "Khắc phục 1-Click & Chứng minh bằng MTTR"
1. **Thực thi khắc phục:**
   * Gạt trả `Fault Switch` (nếu đang bật) rồi bấm nút xanh **🛠️ Xả Ngược & Cân Bằng pH** trên Web Điều khiển (hoặc chạy `python scripts/trigger_incident.py --resolve --device AQUA-TANK-01`, hoặc gọi webhook `POST /api/webhooks/datadog` với `"auto_remediate": true`).
2. **Kết quả xác minh:**
   * **Mạch Wokwi:** Tắt còi & đèn đỏ, đèn `Filter Pump` sáng lại, màn hình OLED trở về `STATUS: [OPTIMAL]`.
   * **MongoDB Atlas:** Incident `AQUA-TANK-01` chuyển từ `ACTIVE` $\to$ `RESOLVED` và tự động tính chính xác **`mttr_seconds`**.
   * **Datadog:** Gửi metric `smartfarm.incidents.mttr_seconds`, log `[INCIDENT_RESOLVED]` và Event xanh xác nhận bể cá hồi phục hoàn toàn.
