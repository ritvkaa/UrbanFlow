"""
UrbanFlow – Smart Crowd Monitoring System
Run with: uvicorn main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.models.database import init_db, SessionLocal
from backend.routers.api import router as api_router
from backend.ml.analyzer import get_detector
from backend.services.simulator import generate_historical

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("urbanflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Initializing database …")
    init_db()

    logger.info("Training anomaly detection model on synthetic history …")
    history = generate_historical(n_rounds=80)
    densities = [h["density"] for h in history]
    get_detector().train(densities)
    logger.info("ML model ready.")

    yield   # ← app runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("UrbanFlow shutting down.")


app = FastAPI(
    title="UrbanFlow – Smart Crowd Monitoring",
    description="AI-powered pedestrian movement analysis and congestion detection.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# API routes
app.include_router(api_router)


# ── Frontend route ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok", "service": "UrbanFlow v1.0"}
