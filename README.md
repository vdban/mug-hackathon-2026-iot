# Smart Hydroponics Real-time Operations 🌱📊
### MongoDB User Group Vietnam Hackathon 2026: Real-time Operations (MongoDB × Datadog)

Dự án xây dựng nền tảng giám sát sinh hóa thời gian thực và tự động phản ứng sự cố vận hành cho hệ thống nông nghiệp thủy canh đô thị (Smart Hydroponics Fleet), kết hợp sức mạnh lưu trữ chuỗi thời gian của **MongoDB Time Series Collections** và năng lực quan sát toàn diện của **Datadog Observability Platform**.

---

## 📋 Mục lục Hồ sơ Bài thi (Tuân thủ Điều 7.2 Thể lệ Cuộc thi)

1. [Tên dự án và Mô tả bài toán](#1-tên-dự-án-và-mô-tả-bài-toán)
2. [Thông tin Đội thi](#2-thông-tin-đội-thi)
3. [Kiến trúc Giải pháp và Ứng dụng](#3-kiến-trúc-giải-pháp-và-ứng-dụng)
4. [Kiến trúc Dữ liệu trên MongoDB](#4-kiến-trúc-dữ-liệu-trên-mongodb)
5. [Kiến trúc Observability trên Datadog](#5-kiến-trúc-observability-trên-datadog)
6. [Yêu cầu Môi trường & Hướng dẫn Cài đặt](#6-yêu-cầu-môi-trường--hướng-dẫn-cài-đặt)
7. [Các bước Chạy thử và Kiểm thử (Testing)](#7-các-bước-chạy-thử-và-kiểm-thử-testing)
8. [Kịch bản Sự cố Trình diễn (Detect $\to$ Investigate $\to$ Respond)](#8-kịch-bản-sự-cố-trình-diễn)
9. [Bản demo MVP & Video Demo](#9-bản-demo-mvp--video-demo)
10. [Khai báo Sử dụng Mã nguồn, Dữ liệu và Công cụ AI](#10-khai-báo-sử-dụng-mã-nguồn-dữ-liệu-và-công-cụ-ai)

---

## 1. Tên dự án và Mô tả bài toán
* **Tên dự án:** Smart Hydroponics Real-time Operations (Hệ thống Giám sát & Vận hành Thủy canh Thông minh)
* **Bài toán thực tế:** Mô hình trồng rau thủy canh hồi lưu (NFT / Vertical Farming) tại ban công, sân thượng đô thị đang phát triển mạnh mẽ. Tuy nhiên, hai sự cố vận hành thường xuyên xảy ra gây mất trắng giàn rau:
  1. *Tắc nghẽn ống hồi lưu:* Rễ cây phát triển nhanh làm nghẹt đường ống, lưu lượng bơm tụt dốc, nước bồn rễ cạn kiệt.
  2. *Kiềm hóa dung dịch (Nutrient Lockout):* Khi nước ngừng tuần hoàn, nồng độ pH kiềm hóa vọt lên $> 7.6$, làm rễ cây bị cháy và không thể hấp thụ dinh dưỡng.
* **Giải pháp:** Hệ thống liên tục thu thập chỉ số cảm biến (pH, EC, lưu lượng bơm LPM, mực nước, nhiệt độ) vào MongoDB Time Series, đồng thời ứng dụng Datadog để phát hiện sớm hiện tượng nghẹt ống từ xa, cho phép điều tra nguyên nhân gốc rễ qua traces/logs và kích hoạt van xả ngược áp lực cao (Reverse Pulse Flush) kết hợp châm pH-Down tự động.

---

## 2. Thông tin Đội thi
* **Tên đội:** *(Điền tên đội của bạn)*
* **Thành viên:** *(Điền tên và email của các thành viên)*
* **Đầu mối liên hệ (Team Lead):** *(Tên, SĐT, Email)*

---

## 3. Kiến trúc Giải pháp và Ứng dụng
Hệ thống gồm 3 tầng chính:
* **AgriTech Edge Simulator:** Mô phỏng 3 giàn thủy canh gửi dữ liệu telemetry chuỗi thời gian mỗi 2 giây.
* **Backend Ingestion & Analytics API (FastAPI):** Tiếp nhận dữ liệu batch, xử lý bất đồng bộ, tích hợp `ddtrace` để thu thập traces & logs, phục vụ Web UI Dashboard tại `localhost:8000`.
* **Data & Observability Platform:** **MongoDB Atlas** (lưu trữ Time Series) và **Datadog** (Dashboard, Monitors, APM, Logs).

👉 *Xem chi tiết sơ đồ luồng tại:* [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 4. Kiến trúc Dữ liệu trên MongoDB
Áp dụng toàn bộ best practices từ **Workshop MongoDB MUG VN 10/2026**:
* **Time Series Collection (`hydroponic_telemetry`):**
  * `timeField`: `ts` (kiểu Date/ISODate).
  * `metaField`: `sensor` (`id`, `zone`, `crop`, `system_type`).
  * `granularity`: `"seconds"`.
  * `expireAfterSeconds`: `604800` (TTL 7 ngày tự động thu dọn dữ liệu cũ).
* **Aggregation Pipelines:**
  * Tính lưu lượng và pH trung bình theo từng giờ sử dụng `$dateTrunc` với timezone `"Asia/Ho_Chi_Minh"`.
  * Phân tích xu hướng và Moving Average bằng toán tử `$setWindowFields`.

👉 *Xem chi tiết tại:* [docs/MONGODB_MODEL.md](docs/MONGODB_MODEL.md)

---

## 5. Kiến trúc Observability trên Datadog
* **Dashboard:** Giám sát thời gian thực Lưu lượng nước (LPM), Biến thiên độ pH, Nồng độ EC và p95 Latency.
* **Monitors / Alerts:** Cảnh báo P1 khi phát hiện log `[FARM_ALERT]` hoặc lưu lượng bơm $< 1.0\text{ LPM}$.
* **APM & Tracing:** Đo lường độ trễ từ HTTP request đến câu lệnh `insert_many` trên MongoDB.
* **Log Management:** Tự động inject `trace_id` vào logs để điều tra 1-click từ alert sang trace.

👉 *Xem chi tiết tại:* [docs/DATADOG_SETUP.md](docs/DATADOG_SETUP.md)

---

## 6. Yêu cầu Môi trường & Hướng dẫn Cài đặt

### Yêu cầu hệ thống:
* Python 3.10 trở lên (đã test mượt mà trên Python 3.12).
* Cụm cơ sở dữ liệu MongoDB Atlas (Free Cluster M0) đã bật quyền truy cập IP.
* Tài khoản Datadog (API Key và Datadog Site).

### Cài đặt:
```bash
# 1. Clone repository
git clone <repo-url>
cd mug-hackathon-2026-iot

# 2. Tạo virtual environment (khuyến nghị)
python -m venv venv
# Trên Windows:
.\venv\Scripts\Activate.ps1
# Trên Linux/Mac:
source venv/bin/activate

# 3. Cài đặt các thư viện cần thiết
pip install -r backend/requirements.txt
```

### Cấu hình biến môi trường:
Tạo file `.env` từ `.env.example`:
```bash
cp .env.example .env
```
Điền các giá trị của bạn vào file `.env`:
```env
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=smart_hydroponics_iot
DD_API_KEY=your_datadog_api_key_here
DD_SITE=datadoghq.com
```

### Khởi tạo Database MongoDB:
Chạy script tự động tạo Time Series Collection và Indexes:
```bash
python scripts/setup_mongo.py
```

---

## 7. Các bước Chạy thử và Kiểm thử (Testing)

### Bước 1: Khởi động Backend API
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Mở trình duyệt truy cập:
* **Giao diện Giám sát Trực quan:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Bước 2: Khởi động Simulator gửi Telemetry
Mở một cửa sổ Terminal mới:
```bash
python simulator/sensor_simulator.py --interval 2.0
```
Terminal sẽ hiển thị log các batch telemetry đang được gửi đều đặn vào MongoDB và đẩy metric lên Datadog.

---

## 8. Kịch bản Sự cố Trình diễn (3 Bước Bắt buộc)

1. **Phát hiện (Detect):** Kích hoạt lỗi nghẹt rễ và kiềm hóa pH:
   ```bash
   python scripts/trigger_incident.py --fault --device HYDROPONIC-RACK-01
   ```
   *(Hoặc bấm nút đỏ trên giao diện Web UI).*  
   $\to$ Datadog Monitor lập tức nổ alert đỏ do lưu lượng tụt về 0.3 LPM và pH vọt 8.2.
2. **Điều tra (Investigate):** Xem liên kết giữa Alert $\to$ Logs $\to$ Traces và kết quả của MongoDB Aggregation Window Function để khoanh vùng nguyên nhân nghẹt rễ tại bồn hồi lưu.
3. **Phản ứng (Respond):** Tự động khắc phục bằng lệnh:
   ```bash
   python scripts/trigger_incident.py --resolve --device HYDROPONIC-RACK-01
   ```
   *(Hoặc bấm nút xanh trên giao diện Web UI).*  
   $\to$ Đường ống được xả ngược áp lực cao, pH-Down châm vào bồn, lưu lượng phục hồi 4.5 LPM và Datadog Monitor chuyển xanh an toàn.

👉 *Xem chi tiết kịch bản thuyết trình tại:* [docs/INCIDENT_SCENARIO.md](docs/INCIDENT_SCENARIO.md)

---

## 9. Bản demo MVP & Video Demo
* **Link Video Demo (YouTube/Drive):** *(Điền link video)*
* **Link Slide Thuyết trình:** *(Điền link Canva/Google Slides)*

---

## 10. Khai báo Sử dụng Mã nguồn, Dữ liệu và Công cụ AI
* **Mã nguồn và thư viện:** FastAPI, PyMongo, Pydantic, ddtrace, Requests (tuân thủ giấy phép MIT/Apache 2.0).
* **Dữ liệu:** Toàn bộ dữ liệu telemetry được tạo từ bộ giả lập toán học ngẫu nhiên (`sensor_simulator.py`), không sử dụng dữ liệu mật của doanh nghiệp.
* **Công cụ AI:** Sử dụng Google Antigravity (Gemini) hỗ trợ thiết kế kiến trúc và sinh khung sườn mã nguồn mẫu.
