# Hồ sơ Nộp bài Nhanh & Kịch bản Quay Video Demo (Trước 00:00)

Tài liệu này gom sẵn toàn bộ nội dung chuẩn để bạn **copy – paste thẳng vào form nộp bài**, **xuất Slide PDF**, và **quay Video Demo 2 phút một lần ăn ngay**.

---

## ✅ PHẦN 1: CHECKLIST 3 VIỆC BẠN CẦN LÀM NGAY (Mất ~10 phút)

1. **Điền thông tin đội vào [README.md](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/README.md) (Mục 2)** và push code lên GitHub Repo của bạn.
2. **Xuất Slide PDF để nộp:**
   - Mở `http://127.0.0.1:8000/slides` (hoặc mở trực tiếp [docs/slides.html](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/docs/slides.html) bằng Chrome/Edge).
   - Bấm nút **🖨️ Xuất PDF / In Slide** ở góc trên phải $\rightarrow$ Chọn **Save as PDF** (Layout: Landscape) $\rightarrow$ lưu thành file `Slide_Frutiger_Aqua.pdf` (10 trang đẹp chuẩn).
3. **Quay Video Demo (~2 phút)** bằng phím tắt có sẵn trên Windows (**`Win + Alt + R`** hoặc **`Win + G`** $\to$ Record, hoặc OBS), upload lên YouTube Unlisted / Google Drive để lấy link nộp.

---

## 🎥 PHẦN 2: KỊCH BẢN QUAY VIDEO DEMO 2 PHÚT (1 LẦN ĂN NGAY)

**Chuẩn bị màn hình trước khi bấm Record:**
- Cửa sổ bên trái: VS Code đang chạy **Wokwi Simulator** ([wokwi/diagram.json](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/wokwi/diagram.json) đã nhấn Play).
- Cửa sổ bên phải (3 tab trình duyệt):
  - Tab 1: **Web Điều khiển** `http://127.0.0.1:8000/`
  - Tab 2: **Web Dữ liệu & Biểu đồ** `http://127.0.0.1:8000/data`
  - Tab 3: **Datadog Dashboard** (`https://app.datadoghq.com/dashboard/n72-nmb-pp6/smart-hydroponics-fleet-operations-mongodb--datadog`)

**Diễn biến quay theo từng mốc giây:**
- **0:00 – 0:20 | Giới thiệu & Trạng thái bình thường:**
  - Nói ngắn: *"Chào BGK, đây là dự án Frutiger Aqua Smart Aquarium tích hợp phần cứng mô phỏng Wokwi ESP32, MongoDB Atlas Time Series và Datadog Observability."*
  - Chỉ vào Web Control (`/`): góc trên hiện xanh `Live: MongoDB (OK)`, trên Wokwi đèn xanh `Filter Pump` sáng, OLED báo `STATUS: [OPTIMAL]`, Serial hiện tiếng Việt thông số trực tiếp.
  - Thử bấm nút **🫧 Bật / Tắt Sục Khí Oxy** trên Web $\rightarrow$ chỉ ngay đèn LED xanh lá trên Wokwi tắt/bật theo `<0.2s`!
- **0:20 – 0:50 | Bước 1 — DETECT (Phát hiện sự cố):**
  - Vặn thử núm `pH Sensor` hoặc gạt công tắc `Fault Switch` trên Wokwi (hoặc bấm **🚨 Gây Sự Cố** trên Web).
  - Chỉ vào Wokwi: đèn đỏ `Critical Alarm` bật sáng, `Filter Pump` tắt, OLED báo `STATUS: [CLOG ALERT!]`.
  - Chỉ sang Web (`/data`): thấy sự cố `ACTIVE` vừa ghi vào MongoDB `incidents`.
- **0:50 – 1:25 | Bước 2 — INVESTIGATE (Điều tra trên Datadog & MongoDB):**
  - Mở Tab **Datadog Dashboard** (`n72-nmb-pp6`): chỉ biểu đồ `pump_flow_lpm` tụt `< 1.0`, `ph` vọt `> 8.0`, kèm `ingest.latency_ms` ổn định (chứng tỏ lỗi tại bể chứ không phải DB) và P1 Monitor (`345173530`) chuyển cảnh báo + Log `[AQUA_ALERT]` gắn `dd.trace_id`.
  - Quay lại Tab `/data`: chỉ biểu đồ Chart.js đường Moving Average (`$setWindowFields`) và bảng tổng hợp theo giờ (`$dateTrunc` múi giờ Việt Nam).
- **1:25 – 2:00 | Bước 3 — RESPOND (Phản ứng & Chứng minh MTTR):**
  - Gạt trả công tắc `Fault Switch` trên Wokwi (nếu đang gạt) rồi bấm nút **🛠️ Xả Ngược & Cân Bằng pH** trên Web (`/`).
  - Chỉ mạch Wokwi tắt báo động đỏ ngay lập tức, OLED trở về `[OPTIMAL]`.
  - Mở lại Tab `/data`: bảng **Nhật ký sự cố (`incidents`)** chuyển trạng thái `RESOLVED` và hiện số **MTTR (giây)** chính xác, đồng thời gửi `smartfarm.incidents.mttr_seconds` lên Datadog. Kết thúc!

---

## 📝 PHẦN 3: NỘI DUNG COPY–PASTE ĐIỀN FORM NỘP BÀI

* **Tên dự án:**  
  `Frutiger Aqua • Smart Aquarium Real-time Operations`

