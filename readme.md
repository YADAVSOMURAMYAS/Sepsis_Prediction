# 🏥 SepsisAI — AI-Powered Early Sepsis Prediction Platform

> **Predict Sepsis 6 Hours Before It Strikes**
>
> A full-stack clinical intelligence platform powered by XGBoost, trained on **40,336 ICU patients** from the PhysioNet Challenge 2019, deployed as a multi-hospital SaaS.

---

## 🎥 Video Demonstration

> 📹 **[Watch Full Demo on YouTube](#)** ← *(replace with your YouTube link)*

---

## 🌐 Live Deployment

| Service  | URL |
|----------|-----|
| **Frontend** | [https://sepsis-prediction.vercel.app/](https://sepsis-prediction.vercel.app/) |
| **Backend API** | [https://sepsisai-backend-1018720951308.us-central1.run.app/docs](https://sepsisai-backend-1018720951308.us-central1.run.app/docs) |

### 🔐 Demo Credentials (pre-seeded hospitals)

| Hospital | Email | Password |
|----------|-------|----------|
| City General Hospital | admin@citygeneral.com | SepsisAI2024 |
| St. Mary's Medical Center | admin@stmarys.com | SepsisAI2024 |
| Pacific Coast Hospital | admin@pacificcoast.com | SepsisAI2024 |
| Northside Health System | admin@northside.com | SepsisAI2024 |
| Mountain View Hospital | admin@mountainview.com | SepsisAI2024 |

---

## 🎯 Project Aim

Sepsis kills **1 in 3 hospital patients** and every hour of delayed treatment raises mortality by **7.6%**. Traditional clinical workflows detect it only after deterioration is obvious.

**SepsisAI solves this** by:
1. Running an XGBoost model trained on time-series ICU data to predict sepsis **6 hours before onset**
2. Ranking every active ICU patient by a composite **priority score** — so clinicians focus on the most critical patients first
3. Providing a real-time, multi-hospital dashboard with vitals, trends, and automated alerts

---

## 🗂️ Project Structure

```
ML_Lab_Project/
│
├── Dockerfile                    # Multi-stage Docker build for Cloud Run
├── .dockerignore
├── .env.cloudrun                 # Cloud Run environment variables
├── .env.cloudrun.yaml            # Cloud Run YAML deployment config
│
├── Sepsis-Prediction/            # 🧠 ML PIPELINE (offline training)
│   ├── xgboost_model.pkl         # Trained model artifact (624 KB)
│   ├── requirements.txt          # ML-specific Python dependencies
│   └── src/
│       ├── phase1_preprocessing.py   # Data ingestion & cleaning
│       ├── phase2_features.py        # Feature engineering
│       ├── phase3_train.py           # XGBoost training & evaluation
│       ├── phase4_severity.py        # Severity scoring & patient ranking
│       ├── phase5_simulate.py        # ICU patient deterioration simulation
│       └── dashboard.py              # Offline analytics dashboard
│
├── backend/                      # 🔧 FASTAPI BACKEND (production API)
│   ├── main.py                   # App entry point, CORS, router mount
│   ├── database.py               # SQLAlchemy engine (SQLite dev / PostgreSQL prod)
│   ├── models.py                 # ORM models: Hospital, Patient, VitalHistory
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── auth.py                   # JWT creation/verification, bcrypt hashing
│   ├── ml_model.py               # XGBoost loader + hybrid scoring engine
│   ├── seed.py                   # Idempotent DB seeder (5 hospitals, ~156 patients)
│   ├── requirements.txt          # Backend Python dependencies
│   ├── sepsisai.db               # Local SQLite database (dev only)
│   └── routers/
│       ├── auth_router.py        # POST /auth/register, /auth/login, GET /auth/me
│       └── patients_router.py    # GET/POST /patients, discharge, vitals history
│
├── frontend/                     # ⚛️ REACT FRONTEND (Vercel)
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   ├── vercel.json               # SPA routing config for Vercel
│   ├── .env.production           # VITE_API_URL for production build
│   └── src/
│       ├── main.tsx              # React entry point
│       ├── App.tsx               # Routes + context providers
│       ├── index.css             # Global design system (CSS variables, utilities)
│       ├── api/
│       │   ├── client.ts         # Base fetch wrapper (JWT injection)
│       │   ├── auth.ts           # Login, register, /me API calls
│       │   └── patients.ts       # Patient CRUD, discharge, history API calls
│       ├── context/
│       │   ├── AuthContext.tsx   # Hospital auth state + localStorage persistence
│       │   ├── PatientContext.tsx# Global patient list state
│       │   └── ThemeContext.tsx  # Light/dark mode toggle
│       ├── components/
│       │   ├── Navbar.tsx        # Top nav with hospital branding & theme toggle
│       │   ├── ParticleBackground.tsx # Animated canvas particle system
│       │   ├── KpiCard.tsx       # Reusable KPI metric card
│       │   ├── AlertBanner.tsx   # Dismissable clinical alert notification
│       │   ├── AddPatientModal.tsx   # Vital-input form → API patient creation
│       │   └── ProtectedRoute.tsx    # Auth guard for dashboard routes
│       └── pages/
│           ├── LandingPage.tsx   # Hero, features, model metrics, CTA
│           ├── Dashboard.tsx     # ICU overview: patient table, vitals, charts
│           ├── PatientsPage.tsx  # Detailed patient management & editing
│           └── auth/
│               └── LoginPage.tsx # Hospital login / register form
│
└── output/                       # ML pipeline output artifacts (charts, CSVs)
```

---

## 🧠 How the Model Was Developed

### Dataset — PhysioNet/CinC Challenge 2019

- **Source:** PhysioNet Computing in Cardiology Challenge 2019
- **Size:** 40,336 ICU patients (~1.55 million hourly rows)
- **Format:** Two sets of `.psv` files (`trainingdataA`, `trainingdataB`)
- **Label:** Binary `SepsisLabel` per row (1 = sepsis onset hour)
- **Class Imbalance:** ~55:1 (non-sepsis : sepsis rows)

---

### Phase 1 — Data Preprocessing (`phase1_preprocessing.py`)

**Goal:** Convert 40K raw `.psv` patient files into clean train/test CSVs without loading everything into RAM.

| Step | Description |
|------|-------------|
| **1. Stream** | Row-by-row `csv.writer` — streams all `.psv` files to `raw_combined.csv`. No `pd.concat`. |
| **2. EDA** | Single-pass chunked scan for missing rates, class distribution, hospital-wise sepsis rates |
| **3. Split** | Patient-level stratified 80/20 split (no row-level split — prevents patient data leakage) |
| **4. Impute** | Two-pass chunked: compute train means → forward-fill per patient → fill remaining with mean |
| **5. Scale** | `StandardScaler` with `partial_fit` on train chunks → transform both train and test |
| **6. Early Labels** | Shift `SepsisLabel` backward by **6 hours** → `EarlyLabel`. This teaches the model to fire before onset. |
| **7. Sanity** | Assert zero NaNs, no patient overlap between train/test, EarlyLabel present |

**Outputs:** `train.csv`, `test.csv`, `scaler.pkl`, `imputation_means.pkl`, `feature_cols.pkl`

---

### Phase 2 — Feature Engineering (`phase2_features.py`)

**Goal:** Enrich each patient's time-series with temporal context features.

Per vital signal (`HR`, `O2Sat`, `Temp`, `SBP`, `DBP`, `MAP`, `Resp`, `Glucose`):

| Feature Type | Windows | Description |
|---|---|---|
| Rolling Mean | 3h, 6h | Smoothed vital trend |
| Rolling Std | 3h, 6h | Vital variability indicator |
| Delta | 1h, 2h | Rate of change (deterioration signal) |

**Clinical Flags (binary 0/1):**

| Flag | Threshold | Clinical Meaning |
|---|---|---|
| `flag_MAP_low` | MAP < 65 | Hypoperfusion |
| `flag_HR_high` | HR > 100 | Tachycardia |
| `flag_RR_high` | RR > 22 | Tachypnea |
| `flag_SBP_low` | SBP < 90 | Hypotension |
| `flag_O2_low` | SpO₂ < 94 | Hypoxemia |
| `flag_hemo_instability` | MAP<65 AND HR>100 | Combined hemodynamic shock |
| `shock_index` | HR / SBP | Composite perfusion score |

**Total features after engineering:** **68 features**

---

### Phase 3 — XGBoost Training (`phase3_train.py`)

**Architecture:**

```python
params = {
    "objective":         "binary:logistic",
    "eval_metric":       ["auc", "logloss"],
    "scale_pos_weight":  55,          # counteracts 55:1 class imbalance
    "max_depth":         5,
    "learning_rate":     0.05,
    "subsample":         0.7,
    "colsample_bytree":  0.7,
    "min_child_weight":  10,
    "gamma":             2,
    "reg_alpha":         0.5,
    "reg_lambda":        2.0,
    "tree_method":       "hist",      # memory-efficient histogram method
}
```

- **Max rounds:** 500 with **early stopping** (patience = 20 on test AUC)
- **Threshold selection:** Automated sweep across 0.10–0.90; selects best balanced threshold where recall ≥ 70%
- **Memory safe:** Loads data via `csv.reader` in 50K-row batches into `xgb.DMatrix`

**Evaluation Results:**

| Metric | Row-Level | Patient-Level |
|--------|-----------|---------------|
| ROC-AUC | 0.755 | **0.800** |
| Recall | — | **69.5%** |
| Precision | — | 19.6% |
| False Alarms per Catch | — | **4.1×** |

---

### Phase 4 — Severity Scoring (`phase4_severity.py`)

Converts raw XGBoost probabilities into a clinically actionable **Priority Score**:

```
Priority Score = 0.6 × rolling_mean_prob(3h)
              + 0.2 × HR_risk   (flag_HR_high)
              + 0.2 × BP_risk   (flag_MAP_low + 0.5 × flag_SBP_low, clipped to 1)
```

**Risk tiers:**
- 🔴 **High** — Priority Score > 0.60
- 🟡 **Medium** — 0.40–0.60
- 🟢 **Low** — < 0.40

Patients are ranked by this score in the ICU dashboard so clinicians see the most critical patients first.

---

### Phase 5 — Simulation (`phase5_simulate.py`)

Generates realistic patient deterioration trajectories for testing/training workflows without using real patient data.

---

## 🔧 Backend Architecture

**Stack:** FastAPI · SQLAlchemy · SQLite (dev) / PostgreSQL (prod) · JWT Auth · Uvicorn

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | ❌ | Register a new hospital |
| `POST` | `/auth/login` | ❌ | Login, receive JWT token |
| `GET` | `/auth/me` | ✅ | Get current hospital profile |
| `GET` | `/hospitals` | ❌ | List all hospitals (for login dropdown) |
| `GET` | `/patients` | ✅ | List active patients, sorted by priority |
| `POST` | `/patients` | ✅ | Add patient — triggers ML scoring |
| `POST` | `/patients/{id}/discharge` | ✅ | Discharge patient (soft delete) |
| `GET` | `/patients/{id}/history` | ✅ | Get hourly vital history |
| `GET` | `/` | ❌ | Health check + model status |

### ML Inference — Hybrid Scoring (`ml_model.py`)

Because the model was trained on time-series data but production only has a single vital snapshot, raw XGBoost output is compressed into a narrow band (~0.05–0.12). A calibrated hybrid prevents this:

```
final_score = 0.60 × clinical_formula  +  0.40 × xgb_calibrated

clinical_formula = weighted sum of:
  HR deviation (0.25) + SBP (0.20) + SpO₂ (0.20) +
  RR (0.15) + Temp (0.10) + MAP (0.10)

xgb_calibrated = min(1.0, xgb_raw / 0.13)   # rescale to 0-1
```

Falls back to clinical formula only if model file is unavailable.

### Database Models

```
Hospital
  └─ id, name, city, address, admin_email, password_hash
  └─ accent_color, units (JSON), beds_total, established
  └─ → patients (cascade)

Patient
  └─ id, hospital_id, name, age, gender, unit, diagnosis
  └─ hr, sbp, dbp, map, temp, spo2, rr, glucose  (current vitals)
  └─ sepsis_prob, priority_score, risk, alerts (JSON)
  └─ is_active, admission_hour, icu_hour
  └─ → history (cascade)

VitalHistory
  └─ patient_id, hour, hr, sbp, map, temp, spo2, rr, prob
```

### Auth & Security

- **Password hashing:** `sha256_crypt` via `passlib`
- **Tokens:** HS256 JWT, 48-hour expiry via `python-jose`
- **Multi-tenancy:** Every patient is scoped to its `hospital_id` — hospitals cannot see each other's data

---

## ⚛️ Frontend Architecture

**Stack:** React 19 · TypeScript · Vite · Framer Motion · Recharts · Lucide Icons · CSS Modules

### Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `LandingPage` | Hero with animated stethoscope, model metrics, feature cards |
| `/login` | `LoginPage` | Hospital login & registration form |
| `/dashboard` | `Dashboard` | ICU overview: KPI cards, patient priority table, Recharts vitals |
| `/patients` | `PatientsPage` | Full patient management: add, discharge, vitals history charts |

### State Management (Context API)

| Context | Responsibility |
|---------|---------------|
| `AuthContext` | JWT token, hospital profile, login/logout — persisted in `localStorage` |
| `PatientContext` | Active patient list, global refresh |
| `ThemeContext` | Light/dark mode toggle |

### API Layer

- `api/client.ts` — base `apiFetch<T>()` wrapper: injects JWT, handles 4xx/5xx
- `api/auth.ts` — login, register, `/me`
- `api/patients.ts` — list, create, discharge, history

---

## 🐳 Deployment

### Backend — Google Cloud Run

Multi-stage Dockerfile:
1. **Builder stage** — installs gcc, libpq-dev, all Python packages
2. **Runtime stage** — copies only compiled packages + backend source + `xgboost_model.pkl`

```bash
# Build & push
gcloud builds submit --tag gcr.io/PROJECT_ID/sepsisai-backend

# Deploy
gcloud run deploy sepsisai-backend \
  --image gcr.io/PROJECT_ID/sepsisai-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=postgresql://...,ALLOWED_ORIGINS=https://sepsis-prediction.vercel.app
```

**Environment variables:**

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (Cloud SQL) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |
| `PORT` | Set automatically by Cloud Run (8080) |

### Frontend — Vercel

```bash
cd frontend
# .env.production contains:
# VITE_API_URL=https://sepsisai-backend-1018720951308.us-central1.run.app

vercel --prod
```

`vercel.json` rewrites all paths to `index.html` for SPA routing.

---

## 🚀 Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git

### Backend

```bash
cd backend
pip install -r requirements.txt

# Run (auto-creates SQLite DB and seeds 5 hospitals on first start)
uvicorn main:app --reload --port 8000

# Swagger UI available at:
# http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install

# Create .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:5173
```

---

## 📊 Model Performance Summary

| Metric | Value | Notes |
|--------|-------|-------|
| Row-level ROC-AUC | 0.755 | All hourly rows |
| **Patient-level ROC-AUC** | **0.800** | Per-patient max probability |
| Patient Recall | 69.5% | Septic patients caught |
| Patient Precision | 19.6% | True alerts / all alerts |
| False Alarm Rate | 4.1× | False alerts per true catch |
| Training set | 32,268 patients | 80% stratified split |
| Test set | 8,068 patients | 20% held-out |
| Class imbalance | 55:1 | Handled via `scale_pos_weight` |
| Early warning window | **6 hours** | Label shifted backward in training |

---

## 🛠️ Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| ML Training | Python, XGBoost, scikit-learn, pandas, NumPy, joblib |
| Backend API | FastAPI, SQLAlchemy, Uvicorn, Pydantic v2 |
| Auth | JWT (python-jose), passlib (sha256_crypt) |
| Database (Dev) | SQLite |
| Database (Prod) | PostgreSQL via Cloud SQL |
| Containerization | Docker (multi-stage, python:3.11-slim) |
| Backend Hosting | Google Cloud Run |
| Frontend | React 19, TypeScript, Vite |
| Animations | Framer Motion |
| Charts | Recharts |
| Icons | Lucide React |
| Frontend Hosting | Vercel |
| Dataset | PhysioNet/CinC Challenge 2019 |

---

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `Sepsis-Prediction/xgboost_model.pkl` | Trained XGBoost booster (624 KB) |
| `backend/ml_model.py` | Hybrid scoring: XGBoost + clinical formula |
| `backend/seed.py` | Seeds 5 hospitals + ~156 synthetic patients |
| `backend/routers/patients_router.py` | Patient CRUD + ML inference on admission |
| `frontend/src/pages/Dashboard.tsx` | Main ICU dashboard with priority ranking |
| `frontend/src/context/AuthContext.tsx` | Multi-hospital JWT auth state |
| `Dockerfile` | Cloud Run deployment container |

---

## 👨‍💻 Author

**Somu Ram Yadav** — ML Lab Project, 2024

Dataset citation:
> Reyna M, et al. *Early Prediction of Sepsis from Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019.* Critical Care Medicine 48(2):210-217, 2020.
