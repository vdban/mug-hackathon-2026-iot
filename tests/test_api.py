"""
Automated Integration Tests for Smart Fridge IoT API.
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
            "device_id": "FRIDGE-KITCHEN-01",
            "compartment": "fridge",
            "action": "CLOSE_DOOR_TEST",
            "notes": "Automated pytest run"
        }
        response = client.post("/api/incident/respond", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "remediated"
        assert data["action_taken"] == "CLOSE_DOOR_TEST"

def test_telemetry_ingest_endpoint():
    with patch("app.main.get_database") as mock_db:
        mock_coll = MagicMock()
        mock_coll.insert_many.return_value.inserted_ids = ["id1", "id2"]
        mock_db.return_value.__getitem__.return_value = mock_coll

        payload = {
            "readings": [
                {
                    "ts": "2026-11-03T10:00:00Z",
                    "sensor": {
                        "id": "FRIDGE-KITCHEN-01",
                        "compartment": "fridge",
                        "model": "Inverter Pro 550L"
                    },
                    "temperature": 4.5,
                    "humidity": 65.0,
                    "door_open": False,
                    "power_watts": 60.0
                }
            ]
        }
        response = client.post("/api/telemetry/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["inserted_mongo"] == 2
