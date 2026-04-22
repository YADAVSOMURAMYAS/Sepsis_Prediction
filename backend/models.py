"""SQLAlchemy ORM models."""
import json
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id            = Column(String, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    city          = Column(String, nullable=False)
    address       = Column(String, nullable=False)
    admin_email   = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    accent_color  = Column(String, default="#06b6d4")
    _units        = Column("units", Text, default="[]")   # stored as JSON
    beds_total    = Column(Integer, default=100)
    established   = Column(String, default="")
    created_at    = Column(DateTime, default=datetime.utcnow)

    patients      = relationship("Patient", back_populates="hospital", cascade="all, delete")

    @property
    def units(self):
        return json.loads(self._units)

    @units.setter
    def units(self, value):
        self._units = json.dumps(value)


class Patient(Base):
    __tablename__ = "patients"

    id            = Column(String, primary_key=True, index=True)
    hospital_id   = Column(String, ForeignKey("hospitals.id"), nullable=False)
    name          = Column(String, nullable=False)
    age           = Column(Integer, nullable=False)
    gender        = Column(String(1), default="M")      # 'M' | 'F'
    unit          = Column(String, default="MICU")
    diagnosis     = Column(String, default="Unknown")
    admission_hour= Column(Float, default=0.0)
    icu_hour      = Column(Float, default=0.0)

    # Current vitals
    hr      = Column(Float, default=80.0)
    sbp     = Column(Float, default=120.0)
    dbp     = Column(Float, default=75.0)
    map     = Column(Float, default=90.0)
    temp    = Column(Float, default=37.0)
    spo2    = Column(Float, default=98.0)
    rr      = Column(Float, default=16.0)
    glucose = Column(Float, default=100.0)

    # Risk scores
    sepsis_prob     = Column(Float, default=0.0)
    priority_score  = Column(Float, default=0.0)
    risk            = Column(String, default="Low")
    _alerts         = Column("alerts", Text, default="[]")

    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="patients")
    history  = relationship("VitalHistory", back_populates="patient",
                            order_by="VitalHistory.hour", cascade="all, delete")

    @property
    def alerts(self):
        return json.loads(self._alerts)

    @alerts.setter
    def alerts(self, value):
        self._alerts = json.dumps(value)


class VitalHistory(Base):
    __tablename__ = "vital_history"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    hour       = Column(Float, nullable=False)
    hr         = Column(Float)
    sbp        = Column(Float)
    map        = Column(Float)
    temp       = Column(Float)
    spo2       = Column(Float)
    rr         = Column(Float)
    prob       = Column(Float)

    patient = relationship("Patient", back_populates="history")
