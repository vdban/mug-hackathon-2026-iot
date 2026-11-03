# Solution & System Architecture

## 1. Tổng quan Kiến trúc Hệ thống

Dự án **Smart Fridge Real-time Operations** được xây dựng theo kiến trúc hướng dữ liệu thời gian thực (Real-time IoT Telemetry & Observability), tích hợp sâu giữa **MongoDB Time Series Collections** và **Datadog Observability Platform**:

```mermaid
flowchart TD
    subgraph IoT_Edge ["IoT Device Layer (Edge/Simulator)"]
        S1["Fridge Sensor: Kitchen 1F\n(Temp, Humidity, Door, Power)"]
        S2["Fridge Sensor: Living Room\n(Temp, Humidity, Door, Power)"]
        S3["Fridge Sensor: Pantry 2F\n(Temp, Humidity, Door, Power)"]
    end

    subgraph Backend_Layer ["Application & Ingestion Service (FastAPI)"]
        API["FastAPI Ingestion Endpoint\n/api/telemetry/ingest"]
        AnAPI["Aggregation Analytics Endpoint\n/api/analytics/hourly & trend"]
        ResAPI["Incident Mitigation Endpoint\n/api/incident/respond"]
        DDTracer["Datadog Tracer (ddtrace)\nAPM & Auto-Instrumentation"]
        API --> DDTracer
    end

    subgraph MongoDB_Layer ["MongoDB Atlas Platform (Primary Operational Store)"]
        TSColl[("fridge_telemetry\n(Time Series Collection)\ngranularity: seconds\nTTL: 7 days")]
        IncColl[("incidents\n(Normal Collection)")]
        DevColl[("devices\n(Normal Collection)")]
    end

    subgraph Datadog_Layer ["Datadog Observability Platform"]
        DDDash["Real-time Operations Dashboard\n(Latency, Temp, Power, Ingest Rate)"]
        DDMon["Smart Alert Monitors\n(Threshold Alert, Anomaly Detection)"]
        DDAPM["APM Distributed Tracing\n(FastAPI -> PyMongo queries)"]
        DDLogs["Log Management\n(Correlated with Trace IDs)"]
    end

    S1 -->|HTTP POST JSON Batch| API
    S2 -->|HTTP POST JSON Batch| API
    S3 -->|HTTP POST JSON Batch| API

    API -->|insertMany ordered:false| TSColl
    AnAPI -->|Aggregation Pipeline $match $group $window| TSColl
    ResAPI -->|Record remediation| IncColl

    DDTracer -.->|Traces, Metrics, Logs| Datadog_Layer
    DDMon -->|Webhook / Slack Alert| ResAPI
```

---

## 2. Các tầng trong kiến trúc

### 2.1 Tầng Cảm biến & Thu thập (IoT Edge Simulation)
* Mô phỏng đội xe/thiết bị tủ lạnh thông minh gửi gói dữ liệu (batch) mỗi 2 giây.
* Payload chứa 3 thành phần theo đúng chuẩn thiết kế của MongoDB:
  * `timeField` (`ts`): Kiểu `Date` (ISODate UTC).
  * `metaField` (`sensor`): Nhãn định danh nguồn cảm biến (`id`, `compartment`, `model`).
  * `measurements`: Các chỉ số đo đạc (`temperature`, `humidity`, `door_open`, `power_watts`).

### 2.2 Tầng Ứng dụng & Dịch vụ (FastAPI + ddtrace)
* **Xử lý bất đồng bộ & Batch Ingestion:** Tối ưu hóa ghi dữ liệu bằng cách sử dụng `insert_many(..., ordered=False)`.
* **Tích hợp Datadog APM:** Tự động tạo spans cho mọi HTTP request, truy vấn database và ghi log có gán kèm `dd.trace_id` và `dd.span_id`.

### 2.3 Tầng Cơ sở dữ liệu (MongoDB Atlas)
* **Time Series Collection (`fridge_telemetry`):**
  * Tự động gom dữ liệu vào các bucket tối ưu nén lên đến 1,000 readings hoặc 125 KB/bucket.
  * Tích hợp **TTL Index (`expireAfterSeconds: 604800`)** tự động dọn dẹp các bucket quá 7 ngày tuổi ngầm dưới nền.
* **Collections nghiệp vụ thường (`devices`, `incidents`):** Lưu trữ metadata thiết bị và nhật ký hành động khắc phục sự cố.

### 2.4 Tầng Quan sát & Vận hành (Datadog Platform)
* **APM & Tracing:** Theo dõi thời gian phản hồi (p95 latency) của endpoint ghi dữ liệu và độ trễ truy vấn PyMongo.
* **Logs Correlation:** Khi có lỗi hoặc cảnh báo vượt ngưỡng, log được liên kết trực tiếp với trace để truy vết root cause trong vòng 1 cú click.
* **Monitors & Anomaly Detection:** Phát hiện khi nhiệt độ vượt ngưỡng an toàn ($>10^\circ\text{C}$ ở ngăn mát) hoặc khi có hiện tượng mở cửa kéo dài.