* **Mô tả bài toán & giải pháp:**  
  Hệ thống bể cá cảnh và thủy sinh tuần hoàn thường gặp 2 rủi ro chí tử: tắc nghẽn lọc sinh học làm tụt lưu lượng nước (`< 1.0 LPM`) gây ngạt oxy và sốc kiềm `pH > 7.6` tạo khí độc Amoniac (`NH₃`). Dự án kết nối cảm biến ESP32 (mô phỏng Wokwi: nhiệt độ nước `DS18B20`, mực nước siêu âm `HC-SR04`, `pH`, `EC/TDS`, LED, Buzzer, OLED) qua **FastAPI Auto-Bridge (`<0.2s`)**, lưu trữ chuỗi thời gian vào **MongoDB Atlas Time Series** và giám sát – cảnh báo – xử lý sự cố theo chu trình **Detect → Investigate → Respond** trên **Datadog**.

* **Kiến trúc giải pháp & ứng dụng:**  
  4 tầng: (1) Edge ESP32 Wokwi (`wokwi/sketch.ino`, `diagram.json`) & Fleet Simulator (`AQUA-TANK-01/02/03`); (2) FastAPI Backend tích hợp Wokwi Serial Auto-Bridge (RFC2217 `:4000`), Web UI Frutiger Aqua tách riêng trang Điều khiển (`/`) & Dữ liệu (`/data`) + Firebase Auth (Google Sign-In); (3) MongoDB Atlas (`smart_aquarium_iot`); (4) Datadog Observability (`datadoghq.com`) + Webhook auto-remediation.

* **Kiến trúc dữ liệu & data model trên MongoDB:**  
  Dùng database `smart_aquarium_iot` làm kho dữ liệu vận hành chính:
  - Time Series Collection `aquarium_telemetry` theo mô hình 3 phần (`timeField: "ts"`, `metaField: "sensor"`, `granularity: "seconds"`, `expireAfterSeconds: 604800` TTL 7 ngày).
  - Compound Indexes `[('sensor.id', 1), ('ts', -1)]` và `[('sensor.crop', 1), ('ts', -1)]`.
  - 3 Aggregation Pipelines: lấy trạng thái mới nhất (`$match` skip bucket + `$group`/`$first`), tổng hợp theo giờ Việt Nam (`$dateTrunc` timezone `Asia/Ho_Chi_Minh`), và Window Function `$setWindowFields` (`documents: [-4, 0]`) tính Moving Average phát hiện sớm tắc lọc/lệch pH.
  - Collection `incidents` lưu vòng đời sự cố `ACTIVE → RESOLVED`, `mttr_seconds`, và `dd_trace_id`; collection `devices` quản lý 3 bể cá.

* **Kiến trúc observability trên Datadog:**  
  - Dashboard live (`https://app.datadoghq.com/dashboard/n72-nmb-pp6`) theo dõi `smartfarm.pump_flow_lpm`, `smartfarm.ph`, `smartfarm.ec_ppm`, `smartfarm.water_temp`, `smartfarm.water_level_pct`, độ trễ ghi MongoDB `smartfarm.ingest.latency_ms`, `smartfarm.alerts.count` và `smartfarm.incidents.mttr_seconds`.
  - 2 Monitors P1 (`345173530` Pipe Clogging `< 1.0 LPM` và `345174672` Log Spike / `345173822` pH Drift).
  - Bổ sung APM Distributed Tracing (`ddtrace`), Log Management (HTTP Intake v2), và Event Stream: nhúng `dd.trace_id`, `dd.span_id` và bộ tags `rack_id`, `crop`, `zone`, `env`, `service` để điều tra 1-click và kích hoạt Webhook khắc phục `/api/webhooks/datadog`.

* **Mô tả sự cố vận hành được trình diễn:**  
  Trình diễn trực tiếp lỗi **tắc nghẽn lọc sinh học & sốc kiềm pH** trên `AQUA-TANK-01` qua 3 bước: (1) **Detect** — Gạt công tắc `Fault Switch` trên Wokwi hoặc bấm `INJECT_FAULT` trên Web làm lưu lượng tụt còn `0.35 LPM`, pH lên `8.15`, mạch hú còi & bật LED đỏ, Datadog Monitor nổ P1; (2) **Investigate** — Mở log `[AQUA_ALERT]` gắn `dd.trace_id`, kiểm tra `ingest.latency_ms` và biểu đồ `$setWindowFields` tại `/data` xác nhận nguyên nhân tắc lọc; (3) **Respond** — Bấm `RESOLVE` (Xả ngược lọc & cân bằng pH) trên Web $\rightarrow$ Wokwi tắt báo động `<0.2s`, MongoDB chốt sự cố `RESOLVED` + tính `mttr_seconds` đẩy lên Datadog.

* **Khai báo thành phần tái sử dụng, dataset bên ngoài & công cụ AI đã dùng:**  
  - Thư viện mã nguồn mở: FastAPI, Uvicorn, PyMongo, Pydantic, Requests, python-dotenv, ddtrace, pytest, httpx, Tailwind CSS CDN, Chart.js CDN, Firebase Auth/Hosting, thư viện Arduino (`Adafruit GFX`, `Adafruit SSD1306`, `ArduinoJson`, `DallasTemperature`, `OneWire`).
  - Dataset: Không dùng dataset bên ngoài hay dữ liệu nhạy cảm; 100% telemetry được sinh từ mô phỏng phần cứng Wokwi ESP32 và trình giả lập `sensor_simulator.py`.
  - Công cụ AI: Google Antigravity (Gemini) hỗ trợ thiết kế kiến trúc, sinh khung mã nguồn mẫu, tối ưu schema MongoDB/Datadog và biên soạn tài liệu.
