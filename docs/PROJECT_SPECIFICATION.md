# BÁO CÁO ĐẶC TẢ CHI TIẾT DỰ ÁN
## SMART FRIDGE REAL-TIME OPERATIONS
**Cuộc thi:** MongoDB User Group Vietnam Hackathon 2026 (MongoDB × Datadog)  
**Chủ đề:** Real-time Operations • **Nền tảng:** MongoDB Time Series & Datadog Observability  

---

## 1. Mục đích Dự án & Bối cảnh Thực tế
Trong đời sống gia đình hàng ngày, tủ lạnh là thiết bị tiêu thụ điện liên tục 24/7 và bảo quản toàn bộ nguồn lương thực tươi sống. Tuy nhiên, hai sự cố vận hành thường xuyên xảy ra nhưng rất khó phát hiện kịp thời:
* **Quên đóng khít cửa tủ lạnh (Door Ajar):** Do trẻ nhỏ lấy đồ hoặc gioăng cao su bị hở. Hơi lạnh thất thoát khiến ngăn mát vọt lên trên 15°C, thực phẩm bị ôi thiu bốc mùi, máy nén gồng hết công suất 180W gây lãng phí điện năng nghiêm trọng.
* **Quá tải nhiệt máy nén (Compressor Overheat):** Bụi bẩn bám dàn nóng hoặc môi trường oi bức khiến động cơ chạy liên tục ở nhiệt độ cao, tiềm ẩn nguy cơ chập cháy điện gia đình.

**Mục tiêu cốt lõi:** Xây dựng hệ thống IoT thông minh giúp:
1. **Tự động phát hiện (Detect):** Bắt lỗi trước khi người dùng kịp mở tủ qua Datadog Monitors & Alerts.
2. **Điều tra nguyên nhân (Investigate):** Sử dụng liên kết giữa Metrics, Traces, Logs và MongoDB Window Functions.
3. **Phản ứng khắc phục (Respond):** Tự động đóng cửa và tăng cường làm lạnh khẩn cấp, đưa các chỉ số về vùng xanh an toàn.

---

## 2. Các Chức năng Chi tiết của Hệ thống
1. **Thu thập Telemetry Chuỗi Thời gian (High-throughput Batch Ingestion):**
   * Cảm biến tại các tủ lạnh định kỳ gửi gói dữ liệu mỗi 2 giây gồm: nhiệt độ ngăn đông/mát, độ ẩm, trạng thái cửa (mở/đóng), công suất máy nén (Watts).
   * Backend tiếp nhận và ghi hàng loạt bằng lệnh `insert_many(ordered=False)` vào MongoDB Time Series.
2. **Phát hiện Sự cố Tức thời (Real-time Anomaly Detection):**
   * Hệ thống liên tục kiểm tra ngưỡng an toàn: Nếu ngăn mát > 10°C hoặc ngăn đông > -5°C, hệ thống tự động gắn cờ sự cố, bắn Log lỗi `[INCIDENT_ALERT]` và gửi Event khẩn cấp sang Datadog.
3. **Bảng điều khiển Vận hành Trực quan (Fleet Operations Dashboard):**
   * **Datadog Dashboard:** Đo lường độ trễ p95, throughput và error rate.
   * **Web UI Dashboard (Tích hợp tại `localhost:8000`):** Hiển thị thẻ trực quan 3 tủ lạnh và biểu đồ nhiệt độ real-time.
4. **Phân tích Xu hướng Bằng MongoDB Window Functions:**
   * Sử dụng toán tử `$setWindowFields` tính toán Moving Average (trung bình trượt) 5 mẫu gần nhất, giúp nhận biết nhiệt độ đang có xu hướng tăng dốc trước khi chạm ngưỡng nguy hiểm.
5. **Cơ chế Phản ứng & Khắc phục Sự cố (Incident Mitigation API):**
   * Endpoint `/api/incident/respond` cho phép kích hoạt chốt đóng cửa tự động và chế độ làm lạnh tăng cường, đồng thời lưu nhật ký khắc phục vào MongoDB collection `incidents` và gửi tín hiệu phục hồi lên Datadog.

