"""
Automated Integration Tests for Smart Hydroponics Farm API.
Kiểm tra toàn bộ luồng Detect -> Investigate -> Respond và các endpoint MongoDB/Datadog
mà không phụ thuộc kết nối live tới MongoDB Atlas hay Datadog Cloud.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Thêm thư mục backend vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import _aquarium_actuators, _simulator_faults, app  # noqa: E402

client = TestClient(app)


def test_health_endpoint():
    with patch("app.main.check_db_health", return_value={"status": "connected", "database": "smart_aquarium_iot"}):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "datadog_connected" in data
    assert "firebase_connected" in data


def test_dashboard_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data_res = client.get("/data")
    assert data_res.status_code == 200
    data_html_res = client.get("/data.html")
    assert data_html_res.status_code == 200


def test_telemetry_ingest_normal():
    with patch("app.main.get_database") as mock_db, patch("app.main.send_metrics_to_datadog") as mock_metrics:
        mock_coll = MagicMock()
        mock_coll.insert_many.return_value.inserted_ids = ["id1"]
        mock_db.return_value.__getitem__.return_value = mock_coll

        payload = {
            "readings": [
                {
                    "ts": "2026-11-15T01:00:00Z",
                    "sensor": {
                        "id": "AQUA-TANK-01",
                        "zone": "Living Room 1F",
                        "crop": "Neon Tetra & Guppy",
                        "system_type": "Canister Bio-Filter",
                    },
                    "ph": 6.1,
                    "ec_ppm": 950.0,
                    "water_temp": 21.5,
                    "water_level_pct": 88.0,
                    "pump_flow_lpm": 4.5,
                }
            ]
        }
        response = client.post("/api/telemetry/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["inserted_mongo"] == 1
        assert data["alerts_triggered"] == 0
        mock_metrics.assert_called_once()


def test_telemetry_ingest_detects_fault_and_records_active_incident():
    with (
        patch("app.main.get_database") as mock_db,
        patch("app.main.send_metrics_to_datadog") as mock_metrics,
        patch("app.main.send_log_to_datadog") as mock_log,
        patch("app.main.send_incident_event") as mock_event,
    ):
        mock_coll = MagicMock()
        mock_coll.insert_many.return_value.inserted_ids = ["id1"]
        mock_db.return_value.__getitem__.return_value = mock_coll
        mock_db.return_value.incidents.find_one.return_value = None

        payload = {
            "readings": [
                {
                    "ts": "2026-11-15T01:05:00Z",
                    "sensor": {
                        "id": "AQUA-TANK-01",
                        "zone": "Living Room 1F",
                        "crop": "Neon Tetra & Guppy",
                        "system_type": "Canister Bio-Filter",
                    },
                    "ph": 8.2,
                    "ec_ppm": 700.0,
                    "water_temp": 22.0,
                    "water_level_pct": 25.0,
                    "pump_flow_lpm": 0.4,
                }
            ]
        }
        response = client.post("/api/telemetry/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["alerts_triggered"] == 1
        mock_db.return_value.incidents.insert_one.assert_called_once()
        mock_log.assert_called_once()
        mock_event.assert_called_once()
        mock_metrics.assert_called_once()


def test_simulator_control_and_incident_respond_with_mttr():
    _simulator_faults.clear()
    ctrl_res = client.post(
        "/api/simulator/control",
        json={"device_id": "AQUA-TANK-01", "action": "INJECT_FAULT", "reason": "Test fault"},
    )
    assert ctrl_res.status_code == 200
    assert ctrl_res.json()["faults"]["AQUA-TANK-01"] == "CLOG_AND_PH_DRIFT"

    state_res = client.get("/api/simulator/state")
    assert state_res.status_code == 200
    assert state_res.json()["faults"]["AQUA-TANK-01"] == "CLOG_AND_PH_DRIFT"

    detected_at = datetime.now(timezone.utc) - timedelta(seconds=12)
    with (
        patch("app.main.get_database") as mock_db,
        patch("app.main.send_log_to_datadog"),
        patch("app.main.send_incident_event"),
        patch("app.main.send_mttr_metric_to_datadog") as mock_mttr,
    ):
        mock_db.return_value.incidents.find_one.return_value = {
            "_id": "inc-1",
            "device_id": "AQUA-TANK-01",
            "status": "ACTIVE",
            "detected_at": detected_at,
        }
        res = client.post(
            "/api/incident/respond",
            json={"device_id": "AQUA-TANK-01", "action": "REVERSE_FLUSH_AND_DOSING_PH_DOWN"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "remediated"
        assert body["mttr_seconds"] >= 11.0
        mock_db.return_value.incidents.update_one.assert_called_once()
        mock_mttr.assert_called_once()
        assert _simulator_faults["AQUA-TANK-01"] is None


def test_datadog_webhook_triggers_remediation():
    with (
        patch("app.main.get_database") as mock_db,
        patch("app.main.send_log_to_datadog"),
        patch("app.main.send_incident_event"),
    ):
        mock_db.return_value.incidents.find_one.return_value = None
        res = client.post(
            "/api/webhooks/datadog",
            json={
                "alert_title": "[P1] Pipe Clogging",
                "alert_transition": "Triggered",
                "tags": "env:hackathon,rack_id:AQUA-TANK-01",
                "auto_remediate": True,
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "received"
        assert body["device_id"] == "AQUA-TANK-01"
        assert body["remediation"]["status"] == "remediated"


def test_analytics_and_latest_and_incidents_endpoints():
    with patch("app.main.get_database") as mock_db:
        mock_coll = MagicMock()
        mock_coll.aggregate.return_value = [{"rack": "AQUA-TANK-01", "avgPh": 6.1}]
        mock_db.return_value.__getitem__.return_value = mock_coll
        mock_db.return_value.incidents.find.return_value.sort.return_value.limit.return_value = [
            {"device_id": "AQUA-TANK-01", "status": "RESOLVED"}
        ]

        r_latest = client.get("/api/telemetry/latest")
        assert r_latest.status_code == 200
        assert r_latest.json()["count"] == 1

        r_hourly = client.get("/api/analytics/hourly")
        assert r_hourly.status_code == 200
        assert r_hourly.json()["count"] == 1

        r_trend = client.get("/api/analytics/trend?rack_id=AQUA-TANK-01")
        assert r_trend.status_code == 200
        assert r_trend.json()["count"] == 1

        r_inc = client.get("/api/incidents")
        assert r_inc.status_code == 200
        assert r_inc.json()["count"] == 1


def test_aquarium_actuator_controls():
    initial_bubbler = bool(_aquarium_actuators.get("bubbler_on", True))
    prev_fed = _aquarium_actuators.get("last_fed_at")
    try:
        with (
            patch("app.main.send_log_to_datadog"),
            patch("app.main.send_incident_event"),
            patch("app.main.sync_state_to_firebase") as mock_fb_sync,
        ):
            r_toggle_1 = client.post(
                "/api/simulator/control",
                json={"device_id": "AQUA-TANK-01", "action": "TOGGLE_BUBBLER", "reason": "Test bubbler toggle"},
            )
            assert r_toggle_1.status_code == 200
            assert r_toggle_1.json()["actuators"]["bubbler_on"] is (not initial_bubbler)

            r_toggle_2 = client.post(
                "/api/simulator/control",
                json={"device_id": "AQUA-TANK-01", "action": "TOGGLE_BUBBLER", "reason": "Test bubbler restore"},
            )
            assert r_toggle_2.status_code == 200
            assert r_toggle_2.json()["actuators"]["bubbler_on"] is initial_bubbler

            r_feed = client.post(
                "/api/simulator/control",
                json={"device_id": "AQUA-TANK-01", "action": "FEED_FISH", "reason": "Test smart feeder"},
            )
            assert r_feed.status_code == 200
            feed_data = r_feed.json()
            assert feed_data["status"] == "ok"
            assert feed_data["actuators"]["last_fed_at"] is not None
            assert mock_fb_sync.called

            state_res = client.get("/api/simulator/state")
            assert state_res.status_code == 200
            assert state_res.json()["actuators"]["last_fed_at"] == feed_data["actuators"]["last_fed_at"]
    finally:
        _aquarium_actuators["bubbler_on"] = initial_bubbler
        _aquarium_actuators["last_fed_at"] = prev_fed

