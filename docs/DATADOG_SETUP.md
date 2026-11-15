# Kiến trúc Observability & Cấu hình Datadog: Smart Aquarium

Tài liệu này mô tả hệ thống giám sát **Datadog Observability (`datadoghq.com`)** được cấu hình qua [backend/app/datadog_service.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/backend/app/datadog_service.py) và [scripts/provision_datadog.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/scripts/provision_datadog.py).

---

## 1. Dashboard Vận hành Trực quan
* **Dashboard Live URL:** [Smart Operations Dashboard (`n72-nmb-pp6`)](https://app.datadoghq.com/dashboard/n72-nmb-pp6/smart-hydroponics-fleet-operations-mongodb--datadog)
* **Template JSON:** [datadog/dashboard.json](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/datadog/dashboard.json)
* **Các tín hiệu chính hiển thị trên Dashboard:**
  1. `smartfarm.pump_flow_lpm` *(gauge, by `rack_id`)* — Lưu lượng tuần hoàn qua lọc sinh học (`< 1.0 LPM` là tắc lọc).
  2. `smartfarm.ph` *(gauge, by `rack_id`)* — Độ pH nước bể cá (`> 7.6` hoặc `< 5.0` là vùng nguy hiểm).
  3. `smartfarm.ec_ppm` — Tổng chất rắn hòa tan / độ dẫn TDS (ppm).
  4. `smartfarm.water_temp` & `smartfarm.water_level_pct` — Nhiệt độ nước (°C) và mực nước bể (%).
  5. `smartfarm.ingest.latency_ms` — Độ trễ thực thi lệnh `insert_many` vào MongoDB Atlas Time Series (hiệu năng hệ thống).
  6. `smartfarm.alerts.count` & `smartfarm.incidents.mttr_seconds` — Đếm số lần phát sinh cảnh báo và đo **Mean Time To Resolution (giây)** sau mỗi lần xử lý sự cố.

---

## 2. Monitors / Alerts Gắn với Rủi ro Vận hành
Được tự động tạo bằng `python scripts/provision_datadog.py`:
1. **Monitor P1 — Tắc nghẽn lọc tuần hoàn (ID `345173530`):**
   * Định nghĩa tại [datadog/monitor_pipe_clog.json](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/datadog/monitor_pipe_clog.json).
   * Query: `avg(last_1m):avg:smartfarm.pump_flow_lpm{*} by {rack_id} < 1` (Critical `< 1.0 LPM`, Warning `< 2.0 LPM`).
2. **Monitor P1 — Đột biến Log Cảnh báo / Sốc kiềm pH (ID `345174672` & Fallback pH Drift `345173822`):**
   * Định nghĩa tại [datadog/monitor_farm_alert_log.json](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/datadog/monitor_farm_alert_log.json) và logic fallback `avg(last_1m):avg:smartfarm.ph{*} by {rack_id} > 7.5` trong [scripts/provision_datadog.py](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/scripts/provision_datadog.py).

---

## 3. Năng lực Bổ sung & Liên kết Đa chiều (Metrics ↔ Logs ↔ Traces ↔ MongoDB)
1. **Log Management (HTTP Intake v2):** Mọi sự cố `[AQUA_ALERT]`, hành động khôi phục `[INCIDENT_RESOLVED]`, và `[DATADOG_WEBHOOK]` đều được đẩy bất đồng bộ qua `ThreadPoolExecutor` lên `https://http-intake.logs.datadoghq.com/api/v2/logs`.
2. **APM Distributed Tracing (`ddtrace`):** Tự động gắn `DatadogTraceFilter` và `get_current_trace_context()` để nhúng `dd.trace_id` & `dd.span_id` vào cả Datadog Logs lẫn document trong MongoDB `incidents`.
3. **Event Stream & Context Tags đồng nhất:** Gửi sự kiện lên `/api/v1/events` khi sự cố bùng phát (`alert_type: "error"`) và khi khắc phục (`alert_type: "success"`), gắn đồng bộ tags:
   * `rack_id:<AQUA-TANK-01|02|03>`
   * `crop:<Neon Tetra & Guppy|...>`
   * `zone:<Living Room 1F|...>`
   * `env:hackathon`, `service:smart-aquarium-service`
4. **Auto-Remediation Webhook (`POST /api/webhooks/datadog`):** Hỗ trợ nhận alert webhook từ Datadog Monitor và tự động thực thi `AUTO_WEBHOOK_REVERSE_FLUSH_AND_PH_DOWN` nếu `"auto_remediate": true`.

---

## 4. Tùy chọn chạy kèm Datadog Agent (APM Traces Local)
Mặc định FastAPI đã gửi trực tiếp Metrics, Logs, Events và Latency qua Datadog HTTP API mà không cần Agent local. Nếu muốn gửi đầy đủ **APM Trace Flamegraph** qua cổng `8126`, có thể bật [docker-compose.yml](file:///f:/Project%20nghịch%20linh%20tinh/mug-hackathon-2026-iot/docker-compose.yml):
```powershell
docker compose up --build
```
Hoặc chạy backend qua `ddtrace-run`:
```powershell
cd backend
ddtrace-run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
