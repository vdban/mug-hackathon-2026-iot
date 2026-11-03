# BÁO CÁO ĐẶC TẢ CHI TIẾT DỰ ÁN
## SMART HYDROPONICS REAL-TIME OPERATIONS
**Cuộc thi:** MongoDB User Group Vietnam Hackathon 2026 (MongoDB × Datadog)  
**Chủ đề:** Real-time Operations • **Nền tảng:** MongoDB Time Series & Datadog Observability  

---

## 1. Mục đích Dự án & Bối cảnh Thực tế
Trong bối cảnh đô thị hóa nhanh và nhu cầu thực phẩm sạch bùng nổ, mô hình trồng rau thủy canh hồi lưu (NFT / Vertical Farming) tại ban công, sân thượng và căn hộ chung cư đang phát triển mạnh mẽ. Tuy nhiên, hai sự cố vận hành chí mạng thường xuyên xảy ra gây mất trắng giàn rau:
* **Tắc nghẽn rễ cây & cặn đường ống hồi lưu (Pipe Clogging):** Rễ cây phát triển rậm rạp làm nghẹt ống dẫn dinh dưỡng, khiến lưu lượng tuần hoàn tụt dốc, nước trong bồn rễ cạn kiệt.
* **Kiềm hóa dung dịch & Khóa dinh dưỡng (Nutrient Lockout):** Khi nước ngừng tuần hoàn, nồng độ pH nhanh chóng kiềm hóa vọt lên trên 7.6 – 8.2, làm rễ cây không thể hấp thụ sắt và khoáng chất, dẫn đến cháy rễ và chết cây trong vòng 3–4 tiếng dưới nắng gắt.

**Mục tiêu cốt lõi:** Xây dựng hệ thống IoT thông minh giúp:
1. **Tự động phát hiện (Detect):** Bắt lỗi nghẹt ống và kiềm hóa pH tức thì qua Datadog Monitors & Alerts.
2. **Điều tra nguyên nhân (Investigate):** Sử dụng liên kết giữa Metrics, Traces, Logs và MongoDB Window Functions.
3. **Phản ứng khắc phục (Respond):** Tự động kích hoạt van xả ngược áp lực cao (Reverse Pulse Flush) và bơm định lượng pH-Down, đưa hệ sinh thái thủy canh về mức tối ưu.

---

## 2. Các Chức năng Chi tiết của Hệ thống
1. **Thu thập Telemetry Chuỗi Thời gian (High-throughput Batch Ingestion):**
   * Cảm biến tại các giàn thủy canh gửi gói dữ liệu mỗi 2 giây gồm: độ pH, nồng độ EC (ppm), lưu lượng bơm (LPM), mực nước bồn chứa (%), nhiệt độ nước (°C).
   * Backend tiếp nhận và ghi hàng loạt bằng lệnh `insert_many(ordered=False)` vào MongoDB Time Series.
2. **Phát hiện Sự cố Tức thời (Real-time Anomaly Detection):**
   * Hệ thống liên tục kiểm tra ngưỡng an toàn: Nếu lưu lượng bơm $< 1.0\text{ LPM}$ hoặc $\text{pH} > 7.6$, hệ thống tự động gắn cờ sự cố, bắn Log lỗi `[FARM_ALERT]` và gửi Event khẩn cấp sang Datadog.
3. **Bảng điều khiển Vận hành Trực quan (Fleet Operations Dashboard):**
   * **Datadog Dashboard:** Đo lường độ trễ p95, throughput, lưu lượng bơm và phân bố độ pH.
   * **Web UI Dashboard (Tích hợp tại `localhost:8000`):** Hiển thị trực quan 3 giàn thủy canh, biểu đồ thời gian thực đa trục (LPM & pH) và nút bấm giả lập sự cố.
4. **Phân tích Xu hướng Bằng MongoDB Window Functions:**
   * Sử dụng toán tử `$setWindowFields` tính toán Moving Average (trung bình trượt) 5 mẫu gần nhất của lưu lượng nước và độ pH, giúp nhận biết hiện tượng nghẹt ống từ sớm.
5. **Cơ chế Phản ứng & Khắc phục Sự cố (Incident Mitigation API):**
   * Endpoint `/api/incident/respond` cho phép kích hoạt chu trình xả ngược và châm dung dịch cân bằng, lưu nhật ký khắc phục vào MongoDB collection `incidents` và gửi tín hiệu phục hồi lên Datadog.

---

## 3. Kiến trúc Kỹ thuật & Triển khai

| Thành phần | Công nghệ / Nền tảng | Vai trò & Kỹ thuật áp dụng |
| :--- | :--- | :--- |
| **Operational Database** | MongoDB Atlas (Free M0) | Time Series Collection (`granularity: seconds`), TTL Index 7 ngày (`expireAfterSeconds: 604800`), Aggregation Pipeline (`$match`, `$dateTrunc`, `$setWindowFields`). |
| **Observability Platform** | Datadog Cloud | Dashboard thời gian thực, Log Management Injection (`trace_id`), APM Distributed Tracing, Alert Monitors. |
| **Backend Ingestion API** | Python 3.12, FastAPI, ddtrace | Xử lý batch bất đồng bộ, middleware CORS, tích hợp Datadog REST API v1/v2. |
| **AgriTech Edge Simulation** | Python Requests Simulator | Mô phỏng dữ liệu ngẫu nhiên của 3 giàn thủy canh, hỗ trợ cờ `--fault` và `--resolve` phục vụ demo. |

---

## 4. Hướng dẫn Kết nối & Các Bước Thực thi
1. **Cấu hình biến môi trường (`.env`):**
   * Điền `MONGODB_URI` và `DD_API_KEY`.
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
