# Kịch bản Trình diễn Vận hành Thực tế (Incident Runbook)
### Chu trình 3 bước: Phát hiện (Detect) $\to$ Điều tra (Investigate) $\to$ Phản ứng (Respond)

Tài liệu này dùng làm kịch bản thuyết trình và quay video demo cho ban giám khảo cuộc thi MongoDB User Group Vietnam Hackathon 2026.

---

## 🎬 Bối cảnh Sự cố (Incident Scenario)
* **Tình huống:** Tủ lạnh chính tại gian bếp (`FRIDGE-KITCHEN-01`) bị mở hé cửa do sơ suất. Khí lạnh thất thoát nhanh chóng, máy nén khí phải chạy hết công suất (180W) nhưng nhiệt độ ngăn mát vẫn tăng liên tục từ $4^\circ\text{C} \to 18^\circ\text{C}$, đe dọa làm hỏng toàn bộ đồ tươi sống bên trong.

---

## ⏱️ Kịch bản 3 phút Demo trực tiếp

### BƯỚC 1: PHÁT HIỆN (DETECT) - "Biết có chuyện trước người dùng"
1. **Trạng thái ban đầu:**
   * Hệ thống đang chạy bình thường, 3 tủ lạnh gửi dữ liệu đều đặn mỗi 2 giây.
   * Dashboard Datadog hiển thị màu xanh an toàn: Nhiệt độ trung bình ngăn mát duy trì ở mức $4^\circ\text{C}$, p95 latency của API $< 15\text{ms}$.
2. **Kích hoạt sự cố (Inject Fault):**
   * Người thuyết trình chạy lệnh:
     ```bash
     python scripts/trigger_incident.py --fault --device FRIDGE-KITCHEN-01
     ```
   * Simulator lập tức tăng nhiệt độ ngăn mát của `FRIDGE-KITCHEN-01` lên dốc đứng và bật cờ `door_open: true`.
3. **Cảnh báo nổ:**
   * Backend phát hiện nhiệt độ vượt ngưỡng $10^\circ\text{C}$ và ghi log `[INCIDENT_ALERT]`.
   * **Datadog Monitor** lập tức chuyển sang trạng thái **ALERT (Màu Đỏ)**:
     > `🔥 [CRITICAL] Tủ lạnh FRIDGE-KITCHEN-01 phát hiện quá nhiệt nguy hiểm: 17.5°C!`

---

### BƯỚC 2: ĐIỀU TRA (INVESTIGATE) - "Tìm ra nguyên nhân gốc rễ"
1. **Truy vết qua Datadog APM & Logs:**
   * Mở giao diện **Datadog Logs**: Thấy hàng loạt log error đỏ xuất hiện với device `FRIDGE-KITCHEN-01`.
   * Bấm nút **View Trace** từ dòng log để nhảy sang **Datadog APM Tracing**:
     * Thấy span HTTP `POST /api/telemetry/ingest`.
     * Xem chi tiết metadata tag: Thấy trường `door_open = true` và `power_watts = 175W` kéo dài hơn 5 phút.
2. **Đối chiếu với MongoDB Aggregation Analytics:**
   * Gọi API phân tích xu hướng:
     ```http
     GET http://127.0.0.1:8000/api/analytics/trend?device_id=FRIDGE-KITCHEN-01&compartment=fridge
     ```
   * Kết quả sử dụng toán tử `$setWindowFields` của MongoDB cho thấy `movingAvgTemp` tăng liên tục từ 4.0 lên 17.8°C $\to$ **Nguyên nhân gốc rễ:** Cửa tủ lạnh bị mở quên đóng, khiến hệ thống làm lạnh bị vô hiệu hóa dù máy nén đã hoạt động quá tải.

---

### BƯỚC 3: PHẢN ỨNG (RESPOND) - "Khắc phục và chứng minh bằng dữ liệu"
1. **Thực thi hành động khắc phục:**
   * Người thuyết trình chạy lệnh xử lý sự cố (giả lập kích hoạt chốt đóng cửa tự động & bật chế độ làm lạnh tăng cường):
     ```bash
     python scripts/trigger_incident.py --resolve --device FRIDGE-KITCHEN-01
     ```
   * Request được gửi sang `POST /api/incident/respond` và ghi nhận trạng thái vào MongoDB collection `incidents`.
2. **Chứng minh hệ thống đã hồi phục:**
   * Cửa tủ được đóng lại (`door_open: false`).
   * Máy nén làm lạnh nhanh đưa nhiệt độ từ $18^\circ\text{C}$ hạ dần đều về lại $4.0^\circ\text{C}$.
   * **Datadog Dashboard:** Biểu đồ nhiệt độ hạ xuống vùng xanh an toàn.
   * **Datadog Monitor:** Tự động chuyển từ **ALERT (Đỏ)** sang **OK (Xanh)**.
   * Kết thúc kịch bản: Toàn bộ quá trình được lưu lại đầy đủ trên MongoDB và Datadog làm bằng chứng kiểm toán.
