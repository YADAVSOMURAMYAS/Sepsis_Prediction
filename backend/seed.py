"""Seed 5 hospitals + synthetic patients into the database (idempotent)."""
import random
import math
from sqlalchemy.orm import Session
from ml_model import predict_sepsis_prob
from models import Hospital, Patient, VitalHistory
from auth import hash_password

# ── Deterministic seeded RNG ──────────────────────────────
def seeded_rng(seed: int):
    s = seed
    def rng():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7fffffff
        return s / 0x7fffffff
    return rng

def rnd(rng, lo, hi, dec=0):
    v = rng() * (hi - lo) + lo
    return round(v, dec)

def pick(rng, lst):
    return lst[int(rng() * len(lst))]

# ── Name pools ────────────────────────────────────────────
FIRST_M = ["James","Michael","David","Robert","William","John","Thomas","Daniel","Christopher","Andrew","George","Henry","Edward","Charles","Benjamin","Samuel","Joseph","Richard","Mark","Steven"]
FIRST_F = ["Sarah","Emma","Olivia","Sophia","Isabella","Amelia","Charlotte","Emily","Jessica","Lauren","Rachel","Katherine","Michelle","Patricia","Sandra","Dorothy","Helen","Ruth","Marie","Anne"]
LAST    = ["Chen","Patel","Williams","Johnson","Kim","García","Martinez","Anderson","Thompson","White","Davis","Miller","Wilson","Moore","Taylor","Jackson","Harris","Martin","Lee","Walker","Hall","Allen","Young","King","Scott","Green","Baker","Adams","Nelson","Carter"]
DIAGS   = ["Pneumonia","Acute Respiratory Failure","Septic Shock","UTI","Abdominal Sepsis","Meningitis","Post-operative Complications","Cellulitis","Community-Acquired Pneumonia","Bacteremia","Endocarditis","Peritonitis","Cholangitis","Pancreatitis","Necrotizing Fasciitis"]

# ── History builder ───────────────────────────────────────
def build_history(rng, base_prob: float, hours: int):
    snaps = []
    prob = max(0, base_prob - rng() * 0.18)
    hr   = rnd(rng, 65, 130)
    sbp  = rnd(rng, 85, 155)
    map_ = rnd(rng, 58, 110)
    temp = rnd(rng, 36.2, 40.0, 1)
    spo2 = rnd(rng, 89, 100, 1)
    rrv  = rnd(rng, 11, 34)

    for h in range(1, hours + 1):
        hr   = min(160, max(45,  hr   + (rng() - 0.48) * 6))
        sbp  = min(200, max(70,  sbp  + (rng() - 0.47) * 8))
        map_ = min(140, max(50,  map_ + (rng() - 0.47) * 6))
        temp = min(41,  max(35.5,temp + (rng() - 0.48) * 0.25))
        spo2 = min(100, max(85,  spo2 + (rng() - 0.4)  * 1.2))
        rrv  = min(40,  max(8,   rrv  + (rng() - 0.47) * 2))
        prob = min(1,   max(0,   prob + (rng() - 0.42) * 0.07))
        snaps.append({"hour": h, "hr": round(hr), "sbp": round(sbp),
                      "map": round(map_), "temp": round(temp, 1),
                      "spo2": round(spo2, 1), "rr": round(rrv), "prob": round(prob, 3)})
    return snaps

