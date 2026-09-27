"""Alert generation and management service."""
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.models.database import Alert, CrowdReading


SEVERITY_MAP = {
    "CRITICAL": "CRITICAL",
    "HIGH":     "WARNING",
    "MEDIUM":   "INFO",
    "LOW":      "INFO",
}

SUGGESTIONS = {
    "CRITICAL": [
        "Immediately redirect pedestrians via Route Alpha or Delta.",
        "Deploy staff to manage crowd flow at entry points.",
        "Activate PA announcement for alternate exit routing.",
    ],
    "HIGH": [
        "Consider redirecting new arrivals to adjacent zones.",
        "Monitor closely — density approaching critical levels.",
        "Open overflow access points if available.",
    ],
    "MEDIUM": [
        "Keep monitoring; no action needed yet.",
        "Ensure signage is clear for alternate routes.",
    ],
    "ANOMALY": [
        "Unusual crowd pattern detected — verify sensor data.",
        "Possible event or incident causing surge. Investigate.",
    ],
}


def _pick_suggestion(status: str, anomaly: bool = False) -> str:
    import random
    if anomaly:
        return random.choice(SUGGESTIONS["ANOMALY"])
    return random.choice(SUGGESTIONS.get(status, SUGGESTIONS["MEDIUM"]))


def generate_alerts_from_readings(readings: List[Dict], db: Session) -> List[Dict]:
    """Persist alerts for congested/anomalous zones and return them."""
    alerts = []

    for r in readings:
        if r["congested"] or r.get("anomaly"):
            alert_type = "ANOMALY" if r.get("anomaly") and not r["congested"] else "CONGESTION"
            severity = "CRITICAL" if r["status"] == "CRITICAL" else \
                       "WARNING"  if r["status"] == "HIGH" else "INFO"

            message = (
                f"Zone {r['zone_id']} [{r.get('name', '')}]: "
                f"{r['people_count']} people detected. "
                f"Density {r['density']} p/m² — Status: {r['status']}."
            )
            if r.get("anomaly"):
                message += " ⚠ Anomalous reading flagged by ML model."

            suggestion = _pick_suggestion(r["status"], r.get("anomaly", False))

            db_alert = Alert(
                zone_id=r["zone_id"],
                alert_type=alert_type,
                severity=severity,
                message=message,
                suggestion=suggestion,
                timestamp=datetime.utcnow(),
            )
            db.add(db_alert)

            alerts.append({
                "zone_id":    r["zone_id"],
                "alert_type": alert_type,
                "severity":   severity,
                "message":    message,
                "suggestion": suggestion,
                "timestamp":  db_alert.timestamp.isoformat(),
            })

    db.commit()
    return alerts


def get_recent_alerts(db: Session, limit: int = 20) -> List[Dict]:
    rows = (
        db.query(Alert)
        .order_by(Alert.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id":           r.id,
            "zone_id":      r.zone_id,
            "alert_type":   r.alert_type,
            "severity":     r.severity,
            "message":      r.message,
            "suggestion":   r.suggestion,
            "acknowledged": r.acknowledged,
            "timestamp":    r.timestamp.isoformat(),
        }
        for r in rows
    ]


def acknowledge_alert(alert_id: int, db: Session) -> bool:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return False
    alert.acknowledged = True
    db.commit()
    return True
