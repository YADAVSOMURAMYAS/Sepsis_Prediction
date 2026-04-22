"""
Phase 5 — Real-Time ICU Simulation
AI-Based Early Sepsis Prediction System

Simulates a live ICU monitor by replaying hourly patient data.
At each hour step:
  - New vitals arrive for each active patient
  - Features are engineered on the fly (rolling, delta, flags)
  - XGBoost predicts sepsis probability for each patient
  - Priority score is computed
  - All patients re-ranked — most urgent at top
  - Alerts fired for sustained high-risk patients

Input  : output/test_features.csv  (replay source)
         models/xgboost_model.pkl
         output/feature_cols_engineered.pkl
         output/scaler.pkl
         output/imputation_means.pkl

Output : output/simulation_log.csv  — full timestep-by-timestep log
         output/simulation_alerts.csv — only alert events
         output/simulation_summary.png
"""

import os, gc, csv, joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xgboost as xgb
from collections import defaultdict

# ── CONFIG ────────────────────────────────────────────────
OUTPUT_DIR     = "./output"
MODELS_DIR     = "./models"
TEST_IN        = os.path.join(OUTPUT_DIR, "test_features.csv")

PROB_THRESHOLD = 0.45     # row-level probability threshold
PRIORITY_THRESHOLD = 0.65 # patient-level priority alert threshold
CONSEC_HOURS   = 1        # hours above threshold to fire alert
ROLLING_WINDOW = 3
W_PROB, W_HR, W_BP = 0.6, 0.2, 0.2

# Simulation settings
MAX_PATIENTS   = 200      # patients to simulate simultaneously (memory safe)
                          # increase if RAM allows; full test set = 8068 patients
PRINT_INTERVAL = 5        # print ICU snapshot every N hours

# ── Load artifacts ────────────────────────────────────────
all_feature_cols = joblib.load(
    os.path.join(OUTPUT_DIR, "feature_cols_engineered.pkl"))
model            = joblib.load(os.path.join(MODELS_DIR, "xgboost_model.pkl"))
imputation_means = joblib.load(
    os.path.join(OUTPUT_DIR, "imputation_means.pkl"))

print(f"Features        : {len(all_feature_cols)}")
print(f"Prob threshold  : {PROB_THRESHOLD}")
print(f"Alert threshold : {PRIORITY_THRESHOLD}")
print(f"Simulating      : {MAX_PATIENTS} patients")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Load test data into a patient dictionary
#           patient_data[pid] = list of hourly row dicts (sorted by ICULOS)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 1 — Loading patient data for simulation")
print("=" * 60)

patient_data    = defaultdict(list)   # pid → [row_dict, ...]
patient_sepsis  = {}                  # pid → true sepsis label (0/1)
patient_order   = []                  # insertion order

with open(TEST_IN, "r", encoding="utf-8") as f:
    reader  = csv.reader(f)
    header  = next(reader)
    col_idx = {c: i for i, c in enumerate(header)}

    for line in reader:
        rd  = dict(zip(header, line))
        pid = rd.get("patient_id")

        if pid not in patient_data:
            if len(patient_data) >= MAX_PATIENTS:
                continue   # skip once we have enough patients
            patient_order.append(pid)
            patient_sepsis[pid] = 0

        patient_data[pid].append(rd)

        # Track if this patient ever develops sepsis
        try:
            if int(float(rd.get("SepsisLabel", 0))) == 1:
                patient_sepsis[pid] = 1
        except:
            pass

# Keep only MAX_PATIENTS
patient_data = {pid: patient_data[pid] for pid in patient_order}

n_patients = len(patient_data)
n_septic   = sum(patient_sepsis.values())
max_hours  = max(len(v) for v in patient_data.values())

