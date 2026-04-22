"""Pydantic schemas for request/response validation."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, EmailStr


# ── Auth ────────────────────────────────────────────────────
class HospitalRegisterRequest(BaseModel):
    id:           str
    name:         str
    city:         str
    address:      str
    admin_email:  str
    password:     str
    accent_color: Optional[str] = "#06b6d4"
    units:        Optional[List[str]] = ["MICU", "SICU", "CCU"]
    beds_total:   Optional[int] = 100
    established:  Optional[str] = ""


class LoginRequest(BaseModel):
    admin_email: str
    password:    str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    hospital_id:  str
    hospital_name: str


# ── Hospital ─────────────────────────────────────────────────
class HospitalOut(BaseModel):
    id:           str
    name:         str
    city:         str
    address:      str
    admin_email:  str
    accent_color: str
    units:        List[str]
    beds_total:   int
    established:  str

    model_config = {"from_attributes": True}


# ── Vital History ─────────────────────────────────────────────
class VitalHistoryOut(BaseModel):
    hour: float
    hr:   float
    sbp:  float
    map:  float
    temp: float
    spo2: float
    rr:   float
    prob: float

    model_config = {"from_attributes": True}


# ── Patient ───────────────────────────────────────────────────
class PatientOut(BaseModel):
    id:             str
    hospital_id:    str
    name:           str
    age:            int
    gender:         str
    unit:           str
    diagnosis:      str
    admission_hour: float
    icu_hour:       float
    hr:     float; sbp: float; dbp: float; map: float
    temp:   float; spo2: float; rr: float; glucose: float
    sepsis_prob:    float
    priority_score: float
    risk:           str
    alerts:         List[str]
    is_active:      bool
    history:        List[VitalHistoryOut] = []

    model_config = {"from_attributes": True}


class PatientCreateRequest(BaseModel):
    name:      str
    age:       int
    gender:    str = "M"
    unit:      str = "MICU"
    diagnosis: str = "Pending"
    hr:        float = 80.0
    sbp:       float = 120.0
    dbp:       float = 75.0
    map:       float = 90.0
    temp:      float = 37.0
    spo2:      float = 98.0
    rr:        float = 16.0
    glucose:   float = 100.0
