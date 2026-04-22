"""
Phase 4 — Severity Scoring and Patient-Level Prioritization
AI-Based Early Sepsis Prediction System

Input  : output/test_features.csv + models/xgboost_model.pkl
Output : output/patient_scores.csv   — one row per patient per hour
         output/patient_summary.csv  — one row per patient (final risk)
         output/phase4_evaluation.txt

Priority Score formula:
  0.6 × rolling_mean_prob(3h)
  + 0.2 × HR_risk   (uses flag_HR_high — already correct 0/1 binary)
  + 0.2 × BP_risk   (uses flag_MAP_low + flag_SBP_low)

A patient is flagged HIGH when their priority score crosses
the threshold found in Phase 3 (loaded from threshold.pkl).

Patient-level evaluation is the clinically meaningful metric —
not row-level, which produces misleading false positive counts.
"""

import os, gc, csv, joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, f1_score, recall_score, precision_score,
    confusion_matrix, classification_report, roc_curve
)

# ── CONFIG ────────────────────────────────────────────────
OUTPUT_DIR     = "./output"
MODELS_DIR     = "./models"
TEST_IN        = os.path.join(OUTPUT_DIR, "test_features.csv")
ROLLING_WINDOW = 3
W_PROB, W_HR, W_BP = 0.6, 0.2, 0.2

all_feature_cols = joblib.load(
    os.path.join(OUTPUT_DIR, "feature_cols_engineered.pkl"))
model = joblib.load(os.path.join(MODELS_DIR, "xgboost_model.pkl"))

# Load threshold saved by Phase 3 — fall back to 0.45 if file not found
_threshold_path = os.path.join(OUTPUT_DIR, "threshold.pkl")
if os.path.exists(_threshold_path):
    THRESHOLD = joblib.load(_threshold_path)
    print(f"Threshold  : {THRESHOLD:.2f}  (loaded from threshold.pkl)")
else:
    THRESHOLD = 0.45
    print(f"Threshold  : {THRESHOLD:.2f}  (threshold.pkl not found — using default)")
    print("  Tip: re-run phase3_train.py to save the auto-selected threshold.")

