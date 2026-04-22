"""Auth router — register hospital, login."""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Hospital
from schemas import HospitalRegisterRequest, LoginRequest, TokenResponse, HospitalOut
from auth import hash_password, verify_password, create_token, decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


def get_current_hospital(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Hospital:
    hospital_id = decode_token(credentials.credentials)
    if not hospital_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=401, detail="Hospital not found")
    return h


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_hospital(payload: HospitalRegisterRequest, db: Session = Depends(get_db)):
    if db.query(Hospital).filter(Hospital.id == payload.id).first():
        raise HTTPException(400, "Hospital ID already exists")
    if db.query(Hospital).filter(Hospital.admin_email == payload.admin_email).first():
        raise HTTPException(400, "Email already registered")

    h = Hospital(
        id=payload.id,
        name=payload.name,
        city=payload.city,
        address=payload.address,
        admin_email=payload.admin_email,
        password_hash=hash_password(payload.password),
        accent_color=payload.accent_color or "#06b6d4",
        beds_total=payload.beds_total or 100,
        established=payload.established or "",
    )
    h.units = payload.units or ["MICU", "SICU", "CCU"]
    db.add(h)
    db.commit()
    db.refresh(h)

    token = create_token(h.id)
    return TokenResponse(access_token=token, hospital_id=h.id, hospital_name=h.name)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    h = db.query(Hospital).filter(Hospital.admin_email == payload.admin_email).first()
    if not h or not verify_password(payload.password, h.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(h.id)
    return TokenResponse(access_token=token, hospital_id=h.id, hospital_name=h.name)


@router.get("/me", response_model=HospitalOut)
def get_me(hospital: Hospital = Depends(get_current_hospital)):
    return hospital
