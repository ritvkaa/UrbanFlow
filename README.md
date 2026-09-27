# 🏙️ UrbanFlow – Smart Crowd Monitoring System

AI-powered pedestrian movement analysis with real-time congestion detection, ML anomaly flagging, and route recommendations.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Database | SQLite via SQLAlchemy ORM |
| ML Engine | Scikit-learn IsolationForest + threshold logic |
| Frontend | Vanilla JS + Jinja2 templates |
| Data Simulation | NumPy realistic crowd generator |
| Tests | Pytest (12 tests, 100% pass) |

---

## Quick Start

```bash
# 1. Clone / unzip the project
cd urbanflow

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn main:app --reload --port 8000

# 4. Open your browser
# http://localhost:8000
```

That's it. The DB is auto-created, the ML model is trained on startup.

---

## Project Structure

```
urbanflow/
├── main.py                        # FastAPI app + lifespan (DB init, ML training)
├── requirements.txt
├── README.md
│
├── backend/
│   ├── models/
│   │   └── database.py            # SQLAlchemy models: Zone, CrowdReading, Alert, Route
│   ├── ml/
│   │   └── analyzer.py            # IsolationForest anomaly detection + classify_density
│   ├── services/
│   │   ├── simulator.py           # Realistic crowd data generator (20 zones)
│   │   └── alert_service.py       # Alert generation, persistence, acknowledgement
│   └── routers/
│       └── api.py                 # All REST endpoints
│
├── frontend/
│   ├── templates/
│   │   └── index.html             # Dashboard HTML (Jinja2)
│   └── static/
│       ├── css/style.css          # Full dark cyberpunk stylesheet
│       └── js/app.js              # Frontend JS — fetches real API
│
├── data/
│   └── sample_crowd_data.csv      # Upload test file
│
└── tests/
    └── test_api.py                # 12 pytest tests
```

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Live dashboard UI |
| GET | `/health` | Health check |
| GET | `/api/zones` | All 20 zones with latest readings |
| POST | `/api/readings/refresh` | Generate + analyse new readings |
| POST | `/api/readings/upload` | Upload custom CSV |
| GET | `/api/alerts?limit=20` | Recent alerts |
| POST | `/api/alerts/{id}/ack` | Acknowledge an alert |
| GET | `/api/routes` | ML-scored route recommendations |
| GET | `/api/stats` | Aggregated system metrics |
| POST | `/api/simulate/spike` | Force congestion in zones (JSON array) |
| POST | `/api/simulate/clear` | Clear all spikes |
| GET | `/api/history?zone_id=A1&limit=60` | Historical readings |

Interactive docs: **http://localhost:8000/docs**

---

## ML Engine

### 1. Threshold-Based Classification
```
Density (people/m²) → Status
< 0.7              → LOW       (no action)
0.7 – 1.5         → MEDIUM    (monitor)
1.5 – 2.5         → HIGH      (warning)
> 2.5              → CRITICAL  (alert)
```

### 2. Anomaly Detection (IsolationForest)
- Trains on 80 rounds of synthetic historical data at startup
- Flags readings that deviate from learned normal patterns
- Shown as ⚡ markers on the heatmap

### 3. Route Scoring
- 4 pre-defined routes scored 0–100
- Penalty applied for each congested zone on route path
- Status: CLEAR (≥70), BUSY (≥40), BLOCKED (<40)

---

## Dashboard Features

- **Live Heatmap** — 20 zones, color-coded by density (click for tooltip)
- **Alert Feed** — Real-time alerts from backend, click to acknowledge
- **Footfall Bar Chart** — All zones, updates on every refresh
- **AI Route Suggestions** — ML-scored, sorted by safety score
- **History Trend Chart** — Canvas-rendered density timeline per zone
- **CSV Upload** — Drop your own data file in
- **Spike Simulation** — Test congestion scenarios
- **Auto-Refresh** — 10-second polling mode

---

## Running Tests

```bash
pytest tests/ -v
```

Expected: **12 passed**

---

## Deployment

### Local (development)
```bash
uvicorn main:app --reload --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (optional)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Sample CSV Format

Upload your own readings at `/api/readings/upload`:

```csv
zone_id,people_count,area_sqm
A1,120,50
B3,400,150
C4,135,45
```