print(f"  Patients loaded  : {n_patients:,}")
print(f"  Septic patients  : {n_septic:,} ({n_septic/n_patients*100:.1f}%)")
print(f"  Max ICU hours    : {max_hours}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Feature engineering for a single new row
#           Uses patient's history buffer to compute rolling/delta features
# ─────────────────────────────────────────────────────────────────────────────

VITAL_COLS = [c for c in all_feature_cols
              if c not in ("Gender","Unit1","Unit2","HospAdmTime","Age")
              and "_mean" not in c and "_std" not in c
              and "_delta" not in c and "flag_" not in c
              and c != "shock_index"]

def engineer_single_row(history_rows):
    """
    Takes the patient's full history up to and including the current hour.
    Returns a feature vector (numpy array) matching all_feature_cols.
    """
    df = pd.DataFrame(history_rows)

    # Numeric conversion
    for col in VITAL_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Impute with training means
    for col in VITAL_COLS:
        if col in df.columns:
            df[col] = df[col].ffill().fillna(
                imputation_means.get(col, 0))

    # Rolling features
    for col in VITAL_COLS:
        if col not in df.columns:
            continue
        s = df[col]
        for w in [3, 6]:
            df[f"{col}_mean{w}"] = s.rolling(w, min_periods=1).mean()
            df[f"{col}_std{w}"]  = s.rolling(w, min_periods=1).std().fillna(0)
        df[f"{col}_delta1"] = s.diff(1).fillna(0)
        df[f"{col}_delta2"] = s.diff(2).fillna(0)

    # Clinical flags (on raw unscaled values — before any scaler)
    if "MAP"   in df.columns:
        df["flag_MAP_low"]  = (df["MAP"]   < 65).astype(int)
    if "HR"    in df.columns:
        df["flag_HR_high"]  = (df["HR"]    > 100).astype(int)
    if "Resp"  in df.columns:
        df["flag_RR_high"]  = (df["Resp"]  > 22).astype(int)
    if "SBP"   in df.columns:
        df["flag_SBP_low"]  = (df["SBP"]   < 90).astype(int)
    if "O2Sat" in df.columns:
        df["flag_O2_low"]   = (df["O2Sat"] < 94).astype(int)
    if "HR" in df.columns and "SBP" in df.columns:
        hr  = df["HR"]
        sbp = df["SBP"].replace(0, np.nan)
        df["shock_index"] = (hr / sbp).fillna(0).clip(upper=5)
    if "MAP" in df.columns and "HR" in df.columns:
        df["flag_hemo_instability"] = (
            (df["MAP"] < 65) & (df["HR"] > 100)).astype(int)

    # Extract last row (current hour)
    last = df.iloc[-1]

    # Build feature vector aligned to all_feature_cols
    feat_vec = []
    for col in all_feature_cols:
        try:
            val = float(last[col]) if col in last.index else 0.0
            feat_vec.append(0.0 if pd.isna(val) else val)
        except:
            feat_vec.append(0.0)

    return np.array(feat_vec, dtype=np.float32)


def compute_priority(prob_history, flag_hr, flag_map, flag_sbp):
    """Compute priority score from smoothed probability + clinical flags."""
    smooth_prob = np.mean(prob_history[-ROLLING_WINDOW:])
    hr_risk     = float(flag_hr)
    bp_risk     = float(np.clip(flag_map + flag_sbp * 0.5, 0, 1))
    score       = W_PROB * smooth_prob + W_HR * hr_risk + W_BP * bp_risk
    return float(np.clip(score, 0, 1))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Run simulation hour by hour
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Running simulation")
print("=" * 60)

# Per-patient state
state = {pid: {
    "prob_history"   : [],    # rolling probability buffer
    "consec_high"    : 0,     # consecutive hours above threshold
    "alert_fired"    : False, # has alert been triggered
    "alert_hour"     : None,  # which hour alert first fired
    "onset_hour"     : None,  # true sepsis onset hour
} for pid in patient_order}

# Identify true onset hour for each patient
for pid, rows in patient_data.items():
    for row in rows:
        try:
            if int(float(row.get("SepsisLabel", 0))) == 1:
                state[pid]["onset_hour"] = int(float(row.get("ICULOS", 0)))
                break
        except:
            pass

# Output log
log_rows    = []   # full per-patient per-hour log
alert_rows  = []   # only alert events

# Stats collectors
tp_early = fp_total = fn_total = 0

print(f"\n  Simulating {max_hours} hours for {n_patients} patients...\n")

for hour in range(1, max_hours + 1):

    hour_predictions = []

    for pid in patient_order:
        rows = patient_data[pid]

        # Skip patients discharged before this hour
        if hour > len(rows):
            continue

        # Current row (0-indexed)
        history = rows[:hour]
        current = history[-1]

        # Engineer features from history
        feat_vec = engineer_single_row(history)

        # Predict
        dmat  = xgb.DMatrix(feat_vec.reshape(1, -1),
                             feature_names=all_feature_cols)
        prob  = float(model.predict(dmat)[0])

        # Update probability history
        state[pid]["prob_history"].append(prob)

        # Clinical flag values (current raw row)
        def get_flag(col):
            try: return int(float(current.get(col, 0)))
            except: return 0

        flag_hr  = get_flag("flag_HR_high")
        flag_map = get_flag("flag_MAP_low")
        flag_sbp = get_flag("flag_SBP_low")

        # Priority score
        priority = compute_priority(
            state[pid]["prob_history"], flag_hr, flag_map, flag_sbp)

        # Consecutive high-risk counter
        if priority >= PRIORITY_THRESHOLD:
            state[pid]["consec_high"] += 1
        else:
            state[pid]["consec_high"] = 0

        # Fire alert if sustained above threshold
        alert_this_hour = False
        if (state[pid]["consec_high"] >= CONSEC_HOURS
                and not state[pid]["alert_fired"]):
            state[pid]["alert_fired"] = True
            state[pid]["alert_hour"]  = hour
            alert_this_hour = True

            # Classify alert
            onset = state[pid]["onset_hour"]
            if patient_sepsis[pid] == 1 and onset is not None:
                lead_time = onset - hour
                tp_early += 1
                alert_rows.append({
                    "patient_id"  : pid,
                    "alert_hour"  : hour,
                    "onset_hour"  : onset,
                    "lead_time_h" : lead_time,
                    "priority"    : round(priority, 4),
                    "prob"        : round(prob, 4),
                    "type"        : "TRUE_POSITIVE",
                })
            elif patient_sepsis[pid] == 0:
                fp_total += 1
                alert_rows.append({
                    "patient_id"  : pid,
                    "alert_hour"  : hour,
                    "onset_hour"  : None,
                    "lead_time_h" : None,
                    "priority"    : round(priority, 4),
                    "prob"        : round(prob, 4),
                    "type"        : "FALSE_POSITIVE",
                })

        # Risk category
        if priority >= 0.60:
            risk_cat = "High"
        elif priority >= 0.40:
            risk_cat = "Medium"
        else:
            risk_cat = "Low"

        hour_predictions.append({
            "hour"         : hour,
            "patient_id"   : pid,
            "sepsis_prob"  : round(prob, 4),
            "priority"     : round(priority, 4),
            "risk_category": risk_cat,
            "alert"        : int(alert_this_hour),
            "true_sepsis"  : patient_sepsis[pid],
            "true_iculos"  : int(float(current.get("ICULOS", hour))),
        })

    # Sort by priority — highest first (the ICU ranking)
    hour_predictions.sort(key=lambda x: x["priority"], reverse=True)
    log_rows.extend(hour_predictions)

    # Print ICU snapshot every PRINT_INTERVAL hours
    if hour % PRINT_INTERVAL == 0:
        active = len(hour_predictions)
        high   = sum(1 for r in hour_predictions if r["risk_category"] == "High")
        alerts = sum(1 for r in hour_predictions if r["alert"] == 1)
        top3   = hour_predictions[:3]

        print(f"  Hour {hour:3d} | Active: {active:4d} | "
              f"High risk: {high:3d} | New alerts: {alerts}")
        for rank, r in enumerate(top3, 1):
            print(f"    #{rank}  {r['patient_id']:15s}  "
                  f"priority={r['priority']:.3f}  "
                  f"prob={r['sepsis_prob']:.3f}  "
                  f"risk={r['risk_category']}")
        print()

# Count missed septic patients
for pid in patient_order:
    if patient_sepsis[pid] == 1 and not state[pid]["alert_fired"]:
        fn_total += 1

print(f"\n  Simulation complete")
print(f"  True positive alerts  : {tp_early:,}")
print(f"  False positive alerts : {fp_total:,}")
print(f"  Missed septic patients: {fn_total:,}")
if tp_early > 0:
    print(f"  False alerts per catch: {fp_total/tp_early:.1f}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Save outputs
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4 — Saving outputs")
print("=" * 60)

log_df    = pd.DataFrame(log_rows)
alert_df  = pd.DataFrame(alert_rows) if alert_rows else pd.DataFrame()

log_path   = os.path.join(OUTPUT_DIR, "simulation_log.csv")
alert_path = os.path.join(OUTPUT_DIR, "simulation_alerts.csv")

log_df.to_csv(log_path,   index=False)
print(f"  simulation_log.csv    → {len(log_df):,} rows")

if not alert_df.empty:
    alert_df.to_csv(alert_path, index=False)
    print(f"  simulation_alerts.csv → {len(alert_df):,} alerts")

    # Lead time stats for true positives
    tp_df = alert_df[alert_df["type"] == "TRUE_POSITIVE"]
    if len(tp_df):
        lead_times = tp_df["lead_time_h"].dropna()
        print(f"\n  Lead time stats (hours before onset):")
        print(f"    Mean  : {lead_times.mean():.1f}h")
        print(f"    Median: {lead_times.median():.1f}h")
        print(f"    Min   : {lead_times.min():.1f}h")
        print(f"    Max   : {lead_times.max():.1f}h")
        early_warnings = (lead_times > 0).sum()
        print(f"    Warned before onset: "
              f"{early_warnings:,} / {len(tp_df):,} "
              f"({early_warnings/len(tp_df)*100:.1f}%)")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Plots
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5 — Plots")
print("=" * 60)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# ── Plot 1: Active patients per hour by risk tier ──────────
ax = axes[0, 0]
hourly = log_df.groupby(["hour", "risk_category"]).size().unstack(fill_value=0)
for tier, color in [("High","#E24B4A"), ("Medium","#EF9F27"), ("Low","#1D9E75")]:
    if tier in hourly.columns:
        ax.plot(hourly.index, hourly[tier], color=color, lw=1.5, label=tier)
ax.set_xlabel("ICU hour"); ax.set_ylabel("Patient count")
ax.set_title("Active patients by risk tier over time")
ax.legend(); ax.grid(alpha=0.3)

# ── Plot 2: Alert timeline ─────────────────────────────────
ax = axes[0, 1]
if not alert_df.empty:
    tp_alerts = alert_df[alert_df["type"] == "TRUE_POSITIVE"]
    fp_alerts = alert_df[alert_df["type"] == "FALSE_POSITIVE"]
    if len(tp_alerts):
        ax.scatter(tp_alerts["alert_hour"], tp_alerts["priority"],
                   color="#E24B4A", s=60, alpha=0.7, label=f"TP ({len(tp_alerts)})")
    if len(fp_alerts):
        ax.scatter(fp_alerts["alert_hour"], fp_alerts["priority"],
                   color="#378ADD", s=30, alpha=0.4, label=f"FP ({len(fp_alerts)})")
ax.axhline(PRIORITY_THRESHOLD, color="#888780", linestyle="--",
           label=f"Threshold ({PRIORITY_THRESHOLD})")
ax.set_xlabel("ICU hour"); ax.set_ylabel("Priority score at alert")
ax.set_title("Alert events over time")
ax.legend(); ax.grid(alpha=0.3)

# ── Plot 3: Lead time distribution ────────────────────────
ax = axes[1, 0]
if not alert_df.empty and len(tp_df) > 0:
    lead_times = tp_df["lead_time_h"].dropna()
    ax.hist(lead_times, bins=20, color="#378ADD", alpha=0.8, edgecolor="white")
    ax.axvline(0, color="#E24B4A", linestyle="--", lw=2, label="Onset hour")
    ax.axvline(lead_times.mean(), color="#1D9E75", linestyle="--",
               lw=1.5, label=f"Mean lead = {lead_times.mean():.1f}h")
    ax.set_xlabel("Hours before onset (positive = early warning)")
    ax.set_ylabel("Count")
    ax.set_title("Lead time distribution — true positive alerts")
    ax.legend(); ax.grid(alpha=0.3)
else:
    ax.text(0.5, 0.5, "No TP alerts in this simulation window",
            ha="center", va="center", transform=ax.transAxes)
    ax.set_title("Lead time distribution")

# ── Plot 4: Priority score over time for 3 septic patients ─
ax = axes[1, 1]
septic_pids = [pid for pid in patient_order if patient_sepsis[pid] == 1][:3]
colors      = ["#E24B4A", "#378ADD", "#1D9E75"]
for pid, color in zip(septic_pids, colors):
    pat_log = log_df[log_df["patient_id"] == pid].sort_values("hour")
    ax.plot(pat_log["hour"], pat_log["priority"],
            color=color, lw=1.5, label=pid)
    onset = state[pid]["onset_hour"]
    if onset:
        ax.axvline(onset, color=color, linestyle="--", alpha=0.5)
ax.axhline(PRIORITY_THRESHOLD, color="#888780", linestyle=":",
           label=f"Alert threshold ({PRIORITY_THRESHOLD})")
ax.set_xlabel("ICU hour"); ax.set_ylabel("Priority score")
ax.set_title("Priority score timeline — 3 septic patients")
ax.legend(fontsize=8); ax.grid(alpha=0.3); ax.set_ylim(0, 1)

plt.suptitle("Phase 5 — Real-Time ICU Simulation Summary", fontsize=14)
plt.tight_layout()
plot_path = os.path.join(OUTPUT_DIR, "simulation_summary.png")
plt.savefig(plot_path, dpi=120, bbox_inches="tight")
plt.close("all")
print(f"  simulation_summary.png saved")

# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 5 COMPLETE")
print("=" * 60)
print(f"  Patients simulated    : {n_patients:,}")
print(f"  Hours simulated       : {max_hours}")
print(f"  True positive alerts  : {tp_early:,}")
print(f"  False positive alerts : {fp_total:,}")
print(f"  Missed (FN)           : {fn_total:,}")
if tp_early > 0:
    print(f"  False alerts per catch: {fp_total/tp_early:.1f}")
    if not alert_df.empty and len(tp_df) > 0:
        print(f"  Mean lead time        : {tp_df['lead_time_h'].mean():.1f}h before onset")
print(f"\n  simulation_log.csv    : {len(log_df):,} rows")
print(f"  simulation_alerts.csv : {len(alert_df):,} alerts")
print(f"  Artifacts in          : {OUTPUT_DIR}/")
print("=" * 60)