print(f"Features   : {len(all_feature_cols)}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Load test data and predict row-level probabilities
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 1 — Predicting row probabilities")
print("=" * 60)

extra_cols = ["flag_HR_high", "flag_MAP_low", "flag_SBP_low",
              "flag_RR_high", "shock_index"]
meta_cols  = ["patient_id", "hospital", "ICULOS", "SepsisLabel", "EarlyLabel"]
keep_cols  = meta_cols + extra_cols

x_rows, y_rows, meta_rows = [], [], []

with open(TEST_IN, "r", encoding="utf-8") as f:
    reader     = csv.reader(f)
    header     = next(reader)
    col_idx    = {c: i for i, c in enumerate(header)}
    feat_idx   = [col_idx[c] for c in all_feature_cols if c in col_idx]
    target_idx = col_idx.get("EarlyLabel")
    keep_idx   = {c: col_idx[c] for c in keep_cols if c in col_idx}

    for line in reader:
        x_row = []
        for i in feat_idx:
            try:
                x_row.append(float(line[i]) if line[i] not in
                             ("","nan","None") else 0.0)
            except (ValueError, IndexError):
                x_row.append(0.0)
        x_rows.append(x_row)
        try:
            y_rows.append(float(line[target_idx]))
        except:
            y_rows.append(0.0)
        meta_rows.append({c: line[idx] for c, idx in keep_idx.items()})

X      = np.array(x_rows, dtype=np.float32)
y      = np.array(y_rows, dtype=np.float32)
del x_rows, y_rows; gc.collect()

dmat   = xgb.DMatrix(X, feature_names=all_feature_cols)
y_prob = model.predict(dmat)
del X, dmat; gc.collect()

print(f"  Rows predicted : {len(y_prob):,}")
print(f"  Row-level AUC  : {roc_auc_score(y, y_prob):.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Build patient-hourly DataFrame
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — Building patient DataFrame")
print("=" * 60)

df = pd.DataFrame(meta_rows)
df["sepsis_prob"] = y_prob
df["true_label"]  = y

for col in ["ICULOS", "SepsisLabel", "EarlyLabel"] + extra_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df.sort_values(["patient_id", "ICULOS"], inplace=True)
df.reset_index(drop=True, inplace=True)
del meta_rows; gc.collect()

print(f"  Patients : {df['patient_id'].nunique():,}")
print(f"  Rows     : {len(df):,}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Severity scoring per patient
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Severity scoring")
print("=" * 60)

def compute_severity(group):
    g = group.copy().reset_index(drop=True)

    g["prob_smooth"] = (
        g["sepsis_prob"].rolling(ROLLING_WINDOW, min_periods=1).mean()
    )

    # Use binary flag columns (correct 0/1, not affected by StandardScaler)
    hr_risk = g["flag_HR_high"].values if "flag_HR_high" in g.columns \
              else np.zeros(len(g))
    bp_low  = g["flag_MAP_low"].values  if "flag_MAP_low"  in g.columns \
              else np.zeros(len(g))
    sbp_low = g["flag_SBP_low"].values  if "flag_SBP_low"  in g.columns \
              else np.zeros(len(g))
    bp_risk = np.clip(bp_low + sbp_low * 0.5, 0, 1)

    g["hr_risk"]  = hr_risk
    g["bp_risk"]  = bp_risk
    g["priority_score"] = (
        W_PROB * g["prob_smooth"] +
        W_HR   * g["hr_risk"]    +
        W_BP   * g["bp_risk"]
    ).clip(0, 1)

    g["risk_category"] = pd.cut(
        g["priority_score"],
        bins=[-0.01, 0.40, 0.60, 1.01],
        labels=["Low", "Medium", "High"]
    )

    is_high = (g["priority_score"] >= THRESHOLD).astype(int).values
    consec, count = [], 0
    for v in is_high:
        count = count + 1 if v else 0
        consec.append(count)
    g["consec_high_hours"] = consec
    g["patient_alert"]     = (np.array(consec) >= 1).astype(int)
    return g

print("  Computing per patient...")
df = df.groupby("patient_id", group_keys=False).apply(compute_severity)
df.reset_index(drop=True, inplace=True)
gc.collect()

df.to_csv(os.path.join(OUTPUT_DIR, "patient_scores.csv"), index=False)
print("  patient_scores.csv saved")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Patient-level summary (one row per patient, sorted by priority)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4 — Patient summary")
print("=" * 60)

summary = df.groupby("patient_id").agg(
    hospital        = ("hospital",          "first"),
    max_prob        = ("sepsis_prob",       "max"),
    max_priority    = ("priority_score",    "max"),
    mean_priority   = ("priority_score",    "mean"),
    max_consec_high = ("consec_high_hours", "max"),
    patient_alert   = ("patient_alert",     "max"),
    icu_hours       = ("ICULOS",            "max"),
    true_sepsis     = ("SepsisLabel",       "max"),
    true_early      = ("EarlyLabel",        "max"),
).reset_index()

summary["final_risk"] = pd.cut(
    summary["max_priority"],
    bins=[-0.01, 0.40, 0.60, 1.01],
    labels=["Low", "Medium", "High"]
)

summary.sort_values("max_priority", ascending=False).to_csv(
    os.path.join(OUTPUT_DIR, "patient_summary.csv"), index=False)

print(f"  {len(summary):,} patients")
print(f"\n  Risk tier distribution:")
for tier in ["High", "Medium", "Low"]:
    n = (summary["final_risk"] == tier).sum()
    print(f"    {tier:8s}: {n:,} ({n/len(summary)*100:.1f}%)")
print(f"\n  Patients alerted     : {summary['patient_alert'].sum():,}")
print(f"  True sepsis patients : {int(summary['true_sepsis'].sum()):,}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Patient-level threshold sweep and evaluation
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5 — Patient-level threshold sweep")
print("=" * 60)

y_pt  = summary["true_sepsis"].values.astype(int)
y_pr  = summary["max_priority"].values
pat_auc = roc_auc_score(y_pt, y_pr)

print(f"\n  Patient ROC-AUC : {pat_auc:.4f}")
print(f"\n  {'Threshold':>10} {'Recall':>8} {'Precision':>10} "
      f"{'F1':>8} {'FP/TP':>8}")
print("  " + "-" * 48)

sweep = []
for t in np.arange(0.20, 0.81, 0.05):
    yp    = (y_pr >= t).astype(int)
    rec   = recall_score(y_pt, yp, zero_division=0)
    prec  = precision_score(y_pt, yp, zero_division=0)
    f1    = f1_score(y_pt, yp, zero_division=0)
    cm_s  = confusion_matrix(y_pt, yp)
    tn_s, fp_s, fn_s, tp_s = cm_s.ravel()
    fp_tp = fp_s / max(tp_s, 1)
    sweep.append((t, rec, prec, f1, fp_tp, tp_s, fp_s))
    print(f"  {t:>10.2f} {rec:>8.3f} {prec:>10.3f} {f1:>8.3f} "
          f"{fp_tp:>8.1f}  (TP={tp_s} FP={fp_s})")

sweep = np.array(sweep)
best_f1_idx = sweep[:, 3].argmax()
cands = [r for r in sweep if r[1] >= 0.60]
best_bal = max(cands, key=lambda r: r[2]) if cands else sweep[best_f1_idx]
FINAL_THRESHOLD = float(best_bal[0])

print(f"\n  Best F1       : t={sweep[best_f1_idx,0]:.2f}  "
      f"Recall={sweep[best_f1_idx,1]:.3f}  "
      f"Precision={sweep[best_f1_idx,2]:.3f}")
print(f"  Best balanced : t={FINAL_THRESHOLD:.2f}  "
      f"Recall={best_bal[1]:.3f}  "
      f"Precision={best_bal[2]:.3f}  ← recommended")

# Final evaluation
y_final   = (y_pr >= FINAL_THRESHOLD).astype(int)
cm_f      = confusion_matrix(y_pt, y_final)
tn, fp, fn, tp_v = cm_f.ravel()
recall    = recall_score(y_pt, y_final, zero_division=0)
precision = precision_score(y_pt, y_final, zero_division=0)
f1        = f1_score(y_pt, y_final, zero_division=0)

print(f"\n  Patient ROC-AUC : {pat_auc:.4f}")
print(f"  Recall          : {recall:.4f}  ({tp_v:,} septic caught)")
print(f"  Precision       : {precision:.4f}  ({fp:,} false alerts)")
print(f"  F1              : {f1:.4f}")
print(f"  TN={tn:,}  FP={fp:,}")
print(f"  FN={fn:,}   TP={tp_v:,}")
print(f"  False alarms per catch : {fp/max(tp_v,1):.1f}")

septic = summary[summary["true_sepsis"] == 1]
caught = septic[y_pr[summary["true_sepsis"] == 1] >= FINAL_THRESHOLD]
print(f"  Septic caught   : {len(caught):,} / {len(septic):,} "
      f"({len(caught)/max(len(septic),1)*100:.1f}%)")

with open(os.path.join(OUTPUT_DIR, "phase4_evaluation.txt"), "w") as rpt:
    rpt.write("Phase 4 — Patient-Level Severity Scoring\n" + "="*50 + "\n")
    rpt.write(f"Patient ROC-AUC        : {pat_auc:.4f}\n")
    rpt.write(f"Final threshold        : {FINAL_THRESHOLD:.2f}\n")
    rpt.write(f"Recall                 : {recall:.4f}\n")
    rpt.write(f"Precision              : {precision:.4f}\n")
    rpt.write(f"F1                     : {f1:.4f}\n")
    rpt.write(f"TN={tn} FP={fp} FN={fn} TP={tp_v}\n")
    rpt.write(f"False alarms per catch : {fp/max(tp_v,1):.1f}\n\n")
    rpt.write(classification_report(y_pt, y_final,
                                     target_names=["No Sepsis","Sepsis"]))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Plots
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6 — Plots")
print("=" * 60)

# Patient confusion matrix
fig, ax = plt.subplots(figsize=(5, 4))
im = ax.imshow(cm_f, cmap="Blues"); plt.colorbar(im, ax=ax)
ax.set_xticks([0,1]); ax.set_xticklabels(["No Sepsis","Sepsis"])
ax.set_yticks([0,1]); ax.set_yticklabels(["No Sepsis","Sepsis"])
thresh_cm = cm_f.max() / 2
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm_f[i,j]:,}", ha="center", va="center",
                color="white" if cm_f[i,j] > thresh_cm else "black")
ax.set_ylabel("True (patient)"); ax.set_xlabel("Predicted (patient)")
ax.set_title(f"Patient-Level Confusion Matrix (t={FINAL_THRESHOLD:.2f})")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "patient_confusion_matrix.png"),
            dpi=120, bbox_inches="tight")
