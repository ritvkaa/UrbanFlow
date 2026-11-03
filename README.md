# UrbanFlow — Smart Crowd Monitoring System

UrbanFlow is a crowd monitoring prototype designed to analyse pedestrian density across multiple urban zones, identify unusual crowd patterns, and provide congestion-aware route recommendations.

The system combines density-based classification, machine learning-based anomaly detection, interactive visualisations, and a REST API to make crowd conditions easier to monitor and understand.

## Overview

UrbanFlow monitors pedestrian activity across 20 predefined zones. Each zone is analysed using its pedestrian count and available area to calculate crowd density.

The system then:
- Classifies zones according to crowd density.
- Detects unusual readings using an Isolation Forest model.
- Displays congestion levels through an interactive dashboard.
- Generates alerts for congested or anomalous conditions.
- Ranks predefined routes using congestion-based scoring.
- Supports CSV uploads for analysing custom crowd data.

**Note:** The current prototype uses simulated pedestrian readings and uploaded CSV data. It is not connected to live CCTV feeds or real-world sensor networks.

## Features

### Crowd Monitoring Dashboard
- Interactive heatmap displaying crowd density across 20 zones.
- Colour-coded congestion levels.
- Zone-level information and density metrics.
- Footfall bar charts and historical density trends.
- Automatically refreshed dashboard data.

### Machine Learning-Based Anomaly Detection
- Uses Scikit-learn's Isolation Forest algorithm.
- Trains on synthetic historical density readings generated during application startup.
- Flags readings that deviate from learned patterns.
- Displays detected anomalies in the monitoring interface.

### Density Classification

Crowd density is calculated as:

`Density = Number of People / Area (m²)`

| Density (people/m²) | Classification |
|---|---|
| Below 0.7 | LOW |
| 0.7 – below 1.5 | MEDIUM |
| 1.5 – below 2.5 | HIGH |
| 2.5 and above | CRITICAL |

### Congestion Alerts
- Generates alerts based on congestion and anomaly conditions.
- Stores alerts for later review.
- Supports alert acknowledgement through the API.

### Route Recommendations
- Evaluates four predefined routes.
- Applies congestion penalties to route scores.
- Ranks routes according to their resulting scores.
- Categorises routes as CLEAR, BUSY, or BLOCKED.

### Custom Data Analysis
- Upload crowd readings through CSV files.
- Analyse custom zone-level pedestrian data.
- Simulate congestion spikes to test system behaviour.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Database | SQLite, SQLAlchemy |
| Machine Learning | Scikit-learn, Isolation Forest |
| Data Processing | NumPy, Pandas |
| Frontend | HTML, CSS, JavaScript, Jinja2 |
| Visualisation | Interactive heatmap, charts, Canvas |
| Testing | Pytest |

## System Architecture

The application follows a modular architecture:

1. **Frontend:** Displays crowd density, alerts, metrics, and route recommendations.
2. **API Layer:** Handles dashboard requests, data uploads, alerts, and simulation endpoints.
3. **Analysis Engine:** Calculates density, classifies congestion, and detects anomalies.
4. **Database Layer:** Stores zones, crowd readings, alerts, and route information.
5. **Data Simulator:** Generates synthetic pedestrian readings for testing and demonstration.

## Project Structure

```text
UrbanFlow/
├── main.py
├── requirements.txt
├── backend/
│   ├── models/
│   │   └── database.py
│   ├── ml/
│   │   └── analyzer.py
│   ├── services/
│   │   ├── simulator.py
│   │   └── alert_service.py
│   └── routers/
│       └── api.py
├── frontend/
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/
│       └── js/
├── data/
│   └── sample_crowd_data.csv
└── tests/
    └── test_api.py
```

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip

### Installation

Clone the repository:

```bash
git clone https://github.com/ritvkaa/UrbanFlow.git
cd UrbanFlow
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
uvicorn main:app --reload --port 8000
```

Open the dashboard:

```text
http://localhost:8000
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

The database is initialised and the anomaly detection model is trained when the application starts.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/health` | Application health check |
| GET | `/api/zones` | Retrieve zone information |
| POST | `/api/readings/refresh` | Generate and analyse readings |
| POST | `/api/readings/upload` | Upload custom CSV data |
| GET | `/api/alerts` | Retrieve recent alerts |
| POST | `/api/alerts/{id}/ack` | Acknowledge an alert |
| GET | `/api/routes` | Retrieve route recommendations |
| GET | `/api/stats` | Retrieve monitoring statistics |
| POST | `/api/simulate/spike` | Simulate congestion |
| POST | `/api/simulate/clear` | Clear simulated spikes |
| GET | `/api/history` | Retrieve historical readings |

## Running Tests

Run the test suite using:

```bash
pytest tests/ -v
```

The existing project test suite contains 12 tests.

## Future Improvements

- Integration with live pedestrian counting systems.
- Camera-based people detection and tracking.
- Dynamic route generation based on real-time map data.
- Deployment with a persistent production database.
- Improved anomaly detection using larger real-world datasets.

## Project Information

**Project:** UrbanFlow — Smart Crowd Monitoring System  
**Repository:** [github.com/ritvkaa/UrbanFlow](https://github.com/ritvkaa/UrbanFlow)

