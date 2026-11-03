# Datadog Observability Configuration & Setup Guide

Tài liệu này hướng dẫn cài đặt và thiết lập các năng lực giám sát trên **Datadog** nhằm đáp ứng toàn bộ yêu cầu kỹ thuật tối thiểu của đề bài Hackathon:
1. Ít nhất 1 Dashboard thể hiện tín hiệu vận hành.
2. Ít nhất 1 Monitor/Alert cảnh báo sự cố có ý nghĩa.
3. Năng lực APM (Distributed Tracing) & Log Management liên kết đa chiều.

---

## 1. Khởi động Ứng dụng với Datadog APM (ddtrace)

Không cần viết code can thiệp sâu, thư viện `ddtrace` tự động gắn hooks theo dõi FastAPI và PyMongo:

```bash
# Cấu hình biến môi trường trên Windows PowerShell
$env:DD_API_KEY="<YOUR_DATADOG_API_KEY>"
$env:DD_SITE="datadoghq.com"  # hoặc us5.datadoghq.com
$env:DD_ENV="hackathon"
$env:DD_SERVICE="smart-fridge-service"
$env:DD_LOGS_INJECTION="true"

# Khởi chạy backend với ddtrace-run
cd backend
ddtrace-run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

* **`DD_LOGS_INJECTION="true"`:** Tự động đính kèm `dd.trace_id` và `dd.span_id` vào mọi dòng log được sinh ra từ Python logger, giúp bạn click từ log nhảy thẳng sang trace tương ứng.

---

## 2. Thiết lập Datadog Dashboard

Truy cập **Dashboards** $\to$ **New Dashboard** (đặt tên: `Smart Fridge IoT Fleet Operations`):

### Widget 1: Ingestion API Latency (p95)
* **Type:** Timeseries
* **Metric:** `trace.fastapi.request.duration{service:smart-fridge-service, resource:post_/api/telemetry/ingest}`
* **Aggregation:** `p95` by `resource`
* **Ý nghĩa:** Giám sát độ trễ tiếp nhận dữ liệu telemetry từ đội tủ lạnh.

### Widget 2: Ingestion Throughput (Requests per Second)
* **Type:** Timeseries
* **Metric:** `trace.fastapi.request.hits{service:smart-fridge-service}`
* **Aggregation:** `sum` as rate
* **Ý nghĩa:** Đảm bảo toàn bộ cảm biến đang gửi dữ liệu đều đặn mỗi 2 giây.

### Widget 3: MongoDB Atlas Execution Time (APM Span)
* **Type:** Timeseries
* **Metric:** `trace.pymongo.query.duration{service:smart-fridge-service}`
* **Aggregation:** `p95` by `mongodb.collection`
* **Ý nghĩa:** Đo lường thời gian ghi vào Time Series collection trên MongoDB.

### Widget 4: Incident Log Stream
* **Type:** Log Stream
* **Query:** `service:smart-fridge-service status:error`
* **Ý nghĩa:** Hiển thị thời gian thực các cảnh báo `[INCIDENT_ALERT]` khi tủ lạnh bị quá nhiệt hoặc mở cửa quên đóng.

---

## 3. Thiết lập Monitor & Cảnh báo (Alerts)

Vào **Monitors** $\to$ **New Monitor**:

### Monitor 1: Cảnh báo Quá nhiệt Tủ lạnh (Log Monitor hoặc APM Error Monitor)
* **Loại Monitor:** Log Monitor
* **Search Query:** `service:smart-fridge-service "INCIDENT_ALERT"`
* **Alert condition:** Kích hoạt cảnh báo khi số lượng log xuất hiện $> 2$ lần trong vòng 1 phút.
* **Alert Message:**
  ```text
  🔥 [CRITICAL] Tủ lạnh phát hiện tình trạng quá nhiệt nguy hiểm!
  Thiết bị có nguy cơ hỏng thực phẩm hoặc cháy máy nén.
  Xem trace và bối cảnh tại: {{log.link}}
  ```
* **Priority:** P1 (Critical)

---

## 4. Cách Điều tra Đa chiều (Trace $\leftrightarrow$ Log $\leftrightarrow$ Metric)

Khi có alert nổ ra:
1. Bấm vào link trong Alert $\to$ Datadog mở trực tiếp Log thông báo sự cố `[INCIDENT_ALERT]`.
2. Bấm nút **View Trace** ở góc dòng log $\to$ Xem toàn bộ vòng đời của request:
   * Thời gian nhận JSON batch.
   * Thời gian thực thi lệnh `insert_many` trên MongoDB Time Series.
3. Nhảy sang tab **Service Map** $\to$ Thấy trực quan luồng dữ liệu từ Client $\to$ FastAPI $\to$ MongoDB Atlas.