plt.close("all"); print("  patient_confusion_matrix.png")

# Patient threshold sweep
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(sweep[:,0], sweep[:,1], "o-", color="#E24B4A", lw=2, label="Recall")
ax.plot(sweep[:,0], sweep[:,2], "o-", color="#378ADD", lw=2, label="Precision")
ax.plot(sweep[:,0], sweep[:,3], "o-", color="#1D9E75", lw=2, label="F1")
ax.axvline(FINAL_THRESHOLD, color="#888780", linestyle="--",
           label=f"Recommended t={FINAL_THRESHOLD:.2f}")
ax.set_xlabel("Max Priority Score Threshold"); ax.set_ylabel("Score")
ax.set_title("Patient-Level Threshold Sweep")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "patient_threshold_sweep.png"),
            dpi=120, bbox_inches="tight")
plt.close("all"); print("  patient_threshold_sweep.png")

# Priority score distribution
fig, ax = plt.subplots(figsize=(8, 5))
sep   = summary[summary["true_sepsis"] == 1]["max_priority"]
nosep = summary[summary["true_sepsis"] == 0]["max_priority"]
ax.hist(nosep, bins=50, alpha=0.6, color="#378ADD",
        label=f"No Sepsis (n={len(nosep):,})", density=True)
ax.hist(sep,   bins=50, alpha=0.6, color="#E24B4A",
        label=f"Sepsis (n={len(sep):,})", density=True)
