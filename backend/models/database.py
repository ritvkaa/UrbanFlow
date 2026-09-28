from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

import os

if os.getenv("VERCEL"):
    DATABASE_URL = "sqlite:////tmp/urbanflow.db"
else:
    DATABASE_URL = "sqlite:///./urbanflow.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, unique=True, index=True)
    name = Column(String)
    area_sqm = Column(Float)
    capacity = Column(Integer)
    location_x = Column(Float)
    location_y = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class CrowdReading(Base):
    __tablename__ = "crowd_readings"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, index=True)
    people_count = Column(Integer)
    density = Column(Float)
    status = Column(String)   # LOW / MEDIUM / HIGH / CRITICAL
    congested = Column(Boolean, default=False)
    anomaly = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, index=True)
    alert_type = Column(String)   # CONGESTION / ANOMALY / CLEARED
    severity = Column(String)     # INFO / WARNING / CRITICAL
    message = Column(String)
    suggestion = Column(String)
    acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class RouteRecommendation(Base):
    __tablename__ = "route_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    from_zone = Column(String)
    to_zone = Column(String)
    route_name = Column(String)
    via_zones = Column(String)   # comma-separated
    status = Column(String)      # CLEAR / BUSY / BLOCKED
    timestamp = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
