"""
UrbanFlow Crowd Data Simulator
Generates realistic pedestrian footfall patterns with
time-of-day effects, random spikes, and zone personalities.
"""
import numpy as np
import random
from datetime import datetime
from typing import List, Dict

# Seed for reproducibility within a session
rng = np.random.default_rng()

ZONES = [
    {"zone_id": "A1", "name": "Main Gate",    "area_sqm": 50,  "capacity": 150, "location_x": 1, "location_y": 1, "base_traffic": 0.9},
    {"zone_id": "A2", "name": "Food Court",   "area_sqm": 80,  "capacity": 250, "location_x": 2, "location_y": 1, "base_traffic": 0.8},
    {"zone_id": "A3", "name": "Atrium",       "area_sqm": 120, "capacity": 300, "location_x": 3, "location_y": 1, "base_traffic": 0.6},
    {"zone_id": "A4", "name": "Parking Lot",  "area_sqm": 200, "capacity": 400, "location_x": 4, "location_y": 1, "base_traffic": 0.4},
    {"zone_id": "A5", "name": "Bus Stop",     "area_sqm": 40,  "capacity": 120, "location_x": 5, "location_y": 1, "base_traffic": 0.7},
    {"zone_id": "B1", "name": "Library",      "area_sqm": 90,  "capacity": 200, "location_x": 1, "location_y": 2, "base_traffic": 0.3},
    {"zone_id": "B2", "name": "Cafeteria",    "area_sqm": 70,  "capacity": 180, "location_x": 2, "location_y": 2, "base_traffic": 0.75},
    {"zone_id": "B3", "name": "Hall A",       "area_sqm": 150, "capacity": 500, "location_x": 3, "location_y": 2, "base_traffic": 0.5},
    {"zone_id": "B4", "name": "Corridor B4",  "area_sqm": 30,  "capacity": 80,  "location_x": 4, "location_y": 2, "base_traffic": 0.6},
    {"zone_id": "B5", "name": "Exit North",   "area_sqm": 35,  "capacity": 100, "location_x": 5, "location_y": 2, "base_traffic": 0.5},
    {"zone_id": "C1", "name": "Main Lobby",   "area_sqm": 60,  "capacity": 200, "location_x": 1, "location_y": 3, "base_traffic": 0.85},
    {"zone_id": "C2", "name": "Lift Area",    "area_sqm": 25,  "capacity": 60,  "location_x": 2, "location_y": 3, "base_traffic": 0.7},
    {"zone_id": "C3", "name": "Central Plaza","area_sqm": 180, "capacity": 600, "location_x": 3, "location_y": 3, "base_traffic": 0.65},
    {"zone_id": "C4", "name": "Metro Entry",  "area_sqm": 45,  "capacity": 150, "location_x": 4, "location_y": 3, "base_traffic": 0.9},
    {"zone_id": "C5", "name": "Garden",       "area_sqm": 300, "capacity": 500, "location_x": 5, "location_y": 3, "base_traffic": 0.2},
    {"zone_id": "D1", "name": "Main Stage",   "area_sqm": 200, "capacity": 800, "location_x": 1, "location_y": 4, "base_traffic": 0.4},
    {"zone_id": "D2", "name": "Queue Area",   "area_sqm": 40,  "capacity": 120, "location_x": 2, "location_y": 4, "base_traffic": 0.8},
    {"zone_id": "D3", "name": "Info Desk",    "area_sqm": 30,  "capacity": 80,  "location_x": 3, "location_y": 4, "base_traffic": 0.5},
    {"zone_id": "D4", "name": "Hall B",       "area_sqm": 140, "capacity": 450, "location_x": 4, "location_y": 4, "base_traffic": 0.45},
    {"zone_id": "D5", "name": "Exit South",   "area_sqm": 35,  "capacity": 100, "location_x": 5, "location_y": 4, "base_traffic": 0.55},
]

# Internal state for continuity between readings
_state: Dict[str, int] = {}
_spike_zones: set = set()


def _time_multiplier() -> float:
    """Rush hour effect: peak at 9am, 12pm, 5pm."""
    h = datetime.now().hour
    if h in (8, 9, 17, 18):
        return 1.4
    if h in (12, 13):
        return 1.2
    if h in (0, 1, 2, 3, 4, 5):
        return 0.1
    return 1.0


def set_spike(zone_ids: List[str]) -> None:
    global _spike_zones
    _spike_zones = set(zone_ids)


def clear_spikes() -> None:
    global _spike_zones
    _spike_zones = set()


def generate_readings() -> List[Dict]:
    """Generate one round of crowd readings for all zones."""
    global _state
    tm = _time_multiplier()
    readings = []

    for zone in ZONES:
        zid = zone["zone_id"]
        cap = zone["capacity"]
        base = zone["base_traffic"]

        prev = _state.get(zid, int(cap * base * 0.5))
        noise = int(rng.normal(0, cap * 0.05))
        drift = int((cap * base * tm - prev) * 0.15)
        spike = int(cap * rng.uniform(0.4, 0.7)) if zid in _spike_zones else 0

        count = int(np.clip(prev + drift + noise + spike, 0, cap))
        _state[zid] = count

        readings.append({
            "zone_id":      zid,
            "name":         zone["name"],
            "area_sqm":     zone["area_sqm"],
            "capacity":     cap,
            "people_count": count,
            "location_x":   zone["location_x"],
            "location_y":   zone["location_y"],
        })

    return readings


def generate_historical(n_rounds: int = 100) -> List[Dict]:
    """Generate synthetic historical data for ML training."""
    history = []
    for _ in range(n_rounds):
        for zone in ZONES:
            count = int(rng.uniform(0, zone["capacity"]))
            density = round(count / zone["area_sqm"], 3)
            history.append({"zone_id": zone["zone_id"], "density": density})
    return history


def get_zone_meta() -> List[Dict]:
    return [{k: v for k, v in z.items() if k != "base_traffic"} for z in ZONES]
