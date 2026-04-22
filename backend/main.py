"""FastAPI application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal, Base
from models import Hospital, Patient, VitalHistory   # ensure tables registered
from routers.auth_router import router as auth_router
from routers.patients_router import router as patients_router
from seed import run_seed
import ml_model  # noqa: F401 — triggers XGBoost model load at startup

# ── Create all tables ─────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Seed on startup ───────────────────────────────────────
with SessionLocal() as db:
    run_seed(db)

# ── Log active database ───────────────────────────────────
from database import DATABASE_URL as _db_url
_safe_url = _db_url.split("@")[-1] if "@" in _db_url else _db_url
print(f"[DB] Connected to: {_safe_url}")


# ── App ───────────────────────────────────────────────────
app = FastAPI(
    title="SepsisAI API",
    description="Clinical Intelligence Platform — multi-hospital ICU management",
    version="1.0.0",
)

# ALLOWED_ORIGINS: comma-separated, e.g. "https://sepsis.vercel.app,http://localhost:5173"
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
)
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(patients_router)


@app.get("/", tags=["health"])
def health():
    model_loaded = ml_model._model is not None
    return {
        "status": "ok",
        "service": "SepsisAI API v1.0",
        "xgboost_model": "loaded" if model_loaded else "not loaded (formula fallback active)",
    }


@app.get("/hospitals", tags=["hospitals"])
def list_hospitals(db=None):
    """Public endpoint — list all hospital names for the login dropdown."""
    from database import SessionLocal
    from schemas import HospitalOut
    with SessionLocal() as s:
        return [{"id": h.id, "name": h.name, "city": h.city,
                 "accent_color": h.accent_color, "admin_email": h.admin_email}
                for h in s.query(Hospital).all()]

