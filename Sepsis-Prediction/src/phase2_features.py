"""
Phase 2 — Feature Engineering
AI-Based Early Sepsis Prediction System

Input  : output/train.csv, output/test.csv
Output : output/train_features.csv, output/test_features.csv
         output/feature_cols_engineered.pkl

Memory strategy: csv.reader line-by-line, one patient buffer at a time.
No pd.read_csv on large files anywhere.

Features created per vital (HR, O2Sat, SBP, DBP, MAP, Resp):
  - Rolling mean  (3h, 6h windows)
  - Rolling std   (3h, 6h windows)
  - Delta 1h      (1-hour change)
  - Delta 2h      (2-hour change)

Clinical flags (binary 0/1):
  - flag_MAP_low          MAP < 65
  - flag_HR_high          HR > 100
  - flag_RR_high          Resp > 22
  - flag_SBP_low          SBP < 90
  - flag_O2_low           O2Sat < 94
  - flag_hemo_instability MAP < 65 AND HR > 100

Derived score:
  - shock_index           HR / SBP
"""

import os, gc, csv, joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── CONFIG ────────────────────────────────────────────────
OUTPUT_DIR = "./output"
TRAIN_IN   = os.path.join(OUTPUT_DIR, "train.csv")
TEST_IN    = os.path.join(OUTPUT_DIR, "test.csv")
TRAIN_OUT  = os.path.join(OUTPUT_DIR, "train_features.csv")
TEST_OUT   = os.path.join(OUTPUT_DIR, "test_features.csv")

feature_cols = joblib.load(os.path.join(OUTPUT_DIR, "feature_cols.pkl"))
print(f"Phase 1 features: {feature_cols}")

VITAL_COLS = [c for c in feature_cols
              if c not in ("Gender", "Unit1", "Unit2", "HospAdmTime", "Age")]
print(f"Vital cols      : {VITAL_COLS}")

WINDOWS = [3, 6]

# ─────────────────────────────────────────────────────────────────────────────
# Feature engineering — runs on one patient's DataFrame (tiny, ~38 rows avg)
# ─────────────────────────────────────────────────────────────────────────────

def engineer_patient(df):
    df = df.copy().reset_index(drop=True)

    for col in VITAL_COLS:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        for w in WINDOWS:
            df[f"{col}_mean{w}"] = series.rolling(w, min_periods=1).mean()
            df[f"{col}_std{w}"]  = series.rolling(w, min_periods=1).std().fillna(0)
        df[f"{col}_delta1"] = series.diff(1).fillna(0)
        df[f"{col}_delta2"] = series.diff(2).fillna(0)

    if "MAP" in df.columns:
        df["flag_MAP_low"]  = (pd.to_numeric(df["MAP"],   errors="coerce") < 65).astype(int)
    if "HR" in df.columns:
        df["flag_HR_high"]  = (pd.to_numeric(df["HR"],    errors="coerce") > 100).astype(int)
    if "Resp" in df.columns:
        df["flag_RR_high"]  = (pd.to_numeric(df["Resp"],  errors="coerce") > 22).astype(int)
    if "SBP" in df.columns:
        df["flag_SBP_low"]  = (pd.to_numeric(df["SBP"],   errors="coerce") < 90).astype(int)
    if "O2Sat" in df.columns:
        df["flag_O2_low"]   = (pd.to_numeric(df["O2Sat"], errors="coerce") < 94).astype(int)
    if "HR" in df.columns and "SBP" in df.columns:
        hr  = pd.to_numeric(df["HR"],  errors="coerce")
        sbp = pd.to_numeric(df["SBP"], errors="coerce").replace(0, np.nan)
        df["shock_index"] = (hr / sbp).fillna(0).clip(upper=5)
    if "MAP" in df.columns and "HR" in df.columns:
        df["flag_hemo_instability"] = (
            (pd.to_numeric(df["MAP"], errors="coerce") < 65) &
            (pd.to_numeric(df["HR"],  errors="coerce") > 100)
        ).astype(int)

    base     = set(feature_cols) | {"patient_id","hospital","ICULOS",
                                     "SepsisLabel","EarlyLabel"}
    new_cols = [c for c in df.columns if c not in base]
    df[new_cols] = df[new_cols].ffill().bfill().fillna(0)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# Infer output columns from first patient only (no large file read)
# ─────────────────────────────────────────────────────────────────────────────
print("\nInferring output schema from first patient...")

def read_first_patient(csv_path):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows   = []
        cur_pid = None
        for line in reader:
            rd  = dict(zip(header, line))
            pid = rd.get("patient_id")
            if cur_pid is None:
                cur_pid = pid
            if pid != cur_pid:
                break
            rows.append(rd)
    return header, rows

in_header, sample_rows = read_first_patient(TRAIN_IN)
sample_df  = pd.DataFrame(sample_rows)
sample_eng = engineer_patient(sample_df)
OUTPUT_COLS = sample_eng.columns.tolist()

new_feature_cols = [c for c in OUTPUT_COLS
                    if c not in (list(feature_cols) +
                                 ["patient_id","hospital","ICULOS",
                                  "SepsisLabel","EarlyLabel"])]
