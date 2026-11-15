# Frutiger Aqua • Smart Aquarium Real-time Operations 🐠📊
### MongoDB User Group Vietnam Hackathon 2026: Real-time Operations (MongoDB × Datadog)

Dự án xây dựng nền tảng giám sát sinh hóa thời gian thực, điều khiển 2 chiều tới phần cứng mô phỏng ESP32 (Wokwi) và tự động phát hiện – điều tra – phản ứng sự cố vận hành cho hệ thống bể cá cảnh/thủy sinh tuần hoàn (**Smart Aquarium Fleet**), kết hợp **MongoDB Atlas Time Series Collections** làm nền tảng dữ liệu vận hành chính và **Datadog Observability Platform** để giám sát toàn diện Metrics, Logs, APM Traces và Alert Monitors.

---

## 📋 Mục lục Hồ sơ Bài nộp

1. [Tên dự án và Mô tả bài toán](#1-tên-dự-án-và-mô-tả-bài-toán)
2. [Thông tin Đội thi và Đầu mối Liên hệ](#2-thông-tin-đội-thi-và-đầu-mối-liên-hệ)
3. [Kiến trúc Giải pháp và Ứng dụng](#3-kiến-trúc-giải-pháp-và-ứng-dụng)
4. [Kiến trúc Dữ liệu & Data Model trên MongoDB](#4-kiến-trúc-dữ-liệu--data-model-trên-mongodb)
5. [Kiến trúc Observability trên Datadog](#5-kiến-trúc-observability-trên-datadog)
6. [Yêu cầu Môi trường, Cấu hình & Hướng dẫn Cài đặt](#6-yêu-cầu-môi-trường-cấu-hình--hướng-dẫn-cài-đặt)
7. [Các bước Chạy thử MVP & Kiểm thử (Testing)](#7-các-bước-chạy-thử-mvp--kiểm-thử-testing)
8. [Mô tả Sự cố Vận hành Trình diễn (Detect → Investigate → Respond)](#8-mô-tả-sự-cố-vận-hành-trình-diễn-detect--investigate--respond)
9. [Bản demo MVP, Video Demo & Slide Thuyết trình](#9-bản-demo-mvp-video-demo--slide-thuyết-trình)
10. [Khai báo Thành phần Tái sử dụng, Dataset & Công cụ AI](#10-khai-báo-thành-phần-tái-sử-dụng-dataset--công-cụ-ai)

---

## 1. Tên dự án và Mô tả bài toán
* **Tên dự án:** **Frutiger Aqua Smart Aquarium Real-time Operations** (Hệ thống Giám sát & Vận hành Bể Cá Thủy Sinh Thông Minh)
* **Bài toán vận hành thực tế:** Trong các hệ thống bể cá cảnh, hồ san hô mini và hồ Koi đô thị sử dụng lọc sinh học tuần hoàn (`Canister Bio-Filter`, `Sump Protein Skimmer`, `Overflow UV Filter`), người vận hành thường xuyên đối mặt với 2 sự cố nghiêm trọng xảy ra âm thầm và gây chết cá chỉ trong vài giờ:
  1. **Tắc nghẽn lọc tuần hoàn (`Pump Clogging`):** Cặn bẩn, rêu hoặc giá thể vi sinh bít kín đường ống hút/xả khiến lưu lượng bơm sụt giảm mạnh xuống `< 1.0 LPM` và mực nước tụt nhanh, gây thiếu hụt oxy hòa tan tức thì.
  2. **Sốc kiềm hóa pH (`Alkaline pH Drift`):** Nước ngừng tuần hoàn hoặc phân hủy hữu cơ tích tụ làm `pH` tăng vọt lên `> 7.6` (hoặc lệch `< 5.0`), chuyển hóa Amoni (`NH₄⁺`) thành khí độc Amoniac (`NH₃`) gây ngộ độc cá và san hô.
* **Giải pháp:** Kết nối cảm biến phần cứng **ESP32 trên Wokwi** (`DS18B20`, `HC-SR04`, `pH`, `TDS/EC`, công tắc sự cố, LED & Buzzer, OLED `SSD1306`) và trình giả lập đội bể 3 khu vực (`AQUA-TANK-01`, `AQUA-TANK-02`, `AQUA-TANK-03`) với **FastAPI Backend** thông qua **Wokwi Serial Auto-Bridge** (`RFC2217` cổng `4000`, đồng bộ `< 0.2s`), lưu trữ toàn bộ telemetry vào **MongoDB Atlas Time Series** và đẩy Metrics + Logs + Traces + Events lên **Datadog** theo chu trình khép kín **Detect → Investigate → Respond**.

---

## 2. Thông tin Đội thi và Đầu mối Liên hệ
> *Ghi chú: Hướng dẫn điền nhanh trước khi nộp được tổng hợp sẵn trong [docs/NOP_BAI_NHANH.md](docs/NOP_BAI_NHANH.md).*
* **Tên đội:** *(Điền tên đội của bạn / Cá nhân)*
* **Thành viên:** *(Điền Họ tên – Vai trò – Email từng thành viên)*
* **Đầu mối liên hệ (Team Lead):** *(Họ tên – Số điện thoại – Email liên hệ)*

---

## 3. Kiến trúc Giải pháp và Ứng dụng
Hệ thống gồm 4 tầng phối hợp theo thời gian thực:
1. **Tầng Thiết bị & Phần cứng Mô phỏng (`wokwi/`, `simulator/`):**
   * Mạch **ESP32 DevKit V4** trên Wokwi (`wokwi/sketch.ino`, `wokwi/diagram.json`) mô phỏng bể chính `AQUA-TANK-01` với màn hình OLED SSD1306, cảm biến nhiệt độ DS18B20, siêu âm mực nước HC-SR04, 2 biến trở pH/EC, công tắc gạt sự cố (`Fault Switch`), 3 đèn LED (`Filter Pump`, `Auto Flush / Oxy`, `Critical Alarm`) và còi Buzzer.
   * Ngoài ra, `simulator/sensor_simulator.py` mô phỏng đồng thời cả 3 bể (`AQUA-TANK-01`, `AQUA-TANK-02`, `AQUA-TANK-03`).
2. **Tầng Ứng dụng, API & Auto-Bridge (`backend/app/main.py`):**
   * **FastAPI + Uvicorn** tích hợp sẵn luồng nền **Wokwi Auto-Bridge** (`lifespan` thread kết nối TCP RFC2217 `127.0.0.1:4000` ↔ Backend trong `< 0.2s`).
   * **Web App tách 2 trang riêng biệt (Frutiger Aqua + Firebase Google Sign-In):**
     * `/` (`index.html`): **Trung tâm Điều khiển Thuần túy** (bể cá tương tác, chọn bể `01/02/03`, 4 nút điều khiển `INJECT_FAULT`, `RESOLVE`, `TOGGLE_BUBBLER`, `FEED_FISH`, nhật ký thao tác kèm tài khoản Google).
     * `/data` & `/data.html`: **Trang Dữ liệu & Biểu đồ** (thẻ telemetry 3 bể, biểu đồ Chart.js vẽ từ MongoDB `$setWindowFields`, bảng tổng hợp theo giờ `$dateTrunc`, nhật ký sự cố `incidents` & MTTR).
     * `/slides`: **Slide Thuyết trình Chung kết (10 slides)** hỗ trợ trình chiếu trực tiếp và xuất PDF 1-click.
3. **Tầng Dữ liệu Vận hành Chính (`MongoDB Atlas — smart_aquarium_iot`):**
   * Time Series Collection `aquarium_telemetry` (`granularity="seconds"`, TTL 7 ngày) + Collections `incidents` & `devices`.
4. **Tầng Quan sát & Cảnh báo (`Datadog Platform`):**
   * Dashboard live (`n72-nmb-pp6`), 2 Monitors P1 (`345173530` & `345174672`), Log Management, APM Tracing (`ddtrace`), Event Stream và Webhook tự động phục hồi sự cố (`/api/webhooks/datadog`).

👉 *Xem chi tiết sơ đồ kiến trúc tại:* [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 4. Kiến trúc Dữ liệu & Data Model trên MongoDB
Áp dụng chuẩn thiết kế **Time Series in MongoDB** trong database `smart_aquarium_iot`:
* **Time Series Collection (`aquarium_telemetry`):**
  * `timeField`: `"ts"` (ISODate UTC).
  * `metaField`: `"sensor"` (`id`, `zone`, `crop`, `system_type`).
  * `granularity`: `"seconds"` (tối ưu nén bucket cho tần suất gửi mỗi 2 giây).
  * `expireAfterSeconds`: `604800` (TTL Index tự động dọn dữ liệu quá 7 ngày).
* **Compound Indexes hiệu quả:**
  * `[("sensor.id", 1), ("ts", -1)]`
  * `[("sensor.crop", 1), ("ts", -1)]`
* **Collections vận hành bổ trợ:** `incidents` (lưu `detected_at`, `resolved_at`, `mttr_seconds`, `dd_trace_id`, `trigger_reading`, `status`) và `devices` (quản lý 3 bể cá).
* **3 Aggregation Pipelines (`backend/app/analytics.py`):**
  1. `get_latest_telemetry_pipeline`: `$match` theo `ts` → `$sort` → `$group` + `$first` lấy trạng thái mới nhất của từng bể.
  2. `get_hourly_summary_pipeline`: `$match` → `$dateTrunc` (`unit: "hour"`, `timezone: "Asia/Ho_Chi_Minh"`) thống kê `avgPh`, `minPh`, `maxPh`, `avgEcPpm`, `avgFlowLpm`, `avgWaterLevelPct`.
  3. `get_trend_and_anomalies_pipeline`: Window Function `$setWindowFields` (`documents: [-4, 0]`) tính Moving Average 5 mẫu (`movingAvgFlowLpm`, `movingAvgPh`) để phát hiện sớm tắc lọc và sốc kiềm.

👉 *Xem chi tiết schema và pipeline tại:* [docs/MONGODB_MODEL.md](docs/MONGODB_MODEL.md)

---

## 5. Kiến trúc Observability trên Datadog
* **Dashboard vận hành (`n72-nmb-pp6`):** Hiển thị real-time `smartfarm.pump_flow_lpm`, `smartfarm.ph`, `smartfarm.ec_ppm`, `smartfarm.water_temp`, `smartfarm.water_level_pct`, độ trễ ghi MongoDB `smartfarm.ingest.latency_ms`, `smartfarm.alerts.count`, `smartfarm.incidents.mttr_seconds` và live Log Stream.
* **Monitors / Alerts P1:**
  * ID `345173530` ([datadog/monitor_pipe_clog.json](datadog/monitor_pipe_clog.json)): `avg(last_1m):avg:smartfarm.pump_flow_lpm{*} by {rack_id} < 1` (critical `< 1.0`, warning `< 2.0`).
  * ID `345174672` ([datadog/monitor_farm_alert_log.json](datadog/monitor_farm_alert_log.json)): Theo dõi đột biến log sự cố (kèm monitor pH drift dự phòng ID `345173822` khi account không bật log monitor).
* **Năng lực bổ sung & Liên kết đa chiều (`backend/app/datadog_service.py`):**
  * **APM Distributed Tracing (`ddtrace`):** Tự động lấy `trace_id` & `span_id` qua `get_current_trace_context()`.
  * **Log Management (Logs Intake v2) & Event Stream (`/api/v1/events`):** Nhúng đồng bộ `dd.trace_id`, `dd.span_id` và bộ tags vận hành (`rack_id`, `crop`, `zone`, `env:hackathon`, `service:smart-aquarium-service`) để liên kết 1-click giữa Alert ↔ Log ↔ Trace ↔ Bản ghi `incidents` trong MongoDB.

👉 *Xem chi tiết cấu hình tại:* [docs/DATADOG_SETUP.md](docs/DATADOG_SETUP.md)

---

## 6. Yêu cầu Môi trường, Cấu hình & Hướng dẫn Cài đặt

### Yêu cầu môi trường
* **Python 3.10+** (đã xác minh chạy ổn định trên Python 3.12).
* **MongoDB Atlas Cluster** (M0 Free Tier trở lên, đã thêm IP truy cập trong Network Access).
* **Tài khoản Datadog** (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE=datadoghq.com`).
* *(Tùy chọn)* **Wokwi for VS Code** + PlatformIO Core (để chạy mô phỏng mạch ESP32 nội bộ) hoặc Docker Desktop (nếu dùng Datadog Agent local).

### Cài đặt & Cấu hình
```powershell
# 1. Clone repository & vào thư mục dự án
git clone <repo-url>
cd mug-hackathon-2026-iot

# 2. Tạo virtual environment & cài dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# 3. Tạo file .env từ mẫu
Copy-Item .env.example .env
```

Điền cấu hình vào `.env`:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=smart_aquarium_iot

DD_API_KEY=<your_datadog_api_key>
DD_APP_KEY=<your_datadog_app_key>
DD_SITE=datadoghq.com
DD_ENV=hackathon
DD_SERVICE=smart-aquarium-service

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```

### Khởi tạo MongoDB Atlas & Datadog
```powershell
# Tạo Time Series collection aquarium_telemetry, indexes, collection incidents & 3 bể mẫu
python scripts/setup_mongo.py

# Tạo Datadog Dashboard & Monitors P1 tự động qua API
python scripts/provision_datadog.py
```

---

## 7. Các bước Chạy thử MVP & Kiểm thử (Testing)

### Cách A: Khởi chạy nhanh 1-Click (Khuyên dùng)
* Double-click file [Start_Smart_Aquarium.bat](Start_Smart_Aquarium.bat) (hoặc mở workspace bằng VS Code có [.vscode/tasks.json](.vscode/tasks.json) tự bật).
* Hoặc chạy tay Backend (+ sẵn **Wokwi Auto-Bridge** chạy ngầm):
  ```powershell
  cd backend
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
* Truy cập Web UI:
  * **Trang Điều khiển:** http://127.0.0.1:8000/
  * **Trang Dữ liệu & Biểu đồ:** http://127.0.0.1:8000/data
  * **Slide Thuyết trình:** http://127.0.0.1:8000/slides
  * **Swagger API Docs:** http://127.0.0.1:8000/docs

### Cách B: Kết nối Mạch Phần cứng ESP32 trên Wokwi
1. Nếu có sửa [wokwi/sketch.ino](wokwi/sketch.ino), biên dịch lại firmware bằng:
   ```powershell
   powershell -ExecutionPolicy Bypass -File wokwi\build_firmware.ps1
   ```
2. Mở [wokwi/diagram.json](wokwi/diagram.json) trong Wokwi Simulator và bấm **Start Simulation (▶️)**.
3. Backend đang chạy sẽ tự kết nối vào cổng `127.0.0.1:4000` (`rfc2217ServerPort = 4000`), đọc telemetry từ ESP32 đẩy vào MongoDB Atlas + Datadog và gửi ngược lệnh Web UI xuống LED/Còi/OLED trong `< 0.2s`.
*(Nếu muốn giả lập cả 3 bể cùng lúc không qua Wokwi, chạy `python simulator/sensor_simulator.py --interval 2.0`, hoặc bật nút "Web Telemetry Streamer" ngay trên trang Điều khiển).*

### Kiểm thử Tự động (Pytest)
```powershell
python -m pytest -v tests/test_api.py
```
Kiểm tra toàn bộ **8 test cases**: `/health`, `/`, `/data`, `/data.html`, batch ingestion, phát hiện lỗi + mở incident `ACTIVE`, luồng `INJECT_FAULT` → `/api/incident/respond` tính MTTR, Datadog Webhook tự phục hồi, 3 endpoints Aggregation Analytics, và điều khiển `TOGGLE_BUBBLER` / `FEED_FISH`.

---

## 8. Mô tả Sự cố Vận hành Trình diễn (Detect → Investigate → Respond)
1. **Phát hiện (Detect):**
   * Gạt công tắc **`Fault Switch`** trên mạch Wokwi (hoặc bấm nút **🚨 Gây Sự Cố** trên Web Control Center, hoặc chạy `python scripts/trigger_incident.py --fault --device AQUA-TANK-01`).
   * Lưu lượng bơm `AQUA-TANK-01` tụt từ `4.5 LPM` xuống `0.35 LPM`, `pH` tăng vọt lên `> 8.15`. Trên mạch Wokwi: đèn đỏ `Critical Alarm` bật sáng, còi hú, OLED hiện `STATUS: [CLOG ALERT!]`. Backend ghi nhận 1 incident `ACTIVE` vào `smart_aquarium_iot.incidents`, log `[AQUA_ALERT]` kèm `dd.trace_id`, Event Stream và **Datadog Monitor `345173530` nổ cảnh báo P1**.
2. **Điều tra (Investigate):**
   * Từ **Datadog Monitor Alert** → mở **Log Stream** (`[AQUA_ALERT]`) → bấm **View Trace** kiểm tra span `POST /api/telemetry/ingest` & thời gian ghi MongoDB (`smartfarm.ingest.latency_ms`).
   * Mở trang `/data` (hoặc gọi `GET /api/analytics/trend?rack_id=AQUA-TANK-01`) để xem kết quả **`$setWindowFields`** cho thấy đường trung bình trượt `movingAvgFlowLpm` rơi dưới ngưỡng `1.0 LPM` và `movingAvgPh` vượt ngưỡng `7.6`.
3. **Phản ứng (Respond):**
   * Bấm nút **🛠️ Xả Ngược & Cân Bằng pH** trên Web UI (hoặc chạy `python scripts/trigger_incident.py --resolve --device AQUA-TANK-01`, hoặc nhận Datadog Webhook `POST /api/webhooks/datadog` với `"auto_remediate": true`).
   * Lệnh xả ngược truyền xuống Wokwi ESP32 tắt còi & đèn đỏ, khôi phục lọc về `4.5 LPM` và `pH` về vùng an toàn; Backend đóng incident `ACTIVE` → `RESOLVED`, tính chính xác **MTTR (`mttr_seconds`)** và đẩy metric `smartfarm.incidents.mttr_seconds` lên Datadog.

👉 *Xem kịch bản quay demo từng giây tại:* [docs/INCIDENT_SCENARIO.md](docs/INCIDENT_SCENARIO.md) và [docs/NOP_BAI_NHANH.md](docs/NOP_BAI_NHANH.md)

---

## 9. Bản demo MVP, Video Demo & Slide Thuyết trình
* **Web Control Center (Firebase Hosting Live):** https://smart-aquarium-mug-2026.web.app *(Hỗ trợ Đăng nhập Google + Cloud Demo fallback + nối về Backend Local qua `?api=...`)*
* **Datadog Live Dashboard:** https://app.datadoghq.com/dashboard/n72-nmb-pp6/smart-hydroponics-fleet-operations-mongodb--datadog
* **Slide Thuyết trình Chung kết (Web & In PDF 1-Click):** [docs/slides.html](docs/slides.html) *(hoặc truy cập `http://127.0.0.1:8000/slides` khi chạy Backend)*
* **Thiết kế UI & Kiến trúc trên Figma:**
  * [Figma Design (Frutiger Aqua UI)](https://www.figma.com/design/Q14P0NQsoVYwJySP4veLSu?node-id=1-3&autoplay-code-preview=1-3&code-import-attempt-id=c93b32198cd17fbbd10ed20cd13edca6fa9735b2b8ba62a08722bc39dee4f1d2&code-import-node-id=1-3&code-import-surface=code_layer)
  * [FigJam Architecture Diagram](https://www.figma.com/board/b5IvzYRRUWcEJ2llejPcA5?utm_source=other&utm_content=edit_in_figjam&oai_id=&request_id=f9af71b8-5919-4cfa-bf93-793fda415161&architecture=true)
  * Vector SVG gốc: [docs/frutiger_aqua_mockup.svg](docs/frutiger_aqua_mockup.svg)
* **Link Video Demo (YouTube / Google Drive):** *(Điền link sau khi quay xong theo kịch bản 2 phút trong `docs/NOP_BAI_NHANH.md`)*

---

## 10. Khai báo Thành phần Tái sử dụng, Dataset & Công cụ AI
* **Thành phần & thư viện mã nguồn mở tái sử dụng:**
  * Backend & DB: FastAPI, Uvicorn, Pydantic, PyMongo, Requests, python-dotenv, ddtrace, pytest, httpx.
  * Frontend & Auth: Tailwind CSS (CDN), Chart.js (CDN), Firebase Authentication (Google Sign-In SDK) & Firebase Hosting.
  * Phần cứng mô phỏng ESP32 (Wokwi & PlatformIO Arduino Framework): `Adafruit GFX Library`, `Adafruit SSD1306`, `ArduinoJson`, `DallasTemperature`, `OneWire`, `WiFi`, `HTTPClient`.
* **Dataset:** Không sử dụng dữ liệu bên ngoài hay dữ liệu cá nhân/doanh nghiệp. Toàn bộ chuỗi dữ liệu telemetry được tạo hoàn toàn từ cảm biến phần cứng mô phỏng **Wokwi ESP32** ([wokwi/sketch.ino](wokwi/sketch.ino)) và trình sinh dữ liệu toán học **Simulator** ([simulator/sensor_simulator.py](simulator/sensor_simulator.py)).
* **Công cụ AI đã sử dụng:** **Google Antigravity (Gemini)** hỗ trợ thiết kế kiến trúc hệ thống, chuẩn hóa schema MongoDB Time Series, viết code mẫu FastAPI/Arduino/UI Frutiger Aqua, tạo script tự động hóa Wokwi Auto-Bridge, rà soát kiểm thử và biên soạn tài liệu thuyết trình.
