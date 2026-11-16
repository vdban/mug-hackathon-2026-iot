# Frutiger Aqua • Smart Aquarium Real-time Operations 🐠📊

Hệ thống giám sát chất lượng nước và điều khiển bể cá thủy sinh thông minh theo thời gian thực (**Wokwi ESP32 + FastAPI + MongoDB Atlas Time Series + Datadog**).

---

## 1. Giới thiệu dự án

Trong vận hành bể cá cảnh và thủy sinh tuần hoàn, hai sự cố nguy hiểm nhất thường xảy ra âm thầm là **tắc nghẽn lọc sinh học** (lưu lượng tụt xuống `< 1.0 LPM` gây thiếu oxy) và **sốc kiềm `pH > 7.6`** (làm chuyển hóa Amoni thành khí độc `NH₃`).

**Frutiger Aqua** giải quyết bài toán này bằng cách kết nối mạch phần cứng mô phỏng **ESP32 trên Wokwi** (`DS18B20`, `HC-SR04`, cảm biến `pH`, `TDS/EC`, màn hình OLED `SSD1306`, còi Buzzer, 3 đèn LED) và trình giả lập đa bể (`AQUA-TANK-01/02/03`) với:
* **FastAPI Backend + Wokwi Auto-Bridge:** Thu thập dữ liệu mỗi 2 giây và đồng bộ lệnh điều khiển 2 chiều từ Web xuống mạch ESP32 trong `< 0.2s`.
* **MongoDB Atlas (`smart_aquarium_iot`):** Lưu chuỗi thời gian cảm biến trong Time Series Collection `aquarium_telemetry` (`expireAfterSeconds: 604800`), tổng hợp theo giờ (`$dateTrunc`), phát hiện xu hướng (`$setWindowFields`) và theo dõi vòng đời sự cố (`incidents`).
* **Datadog (`datadoghq.com`):** Giám sát Metrics, Logs (`[AQUA_ALERT]`), APM Traces (`ddtrace`) và kích hoạt cảnh báo P1 Monitor kèm Webhook tự phục hồi.

### 🌐 Link Demo Trực tuyến (Mở trực tiếp không cần cài đặt)
* **Trang Điều khiển (Web Control):** https://smart-aquarium-mug-2026.web.app/
* **Trang Dữ liệu & Biểu đồ:** https://smart-aquarium-mug-2026.web.app/data
* **Slide trình chiếu (10 trang):** https://smart-aquarium-mug-2026.web.app/slides
* **Datadog Live Dashboard:** https://app.datadoghq.com/dashboard/n72-nmb-pp6/smart-hydroponics-fleet-operations-mongodb--datadog

*(Mẹo: Khi mở bản Web công khai ở trên, nếu muốn kết nối thẳng với FastAPI Backend & MongoDB đang chạy trên máy cá nhân, bấm nút **Kết nối API** trên Web và dán link HTTPS từ script chia sẻ bên dưới).*

---

## 2. Cách hoạt động & Cấu trúc thư mục

### Luồng hoạt động 2 chiều
1. **Thu thập cảm biến (`wokwi/` & `simulator/`):** Cứ mỗi 2 giây, mạch ESP32 gửi các thông số nước (`pH`, `EC/TDS`, nhiệt độ, mực nước, lưu lượng lọc) qua cổng nối tiếp RFC2217 (`:4000`), hoặc script `sensor_simulator.py` gửi batch HTTP cho cả 3 bể về API `POST /api/telemetry/ingest`.
2. **Lưu trữ & Phân tích (`MongoDB Atlas`):** Backend ghi telemetry vào Time Series Collection `aquarium_telemetry`. Nếu lưu lượng `< 1.0 LPM` hoặc `pH > 7.6` (hoặc `pH < 5.0`), hệ thống tự động mở bản ghi sự cố `ACTIVE` trong collection `incidents`. Web `/data` truy vấn dữ liệu trực tiếp qua 3 Aggregation Pipelines (`$group`, `$dateTrunc`, `$setWindowFields`).
3. **Cảnh báo (`Datadog`):** Backend đẩy đồng bộ Metrics, Logs (gắn `dd.trace_id`, `dd.span_id`) và Events lên Datadog Dashboard để theo dõi sức khỏe hệ thống và bật Monitor P1 khi có sự cố.
4. **Điều khiển & Khắc phục (`< 0.2s`):** Khi bấm **Bật/Tắt Sục Oxy**, **Gây Sự Cố**, **Cho Cá Ăn** hoặc **Xả Ngược & Cân Bằng pH** trên Web (`/`), luồng Auto-Bridge đẩy lệnh `CMD:FAULT=...,BUBBLER=...` xuống ngay chân GPIO của ESP32 để đổi trạng thái đèn/còi/OLED, đồng thời chốt sự cố `RESOLVED` và tính thời gian khắc phục (`mttr_seconds`).