all_feature_cols = feature_cols + new_feature_cols
joblib.dump(all_feature_cols,
            os.path.join(OUTPUT_DIR, "feature_cols_engineered.pkl"))

del sample_df, sample_eng, sample_rows
gc.collect()

print(f"  Original features  : {len(feature_cols)}")
print(f"  New features added : {len(new_feature_cols)}")
print(f"  Total features     : {len(all_feature_cols)}")
print(f"\n  New features:")
for f in new_feature_cols:
    print(f"    {f}")

# ─────────────────────────────────────────────────────────────────────────────
# Core processing — csv.reader line-by-line, one patient buffer at a time
# ─────────────────────────────────────────────────────────────────────────────

def process_csv(in_path, out_path):
    total_lines = sum(1 for _ in open(in_path, encoding="utf-8")) - 1
    print(f"  Total rows: {total_lines:,}")

    out_f = open(out_path, "w", newline="", encoding="utf-8")
    out_w = csv.writer(out_f)
    out_w.writerow(OUTPUT_COLS)

    n_patients = n_rows = 0
    cur_pid    = None
    cur_buf    = []

    def flush(pid, buf):
        nonlocal n_patients, n_rows
        if not buf: return
        df     = pd.DataFrame(buf)
        if "ICULOS" in df.columns:
            df = df.sort_values("ICULOS").reset_index(drop=True)
        df_eng = engineer_patient(df)
        df_eng = df_eng.reindex(columns=OUTPUT_COLS)
        for row in df_eng.itertuples(index=False):
            out_w.writerow(list(row))
        n_patients += 1; n_rows += len(df_eng)
        del df, df_eng
        if n_patients % 5000 == 0:
            gc.collect()
            print(f"    {n_patients:,} patients / {n_rows:,} rows written...")

    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows_read = 0
        for line in reader:
            rd  = dict(zip(header, line))
            pid = rd.get("patient_id")
            if pid != cur_pid:
                flush(cur_pid, cur_buf)
                cur_pid = pid; cur_buf = []
            cur_buf.append(rd)
            rows_read += 1
            if rows_read % 100_000 == 0:
                print(f"    rows read: {rows_read:,}  patients done: {n_patients:,}")

    flush(cur_pid, cur_buf)
    out_f.close(); gc.collect()
    return n_patients, n_rows

# ─────────────────────────────────────────────────────────────────────────────
# Run on train and test
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 2 — Feature Engineering")
print("=" * 60)

print("\n  Processing train.csv...")
tr_p, tr_r = process_csv(TRAIN_IN, TRAIN_OUT)
print(f"  Train done — {tr_p:,} patients, {tr_r:,} rows")

print("\n  Processing test.csv...")
te_p, te_r = process_csv(TEST_IN, TEST_OUT)
print(f"  Test  done — {te_p:,} patients, {te_r:,} rows")

# ─────────────────────────────────────────────────────────────────────────────
# Sanity checks
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Sanity checks")
print("=" * 60)

sample_tr = pd.read_csv(TRAIN_OUT, nrows=500)
sample_te = pd.read_csv(TEST_OUT,  nrows=500)

assert "EarlyLabel"   in sample_tr.columns, "EarlyLabel missing"
assert "shock_index"  in sample_tr.columns, "shock_index missing"
assert "flag_HR_high" in sample_tr.columns, "flag_HR_high missing"

fc_present = [c for c in all_feature_cols if c in sample_tr.columns]
assert sample_tr[fc_present].isnull().sum().sum() == 0, "NaNs in train sample"
assert sample_te[fc_present].isnull().sum().sum() == 0, "NaNs in test sample"
print("  All checks PASSED")

# Feature distribution plot
fig, axes = plt.subplots(3, 4, figsize=(20, 12))
axes = axes.flatten()
plot_cols = [c for c in all_feature_cols if c in sample_tr.columns][:12]
for i, col in enumerate(plot_cols):
    sep   = sample_tr[sample_tr["EarlyLabel"] == 1][col].dropna()
    nosep = sample_tr[sample_tr["EarlyLabel"] == 0][col].dropna()
    axes[i].hist(nosep.values, bins=30, alpha=0.6, color="#378ADD",
                 label="No sepsis", density=True)
    axes[i].hist(sep.values,   bins=30, alpha=0.6, color="#E24B4A",
                 label="Sepsis", density=True)
    axes[i].set_title(col, fontsize=9); axes[i].legend(fontsize=7)
for j in range(len(plot_cols), len(axes)):
    axes[j].set_visible(False)
plt.suptitle("Feature distributions — sepsis vs no sepsis (train sample)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "feature_distributions.png"),
            dpi=100, bbox_inches="tight")
plt.close("all")
del sample_tr, sample_te; gc.collect()

print("\n" + "=" * 60)
print("PHASE 2 COMPLETE")
print("=" * 60)
print(f"  train_features.csv : {tr_r:,} rows")
print(f"  test_features.csv  : {te_r:,} rows")
print(f"  Total features     : {len(all_feature_cols)}")
print(f"  Saved              : feature_cols_engineered.pkl")
print(f"  Artifacts in       : {OUTPUT_DIR}/")
print("=" * 60)
