"""Patients router — list, create, discharge, history."""
import math, json
from ml_model import predict_sepsis_prob
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Hospital, Patient, VitalHistory
from schemas import PatientOut, PatientCreateRequest, VitalHistoryOut
from routers.auth_router import get_current_hospital
from typing import List

router = APIRouter(prefix="/patients", tags=["patients"])


def _compute_scores(p: PatientCreateRequest):
    """Compute sepsis probability via XGBoost model, then derive priority/risk/alerts."""
    hr, sbp, spo2, rr, temp, map_, dbp = (
        p.hr, p.sbp, p.spo2, p.rr, p.temp, p.map, p.dbp
    )

    # ── XGBoost prediction (falls back to clinical formula if model unavailable) ──
    prob = predict_sepsis_prob(
        hr=hr, spo2=spo2, temp=temp, sbp=sbp,
        map_=map_, dbp=dbp, rr=rr, glucose=p.glucose,
        age=p.age, gender=p.gender, unit=p.unit,
    )

    # ── Priority score (same formula as training phase 4) ──
    hr_r = 1.0 if hr > 100 else 0.0
    bp_r = min(1.0, (1.0 if map_ < 65 else 0.0) + (0.5 if sbp < 90 else 0.0))
    prio = min(1.0, 0.6 * prob + 0.2 * hr_r + 0.2 * bp_r)
    risk = "High" if prio > 0.78 else "Medium" if prio > 0.48 else "Low"

    # ── Clinical alerts ──
    alerts = []
    if prob > 0.85:  alerts.append("Sepsis probability > 85%")
    if sbp  < 90:   alerts.append(f"Low SBP: {sbp} mmHg")
    if map_ < 65:   alerts.append(f"Low MAP: {map_} mmHg")
    if spo2 < 92:   alerts.append(f"Critical SpO₂: {spo2}%")
    if hr   > 130:  alerts.append(f"Tachycardia: {hr} bpm")
    if temp > 39.5: alerts.append(f"Fever: {temp}°C")
    if rr   > 30:   alerts.append(f"Tachypnea: RR {int(rr)}")

    return round(prob, 3), round(prio, 3), risk, alerts


@router.get("", response_model=List[PatientOut])
def list_patients(
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    patients = (
        db.query(Patient)
        .filter(Patient.hospital_id == hospital.id, Patient.is_active == True)
        .order_by(Patient.priority_score.desc())
        .all()
    )
    return patients


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    payload: PatientCreateRequest,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    sp, prio, risk, alerts = _compute_scores(payload)

    # Generate a unique ID for this hospital
    existing = db.query(Patient).filter(Patient.hospital_id == hospital.id).count()
    pat_id = f"{hospital.id[:3].upper()}-{existing + 100:03d}"
    # Ensure uniqueness
    while db.query(Patient).filter(Patient.id == pat_id).first():
        existing += 1
        pat_id = f"{hospital.id[:3].upper()}-{existing + 100:03d}"

    p = Patient(
        id=pat_id,
        hospital_id=hospital.id,
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        unit=payload.unit,
        diagnosis=payload.diagnosis,
        admission_hour=0.0,
        icu_hour=0.0,
        hr=payload.hr, sbp=payload.sbp, dbp=payload.dbp, map=payload.map,
        temp=payload.temp, spo2=payload.spo2, rr=payload.rr, glucose=payload.glucose,
        sepsis_prob=sp, priority_score=prio, risk=risk,
        is_active=True,
    )
    p.alerts = alerts
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.post("/{patient_id}/discharge", response_model=PatientOut)
def discharge_patient(
    patient_id: str,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    p = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.hospital_id == hospital.id
    ).first()
    if not p:
        raise HTTPException(404, "Patient not found")
    if not p.is_active:
        raise HTTPException(400, "Patient already discharged")

    p.is_active = False
    db.commit()
    db.refresh(p)
    return p


@router.get("/{patient_id}/history", response_model=List[VitalHistoryOut])
def get_history(
    patient_id: str,
    hospital: Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db),
):
    p = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.hospital_id == hospital.id
    ).first()
    if not p:
        raise HTTPException(404, "Patient not found")
    return p.history