# ── Patient builder ───────────────────────────────────────
def build_patient(rng, hospital_id: str, idx: int, units):
    is_male = rng() > 0.44
    first   = pick(rng, FIRST_M if is_male else FIRST_F)
    last    = pick(rng, LAST)
    age     = int(rng() * 55) + 28
    sev     = rng()
    hist_hours = int(rng() * 15) + 6   # 6-20

    hr    = rnd(rng, 58 + sev*50, 85 + sev*60)
    sbp   = rnd(rng, 160 - sev*80, 175 - sev*60)
    dbp   = rnd(rng, 90 - sev*40, 105 - sev*30)
    map_  = rnd(rng, 110 - sev*55, 120 - sev*40)
    temp  = rnd(rng, 36.5 + sev*2.5, 37.0 + sev*3.2, 1)
    spo2  = rnd(rng, 100 - sev*14, 100 - sev*4, 1)
    rrv   = rnd(rng, 12 + sev*14, 16 + sev*22)
    gluc  = rnd(rng, 80 + sev*100, 110 + sev*200)

    # ── XGBoost model prediction ──────────────────────────
    gender_str = "M" if is_male else "F"
    unit_str   = pick(rng, units)   # pick unit early so model can use it
    sp = predict_sepsis_prob(
        hr=hr, spo2=spo2, temp=temp, sbp=sbp,
        map_=map_, dbp=dbp, rr=rrv, glucose=gluc,
        age=age, gender=gender_str, unit=unit_str,
    )
    hr_r = 1.0 if hr > 100 else 0.0
    bp_r = min(1.0, (1.0 if map_ < 65 else 0.0) + (0.5 if sbp < 90 else 0.0))
    prio = round(min(1, 0.6*sp + 0.2*hr_r + 0.2*bp_r), 3)
    risk = "High" if prio > 0.78 else "Medium" if prio > 0.48 else "Low"

    alerts = []
    if sp > 0.85:   alerts.append("Sepsis probability > 85%")
    if sbp < 90:    alerts.append(f"Low SBP: {sbp} mmHg")
    if map_ < 65:   alerts.append(f"Low MAP: {map_} mmHg")
    if spo2 < 92:   alerts.append(f"Critical SpO₂: {spo2}%")
    if hr > 130:    alerts.append(f"Tachycardia: {hr} bpm")
    if temp > 39.5: alerts.append(f"Fever: {temp}°C")
    if rrv > 30:    alerts.append(f"Tachypnea: RR {int(rrv)}")

    pat_id = f"{hospital_id[:3].upper()}-{idx+100:03d}"
    history_snaps = build_history(rng, sp, hist_hours)

    return dict(
        id=pat_id, hospital_id=hospital_id, name=f"{first} {last}",
        age=age, gender=gender_str,
        unit=unit_str, diagnosis=pick(rng, DIAGS),
        admission_hour=rnd(rng, 2, 48), icu_hour=rnd(rng, 1, hist_hours),
        hr=hr, sbp=sbp, dbp=dbp, map=map_, temp=temp,
        spo2=spo2, rr=rrv, glucose=gluc,
        sepsis_prob=sp, priority_score=prio, risk=risk,
        alerts=alerts, is_active=True,
        history_snaps=history_snaps,
    )

# ── Hospital definitions ──────────────────────────────────
HOSPITAL_DEFS = [
    dict(id="CGH", name="City General Hospital",      city="New York, NY",
         address="550 First Avenue, Manhattan, NY 10016",
         admin_email="admin@citygeneral.com",  accent_color="#06b6d4",
         units=["MICU","SICU","CCU","NICU","TICU"],  beds_total=450, established="1902", count=38),
    dict(id="SMM", name="St. Mary's Medical Center",  city="Chicago, IL",
         address="2233 West Division Street, Chicago, IL 60622",
         admin_email="admin@stmarys.com",      accent_color="#8b5cf6",
         units=["MICU","CSICU","Neuro-ICU","PICU"],   beds_total=320, established="1918", count=30),
    dict(id="PCH", name="Pacific Coast Hospital",     city="Los Angeles, CA",
         address="1300 N Vermont Ave, Los Angeles, CA 90027",
         admin_email="admin@pacificcoast.com", accent_color="#10b981",
         units=["MICU","SICU","BICU","CCU"],          beds_total=275, established="1955", count=25),
    dict(id="NHS", name="Northside Health System",    city="Atlanta, GA",
         address="1000 Johnson Ferry Rd NE, Atlanta, GA 30342",
         admin_email="admin@northside.com",    accent_color="#f59e0b",
         units=["MICU","CICU","SICU","PICU","NICU"],  beds_total=390, established="1971", count=35),
    dict(id="MVH", name="Mountain View Hospital",     city="Denver, CO",
         address="4700 E Hale Pkwy, Denver, CO 80220",
         admin_email="admin@mountainview.com", accent_color="#ef4444",
         units=["MICU","SICU","CCU","Trauma-ICU"],    beds_total=210, established="1988", count=28),
]

DEFAULT_PASSWORD = "SepsisAI2024"


def run_seed(db: Session):
    """Idempotent seed — only runs if no hospitals exist."""
    if db.query(Hospital).count() > 0:
        return   # already seeded

    print("[SEED] Seeding database with hospitals and patients...")

    for defn in HOSPITAL_DEFS:
        count  = defn.pop("count")
        units  = defn["units"]
        h_id   = defn["id"]

        hosp = Hospital(
            password_hash=hash_password(DEFAULT_PASSWORD),
            **{k: v for k, v in defn.items() if k not in ("units",)},
        )
        hosp.units = units
        db.add(hosp)
        db.flush()

        rng = seeded_rng((ord(h_id[0]) + 1) * 7919)
        for i in range(count):
            pd = build_patient(rng, h_id, i, units)
            snaps = pd.pop("history_snaps")

            p = Patient(alerts=pd.pop("alerts"), **pd)
            db.add(p)
            db.flush()

            for s in snaps:
                db.add(VitalHistory(patient_id=p.id, **s))

    db.commit()
    print("[SEED] Complete.")
