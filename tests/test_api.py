"""
Automated Integration Tests for Smart Hydroponics Farm API.
Kiểm tra tính đúng đắn của các endpoint mà không cần bắt buộc có live DB.
"""

import sys
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Thêm thư mục backend vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data

def test_dashboard_endpoint():
    response = client.get("/")
    assert response.status_code == 200

def test_incident_respond_endpoint():
    with patch("app.main.get_database") as mock_db:
        mock_db.return_value.incidents.insert_one = MagicMock()
        payload = {
            "device_id": "HYDROPONIC-RACK-01",
            "action": "REVERSE_FLUSH_TEST",
            "notes": "Automated pytest run"
        }
        response = client.post("/api/incident/respond", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "remediated"
        assert data["action_taken"] == "REVERSE_FLUSH_TEST"

def test_telemetry_ingest_endpoint():
    with patch("app.main.get_database") as mock_db:
        mock_coll = MagicMock()
        mock_coll.insert_many.return_value.inserted_ids = ["id1", "id2"]
        mock_db.return_value.__getitem__.return_value = mock_coll

        payload = {
            "readings": [
                {
                    "ts": "2026-11-04T10:00:00Z",
                    "sensor": {
                        "id": "HYDROPONIC-RACK-01",
                        "zone": "Balcony 1F",
                        "crop": "Lettuce",
                        "system_type": "NFT-Vertical"
                    },
                    "ph": 6.1,
                    "ec_ppm": 950.0,
                    "water_temp": 21.5,
                    "water_level_pct": 88.0,
                    "pump_flow_lpm": 4.5
                }
            ]
        }
        response = client.post("/api/telemetry/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["inserted_mongo"] == 2

if __name__ == "__main__":
    print("Running integration tests...")
    test_health_endpoint()
    print("✅ test_health_endpoint passed")
    test_dashboard_endpoint()
    print("✅ test_dashboard_endpoint passed")
    test_incident_respond_endpoint()
    print("✅ test_incident_respond_endpoint passed")
    test_telemetry_ingest_endpoint()
    print("✅ test_telemetry_ingest_endpoint passed")
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