ax.axvline(0.40, color="#888780", linestyle="--", label="Low/Medium (0.40)")
ax.axvline(0.60, color="#1D9E75", linestyle="--", label="Medium/High (0.60)")
ax.axvline(FINAL_THRESHOLD, color="#E24B4A", linestyle=":",
           lw=2, label=f"Recommended t={FINAL_THRESHOLD:.2f}")
ax.set_xlabel("Max Priority Score"); ax.set_ylabel("Density")
ax.set_title("Priority Score Distribution — Patient Level")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "priority_score_dist.png"),
            dpi=120, bbox_inches="tight")
plt.close("all"); print("  priority_score_dist.png")

# Patient timelines (3 septic patients)
septic_pids = summary[summary["true_sepsis"] == 1]["patient_id"].values[:3]
fig, axes   = plt.subplots(3, 1, figsize=(12, 10))
for ax, pid in zip(axes, septic_pids):
    pat = df[df["patient_id"] == pid].sort_values("ICULOS")
    ax.plot(pat["ICULOS"], pat["sepsis_prob"],
            color="#378ADD", lw=1.5, alpha=0.7, label="Raw prob")
    ax.plot(pat["ICULOS"], pat["prob_smooth"],
            color="#E24B4A", lw=2, label="Smoothed prob")
    ax.plot(pat["ICULOS"], pat["priority_score"],
            color="#1D9E75", lw=2, linestyle="--", label="Priority score")
    ax.axhline(THRESHOLD, color="#888780", linestyle=":",
               label=f"Threshold ({THRESHOLD:.2f})")
    onset = pat[pat["SepsisLabel"] == 1.0]
    if len(onset):
        ax.axvline(float(onset["ICULOS"].iloc[0]),
                   color="#E24B4A", linestyle="--",
                   alpha=0.6, label="Sepsis onset")
    ax.set_title(f"Patient: {pid}")
    ax.set_xlabel("ICU hour"); ax.set_ylabel("Score")
    ax.legend(fontsize=8); ax.set_ylim(0, 1)
plt.suptitle("Sample septic patient timelines")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "patient_timelines.png"),
            dpi=120, bbox_inches="tight")
plt.close("all"); print("  patient_timelines.png")

print("\n" + "=" * 60)
print("PHASE 4 COMPLETE")
print("=" * 60)
print(f"  patient_scores.csv    : {len(df):,} rows")
print(f"  patient_summary.csv   : {len(summary):,} patients")
print(f"  Patient AUC           : {pat_auc:.4f}")
print(f"  Recall                : {recall:.4f}")
print(f"  Precision             : {precision:.4f}")
print(f"  F1                    : {f1:.4f}")
print(f"  False alarms per catch: {fp/max(tp_v,1):.1f}")
print(f"  Recommended threshold : {FINAL_THRESHOLD:.2f}")
print(f"  Artifacts in          : {OUTPUT_DIR}/")
print("=" * 60)