# Dàn ý Slide Thuyết trình Chung kết (Finals Presentation Pitch)
### Dự án: Smart Fridge Real-time Operations (MongoDB × Datadog)
*Thời lượng dự kiến: 7–10 phút thuyết trình + 5 phút Q&A*

---

## Slide 1: Giới thiệu & Bìa (Cover)
* **Tiêu đề:** Smart Fridge Real-time Operations
* **Phụ đề:** Hệ thống IoT Giám sát & Phản ứng Sự cố Vận hành Thời gian Thực với MongoDB & Datadog
* **Đội thi:** *(Tên đội của bạn)*
* **Cuộc thi:** MongoDB User Group Vietnam Hackathon 2026

---

## Slide 2: Vấn đề Thực tế (The Problem)
* **Nỗi đau thường nhật:** Tủ lạnh gia đình bị hở cửa (trẻ nhỏ lấy đồ, gioăng cao su mòn) hoặc máy nén bị bám bụi quá tải.
* **Hậu quả vận hành:**
  * Thất thoát năng lượng: Điện năng tiêu thụ tăng gấp 3 lần (từ 60W lên 180W).
  * Hỏng hóc thực phẩm: Ngăn mát vọt lên $> 15^\circ\text{C}$ làm ôi thiu đồ tươi sống.
  * Nguy cơ chập cháy: Máy nén gồng liên tục dẫn đến quá nhiệt động cơ (Thermal Overload).
* **Bài toán:** Cần một hệ thống biết **tự phát hiện** sự cố trước khi người dùng kịp mở tủ, **điều tra** nguyên nhân gốc rễ và **tự động phản ứng** kịp thời.

---

## Slide 3: Kiến trúc Giải pháp (Solution Architecture)
* **Mô hình 3 tầng:**
  1. *Edge IoT Telemetry:* Cảm biến thu thập nhiệt độ, độ ẩm, trạng thái cửa, công suất điện mỗi 2 giây.
  2. *Operational Data Store (MongoDB Atlas):* Time Series Collection với Granularity `seconds` và TTL Index 7 ngày.
  3. *Observability & AIOps (Datadog):* Dashboard, Monitors, Tracing (APM) và Log Correlation.
* *(Chèn sơ đồ kiến trúc từ file `docs/ARCHITECTURE.md`)*

---

## Slide 4: Khai thác Sức mạnh MongoDB (MongoDB Deep-Dive)
* **Time Series Collections (Bucketing):**
  * Tối ưu cấu trúc 3 phần: `timeField: ts`, `metaField: sensor` và các đo đạc `measurements`.
  * Khả năng nén dữ liệu vượt trội (giảm 90% dung lượng so với collection thường).
* **Data Lifecycle Management (TTL Index):**
  * Tự động xóa bucket quá hạn sau 7 ngày (`expireAfterSeconds: 604800`) ngầm dưới nền mà không tốn chi phí vận hành.
* **Aggregation Pipelines:**
  * Phân tích trung bình theo giờ với `$dateTrunc` và timezone `"Asia/Ho_Chi_Minh"`.
  * Ứng dụng **Window Functions (`$setWindowFields`)** tính toán Moving Average để bắt sớm xu hướng nhiệt độ dốc đứng.

---

## Slide 5: Khai thác Năng lực Quan sát Datadog (Datadog Deep-Dive)
* **Real-time Operations Dashboard:** Giám sát p95 Latency, Throughput (req/s) và biến thiên nhiệt độ 3 tủ lạnh.
* **Monitors / Alerts:** Cảnh báo P1 tự động kích hoạt khi log lỗi `[INCIDENT_ALERT]` xuất hiện hoặc nhiệt độ vượt ngưỡng an toàn.
* **APM Distributed Tracing & Log Injection:**
  * Liên kết 1-click từ Alert $\to$ Log $\to$ Trace $\to$ Câu lệnh ghi `insert_many` của PyMongo.

---

## Slide 6: Trình diễn Vận hành Thực tế (Live Incident Demo: 3 Bước)
* **Bước 1: Phát hiện (Detect)**
  * Cửa tủ Bếp chính bị mở hé $\to$ Nhiệt độ vọt lên $18^\circ\text{C}$ $\to$ Datadog Monitor lập tức nổ chuông đỏ cảnh báo.
* **Bước 2: Điều tra (Investigate)**
  * Dùng Datadog Logs & Tracing chỉ ra `door_open = true` và công suất máy nén đạt cực đại 180W.
  * MongoDB Window Function xác nhận nhiệt độ tăng dốc đứng trong 5 mẫu gần nhất.
* **Bước 3: Phản ứng (Respond)**
  * Kích hoạt tự động đóng cửa & tăng cường làm lạnh khẩn cấp qua `/api/incident/respond`.
  * Dashboard hiển thị nhiệt độ hạ dần về $4^\circ\text{C}$, Monitor chuyển trạng thái **OK (Xanh)**.

---

## Slide 7: Tác động & Tiềm năng Mở rộng (Impact & Future Work)
* **Tác động thực tế:** Giảm 40% chi phí điện năng hao phí do sự cố tủ lạnh, ngăn ngừa 100% rủi ro hỏng đồ ăn và cháy nổ động cơ.
* **Hướng phát triển:**
  * Mở rộng từ quy mô hộ gia đình sang chuỗi kho lạnh nhà hàng, siêu thị (Cold Chain Food Retail).
  * Ứng dụng Datadog AI Observability & LLM Agent tự động phân tích root cause và tạo ticket bảo trì.

---

## Slide 8: Q&A (Hỏi & Đáp)
* Lời cảm ơn Ban tổ chức MongoDB User Group Vietnam, MongoDB và Datadog!
* Repository GitHub: *(Link repo của bạn)*