---

## 3. Kiến trúc Kỹ thuật & Triển khai

| Thành phần | Công nghệ / Nền tảng | Vai trò & Kỹ thuật áp dụng |
| :--- | :--- | :--- |
| **Operational Database** | MongoDB Atlas (Free M0) | Time Series Collection (`granularity: seconds`), TTL Index 7 ngày (`expireAfterSeconds: 604800`), Aggregation Pipeline (`$match`, `$dateTrunc`, `$setWindowFields`). |
| **Observability Platform** | Datadog Cloud | Dashboard thời gian thực, Log Management Injection (`trace_id`), APM Distributed Tracing, Alert Monitors. |
| **Backend Ingestion API** | Python 3.12, FastAPI, ddtrace | Xử lý batch bất đồng bộ, middleware CORS, tích hợp Datadog REST API v1/v2. |
| **IoT Edge Simulation** | Python Requests Simulator | Mô phỏng dữ liệu ngẫu nhiên của 3 tủ lạnh, hỗ trợ cờ `--fault` và `--resolve` phục vụ demo. |

---

## 4. Hướng dẫn Kết nối & Các Bước Thực thi
1. **Cấu hình biến môi trường (`.env`):**
   * Tạo file `.env` tại thư mục gốc với `MONGODB_URI` (từ cụm Atlas) và `DD_API_KEY` (từ Datadog Organization Settings).
2. **Cài đặt thư viện Python:**
   * Chạy: `pip install -r backend/requirements.txt`
3. **Khởi tạo Cụm MongoDB Time Series:**
   * Chạy lệnh: `python scripts/setup_mongo.py`
4. **Kiểm tra kết nối Datadog:**
   * Chạy lệnh: `python scripts/test_datadog.py`
5. **Khởi động Backend & Simulator:**
   * Backend: `cd backend && uvicorn app.main:app --reload`
   * Simulator: `python simulator/sensor_simulator.py`
6. **Trình diễn Kịch bản Sự cố (Detect $\to$ Investigate $\to$ Respond):**
   * Gây lỗi: `python scripts/trigger_incident.py --fault`
   * Khắc phục: `python scripts/trigger_incident.py --resolve`

---

## 5. Bảng Checklist Hồ sơ Nộp bài (Điều 7.2 Thể lệ)

| Hạng mục Hồ sơ | Vị trí trong Repository | Trạng thái |
| :--- | :--- | :---: |
| Tên dự án & Mô tả bài toán | `README.md` (Mục 1) | ✅ Đã hoàn thành |
| Thông tin đội thi | `README.md` (Mục 2) | ⚠️ Cần điền tên đội & email |
| Kiến trúc giải pháp | `docs/ARCHITECTURE.md` | ✅ Đã hoàn thành (kèm sơ đồ) |
| Kiến trúc dữ liệu MongoDB | `docs/MONGODB_MODEL.md` | ✅ Đã hoàn thành (Time Series & Aggregation) |
| Kiến trúc Observability Datadog | `docs/DATADOG_SETUP.md` | ✅ Đã hoàn thành (Dashboard & Monitors) |
| Mã nguồn & Hướng dẫn cài đặt | `README.md` & thư mục `backend/`, `simulator/` | ✅ Đã hoàn thành |
| MVP chạy được / Demo trực quan | `localhost:8000` (Web UI Dashboard) | ✅ Đã hoàn thành |
| Kịch bản sự cố thực tế | `docs/INCIDENT_SCENARIO.md` | ✅ Đã hoàn thành (Kịch bản 3 phút) |
| Slide thuyết trình chung kết | `docs/PRESENTATION_SLIDES.md` | ✅ Đã hoàn thành (8 slide chi tiết) |
| Video demo (3 phút) | Link YouTube / Google Drive | ⚠️ Bạn quay theo kịch bản có sẵn |
