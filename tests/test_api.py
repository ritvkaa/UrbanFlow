"""
UrbanFlow test suite
Run: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.models.database import init_db
from backend.ml.analyzer import get_detector
from backend.services.simulator import generate_historical

# Boot DB and ML model once for the test session
init_db()
history = generate_historical(n_rounds=60)
get_detector().train([h["density"] for h in history])

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_zones_list():
    r = client.get("/api/zones")
    assert r.status_code == 200
    zones = r.json()
    assert len(zones) == 20
    assert "zone_id" in zones[0]
    assert "area_sqm" in zones[0]


def test_refresh_readings():
    r = client.post("/api/readings/refresh")
    assert r.status_code == 200
    data = r.json()
    assert "readings" in data
    assert "metrics" in data
    assert "routes" in data
    assert len(data["readings"]) == 20
    for reading in data["readings"]:
        assert "density" in reading
        assert "status" in reading
        assert reading["status"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert isinstance(reading["congested"], bool)


def test_stats():
    client.post("/api/readings/refresh")
    r = client.get("/api/stats")
    assert r.status_code == 200
    stats = r.json()
    assert "total_zones" in stats
    assert "congestion_rate" in stats
    assert 0 <= stats["congestion_rate"] <= 100


def test_alerts():
    client.post("/api/readings/refresh")
    r = client.get("/api/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_routes():
    client.post("/api/readings/refresh")
    r = client.get("/api/routes")
    assert r.status_code == 200
    routes = r.json()
    assert len(routes) > 0
    assert "route_name" in routes[0]
    assert "status" in routes[0]
    assert routes[0]["status"] in ("CLEAR", "BUSY", "BLOCKED")


def test_simulate_spike_and_clear():
    r = client.post("/api/simulate/spike", json=["C4", "A2"])
    assert r.status_code == 200

    data = client.post("/api/readings/refresh").json()
    spike_zones = {r["zone_id"]: r for r in data["readings"]}
    assert spike_zones["C4"]["people_count"] > 0

    r = client.post("/api/simulate/clear")
    assert r.status_code == 200


def test_history():
    client.post("/api/readings/refresh")
    r = client.get("/api/history?limit=10")
    assert r.status_code == 200
    hist = r.json()
    assert isinstance(hist, list)


def test_csv_upload():
    csv_content = b"zone_id,people_count,area_sqm\nA1,120,50\nB2,80,90\nC3,200,180\n"
    r = client.post(
        "/api/readings/upload",
        files={"file": ("test.csv", csv_content, "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rows_processed"] == 3


def test_analyzer_classify():
    from backend.ml.analyzer import classify_density
    assert classify_density(0.3) == ("LOW", False)
    assert classify_density(1.0) == ("MEDIUM", False)
    assert classify_density(2.0) == ("HIGH", True)
    assert classify_density(3.0) == ("CRITICAL", True)


def test_analyzer_bulk():
    from backend.ml.analyzer import bulk_analyse
    readings = [
        {"zone_id": "A1", "people_count": 10, "area_sqm": 50},
        {"zone_id": "B3", "people_count": 400, "area_sqm": 50},
    ]
    results = bulk_analyse(readings)
    assert results[0]["status"] == "LOW"
    assert results[1]["status"] == "CRITICAL"
    assert results[1]["congested"] is True


def test_metrics():
    from backend.ml.analyzer import compute_metrics
    readings = [
        {"zone_id": "A1", "people_count": 10, "density": 0.2, "status": "LOW", "congested": False, "anomaly": False},
        {"zone_id": "C4", "people_count": 200, "density": 4.4, "status": "CRITICAL", "congested": True, "anomaly": False},
    ]
    m = compute_metrics(readings)
    assert m["total_zones"] == 2
    assert m["congested_count"] == 1
    assert m["congestion_rate"] == 50.0