### Cấu trúc thư mục
```text
mug-hackathon-2026-iot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI server, REST API & built-in Wokwi Auto-Bridge (:4000)
│   │   ├── database.py          # Kết nối MongoDB Atlas (smart_aquarium_iot)
│   │   ├── models.py            # Pydantic schemas cho telemetry & control
│   │   ├── analytics.py         # 3 Aggregation Pipelines ($group, $dateTrunc, $setWindowFields)
│   │   ├── datadog_service.py   # Gửi Metrics, Logs Intake v2, Events & APM Tracing (ddtrace)
│   │   ├── firebase_service.py  # Đồng bộ Firebase Realtime Database (tùy chọn)
│   │   └── static/              # Web UI Frutiger Aqua (index.html, data.html, slides.html)
│   ├── Dockerfile
│   └── requirements.txt
├── wokwi/                       # Mạch ESP32 Wokwi (sketch.ino, diagram.json, build_firmware.ps1)
├── simulator/                   # Trình giả lập 3 bể cá (sensor_simulator.py)
├── datadog/                     # JSON cấu hình Datadog Dashboard & P1 Monitors
├── scripts/                     # setup_mongo.py, provision_datadog.py, wokwi_bridge.py, trigger_incident.py
├── docs/                        # Tài liệu kiến trúc & chi tiết kỹ thuật
├── tests/                       # Bộ kiểm thử tự động (test_api.py)
├── docker-compose.yml
├── firebase.json
└── Start_Smart_Aquarium.bat     # Khởi chạy nhanh 1-click trên Windows
```

* Tài liệu kỹ thuật chi tiết trong `docs/`:
  * [Kiến trúc hệ thống (ARCHITECTURE.md)](docs/ARCHITECTURE.md)
  * [Mô hình dữ liệu MongoDB (MONGODB_MODEL.md)](docs/MONGODB_MODEL.md)
  * [Cấu hình Datadog (DATADOG_SETUP.md)](docs/DATADOG_SETUP.md)
  * [Kịch bản sự cố (INCIDENT_SCENARIO.md)](docs/INCIDENT_SCENARIO.md)

---

## 3. Hướng dẫn cài đặt & Cách chạy

### Yêu cầu môi trường
* **Python 3.10+** (đã test trên Python 3.12)
* **MongoDB Atlas Cluster** (M0 trở lên)
* **Tài khoản Datadog** (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE=datadoghq.com`)
* *(Tùy chọn)* **Wokwi for VS Code** + **PlatformIO Core** nếu chạy mô phỏng phần cứng ESP32

### Bước 1: Cài đặt thư viện & biến môi trường
```powershell
# Tạo virtual environment & cài dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Tạo file .env từ mẫu và điền thông tin MongoDB / Datadog của bạn
Copy-Item .env.example .env
```

Cấu hình tối thiểu trong `.env`:
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

### Bước 2: Khởi tạo MongoDB & Datadog
```powershell
# Tạo Time Series collection, compound indexes và 3 bể cá mẫu
python scripts/setup_mongo.py

# Tạo Datadog Dashboard & Monitors P1 tự động qua API
python scripts/provision_datadog.py
```

### Bước 3: Khởi chạy hệ thống
* **Cách nhanh (Windows):** Double-click file [`Start_Smart_Aquarium.bat`](Start_Smart_Aquarium.bat) để tự mở Backend (+ Wokwi Auto-Bridge) và trình duyệt.
* **Cách chạy bằng lệnh:**
  ```powershell
  cd backend
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
* **Các trang Web khi chạy trên máy local (`localhost`):**
  * **Trang Điều khiển:** http://127.0.0.1:8000/
  * **Trang Dữ liệu & Biểu đồ:** http://127.0.0.1:8000/data
  * **Slide trình chiếu:** http://127.0.0.1:8000/slides
  * **Swagger API Docs:** http://127.0.0.1:8000/docs
* **Chia sẻ Backend Local & Swagger `/docs` ra Internet để giám khảo/Web Firebase truy cập được:**
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\share_public_backend.ps1
  ```
  Script sẽ mở một HTTPS tunnel công khai tới cổng `8000` (truy cập được `<url-tunnel>/docs` và dán vào thanh `?api=<url-tunnel>` trên `https://smart-aquarium-mug-2026.web.app/`).

### Bước 4: Chạy mạch ESP32 trên Wokwi (hoặc Simulator)
* **Với Wokwi ESP32:** Mở [`wokwi/diagram.json`](wokwi/diagram.json) trong VS Code và bấm **Start Simulation** (Backend sẽ tự kết nối cổng `127.0.0.1:4000`). Nếu sửa code [`wokwi/sketch.ino`](wokwi/sketch.ino), biên dịch lại firmware bằng:
  ```powershell
  powershell -ExecutionPolicy Bypass -File wokwi\build_firmware.ps1
  ```
* **Với trình giả lập phần mềm 3 bể cá:**
  ```powershell
  python simulator/sensor_simulator.py --interval 2.0
  ```

### Bước 5: Chạy kiểm thử tự động
```powershell
python -m pytest -v tests/test_api.py
```
