# Solution & System Architecture: Smart Hydroponics Farm

## 1. Tổng quan Kiến trúc Hệ thống

Dự án **Smart Hydroponics Real-time Operations** được xây dựng theo kiến trúc hướng dữ liệu thời gian thực (Real-time AgriTech IoT Telemetry & Observability), tích hợp sâu giữa **MongoDB Time Series Collections** và **Datadog Observability Platform**:

```mermaid
flowchart TD
    subgraph IoT_Edge ["IoT AgriTech Edge Layer (Simulator/Gateway)"]
        S1["Hydroponic Tower: Balcony 1F\n(Lettuce NFT: pH, EC, Flow, Level)"]
        S2["Hydroponic Rack: Rooftop 3F\n(Strawberries Drip: pH, EC, Flow, Level)"]
        S3["Hydroponic Shelf: Indoor Kitchen\n(Microgreens Aeroponics: pH, EC, Flow)"]
    end

    subgraph Backend_Layer ["Application & Ingestion Service (FastAPI)"]
        API["FastAPI Ingestion Endpoint\n/api/telemetry/ingest"]
        AnAPI["Aggregation Analytics Endpoint\n/api/analytics/hourly & trend"]
        ResAPI["Incident Mitigation Endpoint\n/api/incident/respond"]
        WebUI["Live Farm Operations Dashboard\nGET /"]
        DDTracer["Datadog Tracer (ddtrace)\nAPM & Auto-Instrumentation"]
        API --> DDTracer
    end

    subgraph MongoDB_Layer ["MongoDB Atlas Platform (Primary Operational Store)"]
        TSColl[("hydroponic_telemetry\n(Time Series Collection)\ngranularity: seconds\nTTL: 7 days")]
        IncColl[("incidents\n(Normal Collection)")]
        DevColl[("devices\n(Normal Collection)")]
    end

    subgraph Datadog_Layer ["Datadog Observability Platform"]
        DDDash["Fleet Operations Dashboard\n(Flow Rate, pH, EC, p95 Latency)"]
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

### 2.1 Tầng Cảm biến Nông nghiệp (AgriTech Edge)
* Mô phỏng đội giàn thủy canh thông minh gửi gói dữ liệu mỗi 2 giây.
* Cấu trúc 3 phần theo chuẩn MongoDB:
  * `timeField` (`ts`): Kiểu `Date` (ISODate UTC).
  * `metaField` (`sensor`): Nhãn định danh nguồn cảm biến (`id`, `zone`, `crop`, `system_type`).
  * `measurements`: Các chỉ số sinh hóa (`ph`, `ec_ppm`, `water_temp`, `water_level_pct`, `pump_flow_lpm`).

### 2.2 Tầng Ứng dụng & Dịch vụ (FastAPI + ddtrace)
* **Xử lý Batch Ingestion:** Tối ưu hóa ghi dữ liệu với `insert_many(..., ordered=False)`.
* **Tích hợp Datadog APM & Logs:** Tự động tạo spans cho mọi HTTP request, truy vấn database và đính kèm `dd.trace_id` vào log lỗi.
* **Giao diện Web UI:** Phục vụ trực tiếp Dashboard điều hành tại `GET /`.

### 2.3 Tầng Cơ sở dữ liệu (MongoDB Atlas)
* **Time Series Collection (`hydroponic_telemetry`):**
  * Tự động gom dữ liệu vào các bucket tối ưu nén lên đến 1,000 readings hoặc 125 KB/bucket.
  * Tích hợp **TTL Index (`expireAfterSeconds: 604800`)** tự động dọn dẹp các bucket quá 7 ngày tuổi.
* **Collections thường (`devices`, `incidents`):** Lưu trữ metadata giàn thủy canh và nhật ký hành động khắc phục sự cố.

### 2.4 Tầng Quan sát & Vận hành (Datadog Platform)
* **APM & Tracing:** Theo dõi thời gian phản hồi (p95 latency) của endpoint và thời gian ghi vào MongoDB.
* **Logs Correlation:** Khi lưu lượng bơm tụt dốc hoặc pH kiềm hóa, log lỗi được liên kết trực tiếp với trace để truy vết root cause trong vòng 1 cú click.
* **Monitors & Anomaly Detection:** Phát hiện khi lưu lượng bơm $< 1.0\text{ LPM}$ (nghẹt rễ) hoặc $\text{pH} > 7.5$ (khóa dinh dưỡng).
