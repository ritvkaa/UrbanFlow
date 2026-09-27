"""
UrbanFlow REST API
Endpoints:
  GET  /api/zones            - list all zones with current readings
  POST /api/readings/refresh - generate + analyse a fresh round of readings
  POST /api/readings/upload  - upload CSV of custom readings
  GET  /api/alerts           - recent alerts
  POST /api/alerts/{id}/ack  - acknowledge an alert
  GET  /api/routes           - route recommendations
  GET  /api/stats            - aggregated metrics
  POST /api/simulate/spike   - trigger congestion spike in specified zones
  POST /api/simulate/clear   - clear all spikes
  GET  /api/history          - last N readings per zone (for charts)
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
from datetime import datetime

from backend.models.database import get_db, Zone, CrowdReading
from backend.ml.analyzer import (
    analyse_reading, bulk_analyse, recommend_routes,
    compute_metrics, get_detector,
)
from backend.services.simulator import (
    generate_readings, get_zone_meta, set_spike, clear_spikes,
)
from backend.services.alert_service import (
    generate_alerts_from_readings, get_recent_alerts, acknowledge_alert,
)

router = APIRouter(prefix="/api")


# ─── Zones ───────────────────────────────────────────────────────────────────

@router.get("/zones")
def list_zones(db: Session = Depends(get_db)):
    """All zones with latest crowd reading."""
    zones = get_zone_meta()
    result = []
    for z in zones:
        latest = (
            db.query(CrowdReading)
            .filter(CrowdReading.zone_id == z["zone_id"])
            .order_by(CrowdReading.timestamp.desc())
            .first()
        )
        result.append({
            **z,
            "latest": {
                "people_count": latest.people_count if latest else 0,
                "density":      latest.density      if latest else 0,
                "status":       latest.status       if latest else "LOW",
                "congested":    latest.congested     if latest else False,
                "anomaly":      latest.anomaly       if latest else False,
                "timestamp":    latest.timestamp.isoformat() if latest else None,
            } if latest else None,
        })
    return result


# ─── Readings ────────────────────────────────────────────────────────────────

@router.post("/readings/refresh")
def refresh_readings(db: Session = Depends(get_db)):
    """Generate a new round of simulated readings, analyse, persist."""
    raw = generate_readings()
    analysed = bulk_analyse(raw)

    # Enrich with zone names from raw
    name_map = {r["zone_id"]: r["name"] for r in raw}

    for r in analysed:
        r["name"] = name_map.get(r["zone_id"], r["zone_id"])
        db.add(CrowdReading(
            zone_id=     r["zone_id"],
            people_count=r["people_count"],
            density=     r["density"],
            status=      r["status"],
            congested=   r["congested"],
            anomaly=     r["anomaly"],
            timestamp=   datetime.utcnow(),
        ))

    db.commit()

    alerts = generate_alerts_from_readings(analysed, db)
    metrics = compute_metrics(analysed)
    congested_zones = [r["zone_id"] for r in analysed if r["congested"]]
    status_map = {r["zone_id"]: r["status"] for r in analysed}
    routes = recommend_routes(congested_zones, status_map)

    return {
        "readings": analysed,
        "alerts":   alerts,
        "metrics":  metrics,
        "routes":   routes,
    }


@router.post("/readings/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accept UrbanFlow CSV or pedestrian_dataset.csv format."""

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted.")

    contents = await file.read()

    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV parse error: {e}")

    # Normalize column names
    original_columns = df.columns.tolist()
    normalized = {
        col: col.strip().lower().replace(" ", "_")
        for col in df.columns
    }
    df.rename(columns=normalized, inplace=True)

    # Find zone/location column
    zone_col = next(
        (
            col for col in df.columns
            if col in {
                "zone_id",
                "location_id",
                "location",
                "zone"
            }
        ),
        None
    )

    # Find pedestrian/footfall column
    people_col = next(
        (
            col for col in df.columns
            if col in {
                "people_count",
                "pedestrian_count",
                "pedestrians",
                "footfall",
                "count",
                "people",
                "total_of_directions"
            }
        ),
        None
    )

    if zone_col is None:
        raise HTTPException(
            status_code=422,
            detail=f"Could not find a zone/location column. Found: {original_columns}"
        )

    if people_col is None:
        raise HTTPException(
            status_code=422,
            detail=f"Could not find a pedestrian/footfall/count column. Found: {original_columns}"
        )

    # Area is optional for pedestrian_dataset.csv
    area_col = next(
        (
            col for col in df.columns
            if col in {
                "area_sqm",
                "area",
                "zone_area"
            }
        ),
        None
    )

    # Build the format expected by bulk_analyse()
    # Aggregate the large pedestrian dataset by location first
    df = (
        df.groupby(zone_col, as_index=False)[people_col]
        .mean()
    )

    readings = []

    for _, row in df.iterrows():

        zone_id = str(row[zone_col]).strip()

    # Convert numeric Location_ID 1–20 → A1–D5
    if zone_id.isdigit():
        n = int(zone_id)

        if 1 <= n <= 20:
            row_num = (n - 1) // 5
            col_num = (n - 1) % 5
            zone_id = f"{chr(65 + row_num)}{col_num + 1}"

    try:
        people_count = float(row[people_col])
    except (ValueError, TypeError):
        people_count = 0

    readings.append({
        "zone_id": zone_id,
        "people_count": people_count,
        "area_sqm": 100
    })

    analysed = bulk_analyse(readings)

    for r in analysed:
        db.add(CrowdReading(
            zone_id=r["zone_id"],
            people_count=r["people_count"],
            density=r["density"],
            status=r["status"],
            congested=r["congested"],
            anomaly=r["anomaly"],
            timestamp=datetime.utcnow(),
        ))

    db.commit()

    alerts = generate_alerts_from_readings(analysed, db)
    metrics = compute_metrics(analysed)

    return {
        "rows_processed": len(analysed),
        "metrics": metrics,
        "alerts": alerts
    }

