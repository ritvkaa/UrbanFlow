"""
UrbanFlow ML Analysis Engine
- Threshold-based congestion classification
- Isolation Forest anomaly detection
- Route scoring
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


# ─── Thresholds (people per sq meter) ────────────────────────────────────────
THRESHOLDS = {
    "LOW":      (0.0,  0.7),
    "MEDIUM":   (0.7,  1.5),
    "HIGH":     (1.5,  2.5),
    "CRITICAL": (2.5, float("inf")),
}


def classify_density(density: float) -> Tuple[str, bool]:
    """Return (status_label, is_congested)."""
    for label, (lo, hi) in THRESHOLDS.items():
        if lo <= density < hi:
            return label, label in ("HIGH", "CRITICAL")
    return "CRITICAL", True


class AnomalyDetector:
    """
    Wraps sklearn IsolationForest.
    Trains on historical density windows; flags sudden spikes/drops.
    """

    def __init__(self, contamination: float = 0.1):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self._trained = False

    def train(self, densities: List[float]) -> None:
        if len(densities) < 10:
            logger.warning("Not enough data to train anomaly detector (%d samples)", len(densities))
            return
        X = np.array(densities).reshape(-1, 1)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._trained = True
        logger.info("Anomaly detector trained on %d samples", len(densities))

    def predict(self, density: float) -> bool:
        """Return True if the density reading is anomalous."""
        if not self._trained:
            return False
        X = np.array([[density]])
        X_scaled = self.scaler.transform(X)
        result = self.model.predict(X_scaled)
        return int(result[0]) == -1   # -1 = anomaly in sklearn

    def is_trained(self) -> bool:
        return self._trained


# One global detector instance per process
_detector = AnomalyDetector()


def get_detector() -> AnomalyDetector:
    return _detector


# ─── Congestion analysis ──────────────────────────────────────────────────────

def analyse_reading(zone_id: str, people_count: int, area_sqm: float) -> Dict:
    """Full analysis of a single zone reading."""
    density = round(people_count / max(area_sqm, 1), 3)
    status, congested = classify_density(density)
    anomaly = _detector.predict(density)

    return {
        "zone_id": zone_id,
        "people_count": people_count,
        "density": density,
        "status": status,
        "congested": congested,
        "anomaly": anomaly,
    }


def bulk_analyse(readings: List[Dict]) -> List[Dict]:
    """Analyse a list of zone readings and return enriched records."""
    results = []
    for r in readings:
        result = analyse_reading(r["zone_id"], r["people_count"], r["area_sqm"])
        results.append(result)
    return results


# ─── Route recommendation ─────────────────────────────────────────────────────

ROUTE_MAP = [
    {"route_name": "Alpha – North Corridor", "via_zones": "Library,Exit N,Parking",   "base_score": 90},
    {"route_name": "Beta – South Bypass",    "via_zones": "Garden,Exit S,Metro Link",  "base_score": 85},
    {"route_name": "Gamma – West Wing",      "via_zones": "Lobby,Hall B,Bus Stop",     "base_score": 70},
    {"route_name": "Delta – Emergency Exit", "via_zones": "Info Desk,Stage Exit,Gate 3","base_score": 95},
]


def recommend_routes(congested_zones: List[str], all_statuses: Dict[str, str]) -> List[Dict]:
    """Score and rank routes avoiding congested zones."""
    results = []
    for route in ROUTE_MAP:
        via = [z.strip() for z in route["via_zones"].split(",")]
        penalty = sum(20 for z in via if z in congested_zones)
        score = max(0, route["base_score"] - penalty)
        status = "CLEAR" if score >= 70 else "BUSY" if score >= 40 else "BLOCKED"
        results.append({
            **route,
            "score": score,
            "status": status,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ─── Metrics ──────────────────────────────────────────────────────────────────

def compute_metrics(readings: List[Dict]) -> Dict:
    if not readings:
        return {}

    statuses = [r["status"] for r in readings]
    congested = [r for r in readings if r["congested"]]
    anomalies = [r for r in readings if r.get("anomaly")]
    densities = [r["density"] for r in readings]

    return {
        "total_zones":       len(readings),
        "total_people":      sum(r["people_count"] for r in readings),
        "avg_density":       round(np.mean(densities), 3),
        "max_density":       round(max(densities), 3),
        "congested_count":   len(congested),
        "congestion_rate":   round(len(congested) / len(readings) * 100, 1),
        "anomaly_count":     len(anomalies),
        "status_breakdown":  {s: statuses.count(s) for s in ("LOW", "MEDIUM", "HIGH", "CRITICAL")},
    }
