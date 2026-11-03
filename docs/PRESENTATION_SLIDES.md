# Dàn ý Slide Thuyết trình Chung kết (Finals Presentation Pitch)
### Dự án: Smart Hydroponics Real-time Operations (MongoDB × Datadog)
*Thời lượng: 7–10 phút thuyết trình + 5 phút Q&A*

---

## Slide 1: Giới thiệu & Bìa (Cover)
* **Tiêu đề:** Smart Hydroponics Real-time Operations
* **Phụ đề:** Hệ thống Nông nghiệp Đô thị Thông minh: Giám sát Sinh hóa & Phản ứng Sự cố Vận hành Thời gian Thực với MongoDB & Datadog
* **Đội thi:** *(Tên đội của bạn)*
* **Cuộc thi:** MongoDB User Group Vietnam Hackathon 2026 (Real-time Operations)

---

## Slide 2: Vấn đề Thực tế (The Problem)
* **Xu hướng Nông nghiệp Đô thị:** Trồng rau thủy canh ban công, sân thượng, nhà phố đang bùng nổ mạnh mẽ (AgriTech & ESG).
* **Nỗi đau vận hành:**
  * Rễ cây phát triển nhanh làm **tắc nghẽn đường ống dinh dưỡng hồi lưu**.
  * Thiếu tuần hoàn nước dẫn đến **kiềm hóa dung dịch (pH vọt $> 7.5$)**, gây ra hiện tượng *Nutrient Lockout* (khóa dinh dưỡng).
  * Chỉ cần nghẹt ống 3–4 tiếng trong ngày nắng gắt, toàn bộ giàn xà lách tiền triệu sẽ bị cháy rễ và chết héo.
* **Bài toán:** Cần một hệ sinh thái IoT biết **tự phát hiện** tắc nghẽn, **điều tra** nguyên nhân gốc rễ và **tự động xả ngược / châm dung dịch cân bằng** kịp thời.

---

## Slide 3: Kiến trúc Giải pháp (Solution Architecture)
* **Mô hình 3 tầng:**
  1. *AgriTech Edge IoT:* Cảm biến đo pH, EC, lưu lượng bơm LPM, mực nước, nhiệt độ mỗi 2 giây.
  2. *Operational Data Store (MongoDB Atlas M0):* Time Series Collection với Granularity `seconds` và TTL Index 7 ngày.
  3. *Observability & AIOps (Datadog):* Dashboard, Monitors, Tracing (APM) và Log Correlation.
* *(Chèn sơ đồ kiến trúc từ file `docs/ARCHITECTURE.md`)*

---

## Slide 4: Khai thác Sức mạnh MongoDB (MongoDB Deep-Dive)
* **Time Series Collections (Bucketing):**
  * Tối ưu cấu trúc 3 phần: `timeField: ts`, `metaField: sensor (id, zone, crop)` và các đo đạc `measurements (ph, ec, flow)`.
  * Nén dữ liệu vượt trội, lưu trữ hàng triệu bản ghi telemetry mà không tốn dung lượng.
* **Data Lifecycle Management (TTL Index):**
  * Tự động xóa bucket quá hạn sau 7 ngày (`expireAfterSeconds: 604800`) ngầm dưới nền.
* **Aggregation Pipelines:**
  * Phân tích trung bình theo giờ với `$dateTrunc` và timezone `"Asia/Ho_Chi_Minh"`.
  * Ứng dụng **Window Functions (`$setWindowFields`)** tính toán Moving Average để bắt sớm xu hướng sụt giảm lưu lượng bơm.

---

## Slide 5: Khai thác Năng lực Quan sát Datadog (Datadog Deep-Dive)
* **Fleet Operations Dashboard:** Giám sát thời gian thực Lưu lượng nước (LPM), Biến thiên độ pH, Nồng độ EC và p95 Ingest Latency.
* **Monitors / Alerts:** Cảnh báo P1 tự động kích hoạt khi log lỗi `[FARM_ALERT]` xuất hiện hoặc lưu lượng bơm $< 1.0\text{ LPM}$.
* **APM Distributed Tracing & Log Injection:**
  * Liên kết 1-click từ Alert $\to$ Log $\to$ Trace $\to$ Câu lệnh ghi `insert_many` của PyMongo.

---

## Slide 6: Trình diễn Vận hành Thực tế (Live Incident Demo: 3 Bước)
* **Bước 1: Phát hiện (Detect)**
  * Giàn xà lách ban công bị tắc rễ $\to$ Lưu lượng tụt về 0.3 LPM, pH vọt lên 8.2 $\to$ Datadog Monitor lập tức nổ chuông đỏ cảnh báo.
* **Bước 2: Điều tra (Investigate)**
  * Dùng Datadog Logs & Tracing chỉ ra `pump_flow_lpm = 0.3` và `water_level = 15%`.
  * MongoDB Window Function xác nhận lưu lượng nước giảm dốc đứng liên tục trong 5 mẫu gần nhất.
* **Bước 3: Phản ứng (Respond)**
  * Kích hoạt tự động xả ngược áp lực cao (Reverse Pulse Flush) & châm dung dịch pH-Down qua `/api/incident/respond`.
  * Lưu lượng bơm vọt lên lại 4.5 LPM, pH hạ về 6.1 lý tưởng, Datadog Monitor chuyển trạng thái **OK (Xanh)**.

---

## Slide 7: Tác động & Tiềm năng Mở rộng (Impact & Future Work)
* **Tác động thực tế:** Giảm 95% nguy cơ mất trắng giàn rau do nghẹt ống, tiết kiệm 50% thời gian chăm sóc thủ công, thúc đẩy nông nghiệp xanh bền vững (ESG).
* **Hướng phát triển:**
  * Mở rộng từ quy mô hộ gia đình sang các trang trại nhà kính thẳng đứng (Vertical Indoor Farming).
  * Ứng dụng Datadog AI Observability & LLM Agent tự động chẩn đoán bệnh cây trồng qua hình ảnh lá.

---

## Slide 8: Q&A (Hỏi & Đáp)
* Cảm ơn Ban giám khảo MongoDB User Group Vietnam, MongoDB và Datadog!
* Repository GitHub: *(Link repo của bạn)*
