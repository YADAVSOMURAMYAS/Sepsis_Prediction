# AI-Based Early Sepsis Prediction and ICU Patient Prioritization

An end-to-end machine learning pipeline that predicts sepsis risk in ICU patients
using hourly time-series clinical data (PhysioNet Sepsis Challenge 2019),
and dynamically prioritizes patients by severity score.

---

## Results

| Metric | Value |
|---|---|
| Row-level ROC-AUC | 0.755 |
| Patient-level ROC-AUC | 0.800 |
| Patient Recall | 69.5% |
| Patient Precision | 19.6% |
| False alarms per true catch | 4.1 |

---

## Project Structure

```
sepsis_prediction/
├── data/
│   ├── trainingdataA/        ← 20,336 .psv files (not tracked)
│   └── trainingdataB/        ← 20,000 .psv files (not tracked)
├── src/
│   ├── phase1_preprocessing.py   ← Stream, impute, scale, early labels
│   ├── phase2_features.py        ← 68 engineered features
│   ├── phase3_train.py           ← XGBoost + early stopping + threshold
│   └── phase4_severity.py        ← Severity scoring + patient ranking
├── models/                   ← Saved models (not tracked)
├── output/                   ← Generated CSVs and plots (not tracked)
├── requirements.txt
└── README.md
```

---

## Dataset

PhysioNet Computing in Cardiology Challenge 2019
- 40,336 ICU patients (Set A: 20,336 + Set B: 20,000)
- Hourly clinical measurements, binary SepsisLabel
- Download: https://physionet.org/content/challenge-2019/1.0.0/

---

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/sepsis-prediction.git
cd sepsis-prediction

python -m venv sepsis
sepsis\Scripts\activate          # Windows
# source sepsis/bin/activate     # Mac/Linux

pip install -r requirements.txt
```

Place all `.psv` files into:
- `data/trainingdataA/`
- `data/trainingdataB/`

---

## Run the Pipeline

```bash
python src/phase1_preprocessing.py   # ~25 min — streams 40k files
python src/phase2_features.py        # ~15 min — engineers 68 features
python src/phase3_train.py           # ~10 min — trains XGBoost
python src/phase4_severity.py        # ~5  min — scores and ranks patients
```

---

## How It Works

### Input (per patient per hour)

| Type | Features |
|---|---|
| Vitals (every hour) | HR, O2Sat, SBP, DBP, MAP, Resp |
| Labs (when drawn) | Temp, Glucose, WBC, Creatinine, pH, Lactate, Hgb, Platelets, HCO3, Potassium |
| Admission (once) | Age, Gender, Unit1, Unit2, HospAdmTime |

### Auto-computed features (Phase 2)
- Rolling mean and std over 3h and 6h windows per vital
- 1h and 2h change (delta) per vital
- Clinical flags: `flag_HR_high`, `flag_MAP_low`, `flag_SBP_low`, `flag_RR_high`, `flag_O2_low`
- Shock index (HR / SBP)
- Haemodynamic instability flag

### Output (per patient per hour)
- Sepsis probability (0–1)
- Priority score = `0.6 × prob + 0.2 × HR_risk + 0.2 × BP_risk`
- Risk category: High / Medium / Low
- Alert flag when sustained above threshold
- Ranked patient list — most urgent first

---

## Key Design Decisions

**Memory handling:** All phases use `csv.reader` line-by-line instead of
`pd.read_csv` on large files — keeps RAM below 1 GB on low-memory machines.

**Train/test split:** Split by patient ID before any imputation to prevent
data leakage. Stratified by hospital (A/B) and sepsis label.

**Early label shift:** `SepsisLabel = 1` is shifted N hours backward
(default 6h) so the model learns to fire before clinical onset.

**Threshold:** Phase 3 auto-selects the threshold where recall ≥ 0.70
and precision is maximized. Saved to `output/threshold.pkl` and loaded
by Phase 4 — no manual tuning needed.

---

## Tech Stack

Python 3.10 · XGBoost · scikit-learn · Pandas · NumPy · Matplotlib · Streamlit · Joblib

---

## Citation

Reyna M, et al. Early Prediction of Sepsis from Clinical Data:
The PhysioNet/Computing in Cardiology Challenge 2019.
Critical Care Medicine 48(2):210-217, 2020.
