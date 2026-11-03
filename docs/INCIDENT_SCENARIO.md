# Kịch bản Trình diễn Vận hành Thực tế: Smart Hydroponics Farm
### Chu trình 3 bước: Phát hiện (Detect) $\to$ Điều tra (Investigate) $\to$ Phản ứng (Respond)

Tài liệu này dùng làm kịch bản thuyết trình và quay video demo cho ban giám khảo cuộc thi MongoDB User Group Vietnam Hackathon 2026.

---

## 🎬 Bối cảnh Sự cố (Incident Scenario)
* **Tình huống:** Giàn xà lách thủy canh ban công (`HYDROPONIC-RACK-01`) sau 3 tuần sinh trưởng rễ phát triển quá rậm rạp làm nghẹt đường ống cấp dinh dưỡng hồi lưu (Clogging / Nutrient Lockout).
* **Hậu quả:** 
  * Lưu lượng tuần hoàn tụt dốc từ $4.5\text{ LPM} \to 0.2\text{ LPM}$.
  * Mực nước bồn rễ cạn kiệt xuống còn $15\%$.
  * Độ pH kiềm hóa vọt lên **8.2** (ngưỡng khóa rễ cây, không thể hấp thụ vi lượng sắt và nitơ, rau sẽ héo rũ và chết trong vòng vài giờ).

---

## ⏱️ Kịch bản 3 phút Demo trực tiếp

### BƯỚC 1: PHÁT HIỆN (DETECT) - "Biết có chuyện trước người dùng"
1. **Trạng thái ban đầu:**
   * 3 giàn thủy canh gửi dữ liệu đều đặn mỗi 2 giây.
   * Dashboard hiển thị màu xanh tối ưu: Lưu lượng bơm 4.5 LPM, pH duy trì 6.1 (vùng lý tưởng), p95 latency của API $< 15\text{ms}$.
2. **Kích hoạt sự cố (Inject Fault):**
   * Người thuyết trình chạy lệnh:
     ```bash
     python scripts/trigger_incident.py --fault --device HYDROPONIC-RACK-01
     ```
   * Hoặc bấm nút đỏ **"Kích hoạt sự cố"** ngay trên giao diện Web UI tại [http://127.0.0.1:8000](http://127.0.0.1:8000).
   * Simulator lập tức làm lưu lượng bơm tụt dốc về 0.3 LPM và pH vọt lên 8.2.
3. **Cảnh báo nổ:**
   * Backend phát hiện lưu lượng $< 1.0\text{ LPM}$ và $\text{pH} > 7.6$, lập tức ghi log `[FARM_ALERT]`.
   * **Datadog Monitor** lập tức chuyển sang trạng thái **ALERT (Màu Đỏ)**:
     > `🌱 [CRITICAL] Giàn xà lách HYDROPONIC-RACK-01 bị tắc nghẽn ống tuần hoàn & pH kiềm hóa (8.2)! Nguy cơ cháy rễ!`

---

### BƯỚC 2: ĐIỀU TRA (INVESTIGATE) - "Tìm ra nguyên nhân gốc rễ"
1. **Truy vết qua Datadog APM & Logs:**
   * Mở giao diện **Datadog Logs**: Thấy log error đỏ xuất hiện với device `HYDROPONIC-RACK-01`.
   * Bấm nút **View Trace** từ dòng log để nhảy sang **Datadog APM Tracing**:
     * Thấy span HTTP `POST /api/telemetry/ingest`.
     * Xem chi tiết metadata tag: Thấy trường `pump_flow_lpm = 0.2` và `water_level_pct = 15%`.
2. **Đối chiếu với MongoDB Aggregation Analytics:**
   * Gọi API phân tích xu hướng:
     ```http
     GET http://127.0.0.1:8000/api/analytics/trend?rack_id=HYDROPONIC-RACK-01
     ```
   * Kết quả sử dụng toán tử `$setWindowFields` của MongoDB cho thấy `movingAvgFlowLpm` giảm dốc đứng liên tục qua 5 mẫu đo $\to$ **Nguyên nhân gốc rễ:** Nghẹt cơ học tại đường ống cấp hồi lưu làm nước không thể tuần hoàn, dẫn đến kiềm hóa cục bộ dung dịch bồn rễ.

---

### BƯỚC 3: PHẢN ỨNG (RESPOND) - "Khắc phục và chứng minh bằng dữ liệu"
1. **Thực thi hành động khắc phục:**
   * Người thuyết trình chạy lệnh xử lý sự cố:
     ```bash
     python scripts/trigger_incident.py --resolve --device HYDROPONIC-RACK-01
     ```
   * Hoặc bấm nút xanh **"Khắc phục tự động"** trên giao diện Web UI.
   * Hệ thống kích hoạt chu trình van xả ngược áp lực cao (Reverse Pulse Flush) để thổi cặn rễ cây và bơm định lượng pH-Down.
2. **Chứng minh hệ thống đã hồi phục:**
   * Đường ống được thông tắc $\to$ Lưu lượng nước vọt lên lại $4.5\text{ LPM}$.
   * Dung dịch được cân bằng $\to$ Độ pH hạ dần từ $8.2$ về mức $6.1$ lý tưởng.
   * Mực nước bồn dâng lên lại $88\%$.
   * **Datadog Dashboard:** Đồ thị đường lưu lượng và pH phục hồi về vùng xanh an toàn.
   * **Datadog Monitor:** Tự động chuyển từ **ALERT (Đỏ)** sang **OK (Xanh)**.
