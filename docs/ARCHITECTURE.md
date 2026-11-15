# Kiến trúc Giải pháp & Ứng dụng: Frutiger Aqua Smart Aquarium

## 1. Tổng quan Kiến trúc Hệ thống

Dự án **Frutiger Aqua Smart Aquarium Real-time Operations** được thiết kế theo mô hình **Real-time IoT Telemetry, Bidirectional Hardware Control & Full-stack Observability**, lấy **MongoDB Atlas Time Series** làm kho dữ liệu vận hành trung tâm và **Datadog** làm bộ não giám sát – điều tra – phản ứng sự cố:

```mermaid
flowchart TD
    subgraph IoT_Edge ["1. Edge Hardware & Simulator Layer"]
        Wokwi["Wokwi ESP32 DevKit V4 (AQUA-TANK-01)\nDS18B20 | HC-SR04 | pH & EC Pots | Fault SW\nOLED SSD1306 | 3x LED | Buzzer\nRFC2217 Serial Port :4000"]
        Sim["Python Fleet Simulator\nAQUA-TANK-01, 02, 03"]
    end

    subgraph App_Layer ["2. Application, Auto-Bridge & Control Layer (FastAPI)"]
        Bridge["Built-in Wokwi Auto-Bridge\nlifespan daemon thread (<0.2s sync)"]
        API["FastAPI Ingestion Endpoint\nPOST /api/telemetry/ingest"]
        AnAPI["MongoDB Analytics Endpoints\n/api/telemetry/latest | /api/analytics/hourly & trend"]
        CtrlAPI["Bidirectional Control & Incident API\n/api/simulator/control | /api/incident/respond\n/api/webhooks/datadog"]
        WebUI["Frutiger Aqua Web UI + Firebase Auth\n/ (Điều khiển) | /data (Biểu đồ) | /slides (Deck)"]
        DDTracer["ddtrace APM & Datadog HTTP Service\nTraces + Logs Intake v2 + Metrics + Events"]
    end

    subgraph Mongo_Layer ["3. Primary Operational Store (MongoDB Atlas: smart_aquarium_iot)"]
        TSColl[("aquarium_telemetry\nTime Series Collection\ngranularity: seconds | TTL: 7 days\nCompound Indexes: sensor.id & sensor.crop")]
        IncColl[("incidents\nSự cố ACTIVE/RESOLVED + MTTR + dd_trace_id")]
        DevColl[("devices\nDanh mục 3 bể cá thông minh")]
    end

    subgraph Datadog_Layer ["4. Datadog Observability Platform (datadoghq.com)"]
        DDDash["Fleet Operations Dashboard (n72-nmb-pp6)\npH, Flow, TDS, Temp, Water Level, Latency, MTTR"]
        DDMon["P1 Monitors\n345173530 (Flow < 1.0 LPM) & 345174672 (Logs)"]
        DDAPM["APM Traces & Log Management\nCorrelated via dd.trace_id, dd.span_id & rack_id"]
    end

    Wokwi <-->|"UART over TCP :4000\nTelemetry <-> CMD:FAULT,BUBBLER"| Bridge
    Bridge -->|"TelemetryBatch"| API
    Sim -->|"HTTP POST /api/telemetry/ingest"| API
    WebUI -->|"Commands & Queries"| CtrlAPI
    WebUI -->|"Read Charts & Hourly Stats"| AnAPI
    CtrlAPI -.->|"Shared State Sync"| Bridge

    API -->|"insert_many(ordered=False)"| TSColl
    AnAPI -->|"Aggregation: $match $dateTrunc $setWindowFields"| TSColl
    CtrlAPI -->|"Open/Resolve & Calculate MTTR"| IncColl
    WebUI -->|"Tank Metadata"| DevColl

    API --> DDTracer
    CtrlAPI --> DDTracer
    DDTracer -.->|"Metrics, Logs v2, Traces, Events"| Datadog_Layer
    DDMon -->|"Webhook auto_remediate=true"| CtrlAPI
```

---

## 2. Chi tiết 4 tầng trong kiến trúc

### 2.1 Tầng Cảm biến & Phần cứng (`wokwi/` & `simulator/`)
* **Wokwi ESP32 Simulator (`AQUA-TANK-01`):** Mô phỏng vi điều khiển thật chạy firmware Arduino ([wokwi/sketch.ino](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/wokwi/sketch.ino)) với 5 cảm biến và 4 cơ cấu chấp hành trên [wokwi/diagram.json](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/wokwi/diagram.json).
* **Python Fleet Simulator ([simulator/sensor_simulator.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/simulator/sensor_simulator.py)) & Web Telemetry Streamer:** Bơm dữ liệu đồng thời cho cả 3 bể (`AQUA-TANK-01` Neon Tetra & Guppy, `AQUA-TANK-02` Clownfish & Coral, `AQUA-TANK-03` Mini Koi & Moss).

### 2.2 Tầng Ứng dụng, Auto-Bridge & Điều khiển (`backend/app/`)
* **Wokwi Auto-Bridge tích hợp sẵn (`_wokwi_auto_bridge_worker`):** Tự động kết nối `127.0.0.1:4000` khi `uvicorn` khởi động; đọc dòng telemetry tiếng Việt từ ESP32 nạp thẳng vào pipeline `ingest_telemetry()` và đẩy lệnh thay đổi từ Web UI xuống ESP32 trong vòng `< 0.2s`.
* **Web UI tách biệt 2 trang + Google Sign-In ([backend/app/static/index.html](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/backend/app/static/index.html), [data.html](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/backend/app/static/data.html)):** Triển khai song song lên **Firebase Hosting** (`https://smart-aquarium-mug-2026.web.app`), hỗ trợ xác thực Google và tự động kết nối API từ xa qua `?api=<url>`.

### 2.3 Tầng Cơ sở Dữ liệu (`MongoDB Atlas — smart_aquarium_iot`)
* Đóng vai trò **Operational Store chính**:
  * Lưu chuỗi thời gian cảm biến trong Time Series Collection `aquarium_telemetry`.
  * Truy vấn tức thời bằng MongoDB Aggregation Pipelines (`$group`, `$dateTrunc`, `$setWindowFields`).
  * Quản lý vòng đời sự cố (`ACTIVE` → `RESOLVED` + tính `mttr_seconds`) trong `incidents`.

### 2.4 Tầng Observability (`Datadog Platform`)
* **Metrics & Ingestion Latency:** Theo dõi 5 chỉ số sinh hóa bể cá (`smartfarm.ph`, `smartfarm.ec_ppm`, `smartfarm.water_temp`, `smartfarm.water_level_pct`, `smartfarm.pump_flow_lpm`), độ trễ ghi MongoDB (`smartfarm.ingest.latency_ms`), số cảnh báo (`smartfarm.alerts.count`) và `smartfarm.incidents.mttr_seconds`.
* **Logs + Traces Correlation:** Mỗi sự cố `[AQUA_ALERT]` hoặc `[INCIDENT_RESOLVED]` gửi lên Datadog Logs Intake v2 kèm `dd.trace_id`, `dd.span_id` và lưu vết vào MongoDB `incidents`.
* **Proactive Alerting & Auto-Remediation:** Monitor P1 phát hiện tắc lọc (`Flow < 1.0 LPM`) có thể bắn Webhook về `/api/webhooks/datadog` để tự động kích hoạt quy trình xả ngược lọc.