# ─── Alerts ──────────────────────────────────────────────────────────────────

@router.get("/alerts")
def list_alerts(limit: int = Query(default=20, le=100), db: Session = Depends(get_db)):
    return get_recent_alerts(db, limit)


@router.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, db: Session = Depends(get_db)):
    ok = acknowledge_alert(alert_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"acknowledged": True}


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/routes")
def get_routes(db: Session = Depends(get_db)):
    latest_per_zone = {}
    for r in db.query(CrowdReading).order_by(CrowdReading.timestamp.desc()).limit(200).all():
        if r.zone_id not in latest_per_zone:
            latest_per_zone[r.zone_id] = r

    congested = [zid for zid, r in latest_per_zone.items() if r.congested]
    status_map = {zid: r.status for zid, r in latest_per_zone.items()}
    return recommend_routes(congested, status_map)


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    latest_per_zone = {}
    for r in db.query(CrowdReading).order_by(CrowdReading.timestamp.desc()).limit(200).all():
        if r.zone_id not in latest_per_zone:
            latest_per_zone[r.zone_id] = r

    if not latest_per_zone:
        return {"message": "No data yet. Call /api/readings/refresh first."}

    readings = [
        {
            "zone_id":      r.zone_id,
            "people_count": r.people_count,
            "density":      r.density,
            "status":       r.status,
            "congested":    r.congested,
            "anomaly":      r.anomaly,
        }
        for r in latest_per_zone.values()
    ]
    metrics = compute_metrics(readings)
    metrics["ml_model_trained"] = get_detector().is_trained()
    metrics["total_alerts_today"] = db.query(CrowdReading).count()
    return metrics


# ─── Simulation controls ─────────────────────────────────────────────────────

@router.post("/simulate/spike")
def trigger_spike(zone_ids: List[str], db: Session = Depends(get_db)):
    """Force high density in specified zone IDs."""
    set_spike(zone_ids)
    return {"spiked_zones": zone_ids, "message": "Spike active. Call /api/readings/refresh to see effect."}


@router.post("/simulate/clear")
def clear_spike():
    clear_spikes()
    return {"message": "All spikes cleared."}


# ─── History ─────────────────────────────────────────────────────────────────

@router.get("/history")
def get_history(
    zone_id: Optional[str] = Query(default=None),
    limit: int = Query(default=60, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(CrowdReading).order_by(CrowdReading.timestamp.desc())
    if zone_id:
        q = q.filter(CrowdReading.zone_id == zone_id)
    rows = q.limit(limit).all()
    return [
        {
            "zone_id":      r.zone_id,
            "people_count": r.people_count,
            "density":      r.density,
            "status":       r.status,
            "congested":    r.congested,
            "anomaly":      r.anomaly,
            "timestamp":    r.timestamp.isoformat(),
        }
        for r in reversed(rows)
    ]
