# Datadog Observability Configuration & Setup Guide: Smart Hydroponics

Tài liệu này hướng dẫn cài đặt và thiết lập các năng lực giám sát trên **Datadog** cho hệ thống Nông nghiệp Thủy canh Thông minh:
1. Dashboard thể hiện tín hiệu vận hành sinh hóa của các giàn rau.
2. Monitor/Alert cảnh báo sự cố tắc nghẽn ống và kiềm hóa pH.
3. Năng lực APM (Distributed Tracing) & Log Management liên kết đa chiều.

---

## 1. Khởi động Ứng dụng với Datadog APM (ddtrace)

Thư viện `ddtrace` tự động gắn hooks theo dõi FastAPI và PyMongo:

```powershell
# Cấu hình biến môi trường trên Windows PowerShell
$env:DD_API_KEY="<YOUR_DATADOG_API_KEY>"
$env:DD_SITE="datadoghq.com"  # hoặc us5.datadoghq.com
$env:DD_ENV="hackathon"
$env:DD_SERVICE="smart-hydroponics-service"
$env:DD_LOGS_INJECTION="true"

# Khởi chạy backend với ddtrace-run
cd backend
ddtrace-run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 2. Thiết lập Datadog Dashboard

Truy cập **Dashboards** $\to$ **New Dashboard** (đặt tên: `Smart Hydroponics Fleet Operations`):

### Widget 1: Pump Flow Rate (LPM)
* **Type:** Timeseries
* **Metric:** `smartfarm.pump_flow_lpm`
* **Aggregation:** `avg` by `rack_id`
* **Ý nghĩa:** Giám sát lưu lượng tuần hoàn nước dinh dưỡng qua rễ cây.

### Widget 2: Nutrient pH Level
* **Type:** Timeseries
* **Metric:** `smartfarm.ph`
* **Aggregation:** `avg` by `rack_id`
* **Ngưỡng an toàn:** Đặt marker cảnh báo tại $\text{pH} = 5.8$ và $\text{pH} = 6.5$.

### Widget 3: Ingestion API Latency (p95)
* **Type:** Timeseries
* **Metric:** `trace.fastapi.request.duration{service:smart-hydroponics-service, resource:post_/api/telemetry/ingest}`
* **Aggregation:** `p95` by `resource`

### Widget 4: Farm Incident Log Stream
* **Type:** Log Stream
* **Query:** `service:smart-hydroponics-service status:error`
* **Ý nghĩa:** Hiển thị thời gian thực các cảnh báo `[FARM_ALERT]` khi giàn thủy canh bị nghẹt ống hoặc pH kiềm hóa.

---

## 3. Thiết lập Monitor & Cảnh báo (Alerts)

Vào **Monitors** $\to$ **New Monitor**:

### Monitor: Cảnh báo Tắc nghẽn Ống & Khóa Dinh dưỡng (Critical Farm Alert)
* **Loại Monitor:** Log Monitor (hoặc Metric Monitor trên `smartfarm.pump_flow_lpm < 1.0`)
* **Search Query:** `service:smart-hydroponics-service "FARM_ALERT"`
* **Alert condition:** Kích hoạt cảnh báo khi xuất hiện $> 2$ logs lỗi trong vòng 1 phút.
* **Alert Message:**
  ```text
  🌱 [CRITICAL] Giàn thủy canh phát hiện tắc nghẽn ống tuần hoàn hoặc pH kiềm hóa!
  Nguy cơ cháy rễ cây và chết giàn rau.
  Xem trace và bối cảnh tại: {{log.link}}
  ```
* **Priority:** P1 (Critical)

---

## 4. Cách Điều tra Đa chiều (Trace $\leftrightarrow$ Log $\leftrightarrow$ Metric)

Khi có alert nổ ra:
1. Bấm vào link trong Alert $\to$ Datadog mở trực tiếp Log thông báo sự cố `[FARM_ALERT]`.
2. Bấm nút **View Trace** ở góc dòng log $\to$ Xem toàn bộ vòng đời của request:
   * Metadata rack `HYDROPONIC-RACK-01`.
   * Lưu lượng sụt giảm từ 4.5 LPM xuống 0.3 LPM.
   * Thời gian thực thi lệnh `insert_many` trên MongoDB Time Series.
3. Nhảy sang tab **Service Map** $\to$ Thấy luồng kết nối trực quan Gateway $\to$ FastAPI $\to$ MongoDB Atlas.
