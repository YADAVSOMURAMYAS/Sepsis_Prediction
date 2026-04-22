"""
Phase 1 — Data Preprocessing Pipeline
AI-Based Early Sepsis Prediction System
PhysioNet Sepsis Challenge 2019

Handles trainingdataA (20,336 files) and trainingdataB (20,000 files).
Memory strategy: csv.writer row-by-row, no large concat or read_csv.

Steps:
  1. Stream all .psv → raw_combined.csv
  2. EDA (chunked single pass)
  3. Patient-wise train/test split
  4. Imputation (two-pass chunked)
  5. Scaling (partial_fit on train)
  6. Early label engineering
  7. Sanity checks and save
"""

import os, gc, csv, glob, joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

# ── CONFIG ────────────────────────────────────────────────
DATA_DIR_A          = "./data/trainingdataA"
DATA_DIR_B          = "./data/trainingdataB"
OUTPUT_DIR          = "./output"
EARLY_HOURS         = 6
TEST_SIZE           = 0.20
RANDOM_STATE        = 42
MISSING_DROP_THRESH = 0.85
READ_CHUNK          = 10_000

os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_CSV   = os.path.join(OUTPUT_DIR, "raw_combined.csv")
TRAIN_CSV = os.path.join(OUTPUT_DIR, "train.csv")
TEST_CSV  = os.path.join(OUTPUT_DIR, "test.csv")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Stream every .psv to disk using csv.writer (row by row)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Streaming .psv files → raw_combined.csv")
print("=" * 60)

def stream_psv_folder(folder_path, hospital_tag, out_writer,
                      master_columns, header_written):
    psv_files = sorted(glob.glob(os.path.join(folder_path, "*.psv")))
    if not psv_files:
        raise FileNotFoundError(f"No .psv files found in: {folder_path}")
    print(f"\n  [{hospital_tag}] {len(psv_files):,} files...")
    patient_index = []
    for path in tqdm(psv_files, desc=f"  Streaming {hospital_tag}"):
        fname      = os.path.splitext(os.path.basename(path))[0]
        patient_id = f"{hospital_tag}_{fname}"
        try:
            df = pd.read_csv(path, sep="|", dtype=str)
        except Exception as e:
            print(f"\n  WARNING: skip {path} — {e}")
            continue
        df.insert(0, "patient_id", patient_id)
        df.insert(1, "hospital",   hospital_tag)
        if "ICULOS" not in df.columns:
            df.insert(2, "ICULOS", [str(i) for i in range(1, len(df) + 1)])
        if not header_written[0]:
            master_columns.extend(df.columns.tolist())
            out_writer.writerow(master_columns)
            header_written[0] = True
        col_idx = {c: i for i, c in enumerate(df.columns)}
        for _, row in df.iterrows():
            out_writer.writerow([row[c] if c in col_idx else ""
                                 for c in master_columns])
        sep_col    = df["SepsisLabel"] if "SepsisLabel" in df.columns \
                     else pd.Series(["0"])
        sepsis_max = int(any(v == "1" for v in sep_col))
        patient_index.append((patient_id, hospital_tag, sepsis_max))
        del df
        if len(patient_index) % 1000 == 0:
            gc.collect()
    print(f"  [{hospital_tag}] {len(patient_index):,} patients written")
    return patient_index

master_columns = []
header_written = [False]
patient_index  = []

with open(RAW_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    patient_index.extend(
        stream_psv_folder(DATA_DIR_A, "A", writer, master_columns, header_written))
    patient_index.extend(
        stream_psv_folder(DATA_DIR_B, "B", writer, master_columns, header_written))

gc.collect()
patient_meta = pd.DataFrame(patient_index,
                             columns=["patient_id", "hospital", "sepsis"])
print(f"\n  Total patients : {len(patient_meta):,}  "
      f"(A={int((patient_meta.hospital=='A').sum()):,}  "
      f"B={int((patient_meta.hospital=='B').sum()):,})")
print(f"  Septic patients: {int(patient_meta.sepsis.sum()):,}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — EDA (chunked single pass)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — EDA")
print("=" * 60)

header_row   = pd.read_csv(RAW_CSV, nrows=0).columns.tolist()
non_features = {"patient_id", "hospital", "ICULOS", "SepsisLabel"}
feature_cols = [c for c in header_row if c not in non_features]

null_sum  = pd.Series(0, index=feature_cols, dtype=np.int64)
row_total = sep_total = 0
hosp_rows = {"A": 0, "B": 0}
hosp_sep  = {"A": 0, "B": 0}

for chunk in tqdm(pd.read_csv(RAW_CSV, chunksize=READ_CHUNK, low_memory=False),
                  desc="  EDA scan"):
    fc = [c for c in feature_cols if c in chunk.columns]
    null_sum[fc] += chunk[fc].isnull().sum()
    row_total    += len(chunk)
    sep_total    += int(chunk["SepsisLabel"].sum())
    for tag in ["A", "B"]:
        sub = chunk[chunk["hospital"] == tag]
        hosp_rows[tag] += len(sub)
        hosp_sep[tag]  += int(sub["SepsisLabel"].sum())

missing_pct = (null_sum / max(row_total, 1) * 100).sort_values(ascending=False)
print("\n  Missing value rates (top 20):")
print(missing_pct.head(20).to_string())

cols_to_drop = missing_pct[missing_pct > MISSING_DROP_THRESH * 100].index.tolist()
if cols_to_drop:
    print(f"\n  Dropping {len(cols_to_drop)} col(s): {cols_to_drop}")
    feature_cols = [c for c in feature_cols if c not in cols_to_drop]

n_pos = sep_total
n_neg = row_total - n_pos
ratio = n_neg / max(n_pos, 1)
print(f"\n  Neg: {n_neg:,}  Pos: {n_pos:,}  Ratio: {ratio:.1f}:1")
print(f"  Recommended scale_pos_weight: {ratio:.0f}")
for tag in ["A", "B"]:
    r = hosp_sep[tag] / max(hosp_rows[tag], 1) * 100
    print(f"  [{tag}] sepsis rate: {r:.2f}%")

fig, axes = plt.subplots(1, 3, figsize=(18, 4))
top_m = missing_pct.head(15)
axes[0].barh(top_m.index[::-1], top_m.values[::-1], color="#378ADD")
axes[0].set_xlabel("Missing %"); axes[0].set_title("Top 15 features — missing rate")
axes[0].axvline(MISSING_DROP_THRESH * 100, color="red", linestyle="--",
                label="Drop threshold"); axes[0].legend()
axes[1].bar(["No Sepsis", "Sepsis"], [n_neg, n_pos], color=["#1D9E75", "#E24B4A"])
axes[1].set_title("Class distribution")
h_vals = [hosp_sep[t] / hosp_rows[t] * 100 for t in ["A", "B"]]
axes[2].bar(["A", "B"], h_vals, color=["#378ADD", "#7F77DD"])
axes[2].set_title("Sepsis rate by hospital (%)")
for i, v in enumerate(h_vals):
    axes[2].text(i, v + 0.05, f"{v:.2f}%", ha="center")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "eda_overview.png"), dpi=150, bbox_inches="tight")
plt.close("all"); gc.collect()
print(f"  EDA plot saved")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Patient-wise train/test split (metadata only in RAM)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Train/test split")
print("=" * 60)

patient_meta["strat_key"] = (
    patient_meta["hospital"] + "_" + patient_meta["sepsis"].astype(str))

train_meta, test_meta = train_test_split(
    patient_meta, test_size=TEST_SIZE,
    random_state=RANDOM_STATE, stratify=patient_meta["strat_key"])

train_ids = set(train_meta["patient_id"])
test_ids  = set(test_meta["patient_id"])
assert len(train_ids & test_ids) == 0, "Patient leak!"

print(f"  Train patients : {len(train_ids):,}")
print(f"  Test  patients : {len(test_ids):,}")
print("  Overlap check  : PASSED")

joblib.dump(train_ids, os.path.join(OUTPUT_DIR, "train_ids.pkl"))
joblib.dump(test_ids,  os.path.join(OUTPUT_DIR, "test_ids.pkl"))

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Imputation (two-pass chunked)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4 — Imputation")
print("=" * 60)

print("  Pass 1 — computing train means...")
tr_sum   = {c: 0.0 for c in feature_cols}
tr_count = {c: 0   for c in feature_cols}

for chunk in tqdm(pd.read_csv(RAW_CSV, chunksize=READ_CHUNK, low_memory=False),
                  desc="  mean scan"):
    sub = chunk[chunk["patient_id"].isin(train_ids)]
    for c in feature_cols:
        if c in sub.columns:
            col = pd.to_numeric(sub[c], errors="coerce")
            tr_sum[c]   += float(col.sum(skipna=True))
            tr_count[c] += int(col.notna().sum())

train_means = {c: (tr_sum[c] / tr_count[c]) if tr_count[c] > 0 else 0.0
               for c in feature_cols}
train_means_series = pd.Series(train_means)
joblib.dump(train_means_series, os.path.join(OUTPUT_DIR, "imputation_means.pkl"))
print("  Train means saved")

print("\n  Pass 2 — forward-fill + write train/test CSVs...")
out_cols = [c for c in master_columns if c not in cols_to_drop]

train_f = open(TRAIN_CSV, "w", newline="", encoding="utf-8")
test_f  = open(TEST_CSV,  "w", newline="", encoding="utf-8")
train_w = csv.writer(train_f); train_w.writerow(out_cols)
test_w  = csv.writer(test_f);  test_w.writerow(out_cols)

cur_pid = None
cur_buf = []

def flush_to_csv(pid, buf, writer):
    if not buf: return
    df = pd.DataFrame(buf, columns=out_cols)
    fc = [c for c in feature_cols if c in df.columns]
    df[fc] = df[fc].apply(pd.to_numeric, errors="coerce")
    df[fc] = df[fc].ffill().fillna({c: train_means[c] for c in fc})
    for row in df.itertuples(index=False):
        writer.writerow(list(row))
    del df

for chunk in tqdm(pd.read_csv(RAW_CSV, chunksize=READ_CHUNK, low_memory=False),
                  desc="  splitting"):
    chunk.drop(columns=[c for c in cols_to_drop if c in chunk.columns],
               inplace=True, errors="ignore")
    for rd in chunk.to_dict("records"):
        pid = rd.get("patient_id")
        if pid != cur_pid:
            if cur_pid is not None:
                w = train_w if cur_pid in train_ids else test_w
                flush_to_csv(cur_pid, cur_buf, w)
            cur_pid = pid; cur_buf = []
        cur_buf.append(rd)

if cur_pid is not None:
    w = train_w if cur_pid in train_ids else test_w
    flush_to_csv(cur_pid, cur_buf, w)

train_f.close(); test_f.close(); gc.collect()
print("  train.csv and test.csv written")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Scaling (partial_fit on train, transform both)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5 — Scaling")
print("=" * 60)

scaler = StandardScaler()

for chunk in tqdm(pd.read_csv(TRAIN_CSV, chunksize=READ_CHUNK, low_memory=False),
                  desc="  scaler fit"):
    fc  = [c for c in feature_cols if c in chunk.columns]
    arr = chunk[fc].apply(pd.to_numeric, errors="coerce").fillna(0).values
    scaler.partial_fit(arr)

joblib.dump(scaler, os.path.join(OUTPUT_DIR, "scaler.pkl"))
print("  scaler.pkl saved")

def scale_csv_inplace(csv_path, scaler, feature_cols, chunk_size):
    tmp = csv_path + ".tmp"; first = True
    for chunk in tqdm(pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False),
                      desc=f"  scale {os.path.basename(csv_path)}"):
        fc  = [c for c in feature_cols if c in chunk.columns]
        arr = chunk[fc].apply(pd.to_numeric, errors="coerce").fillna(0).values
        chunk[fc] = scaler.transform(arr)
        chunk.to_csv(tmp, index=False, header=first,
                     mode="w" if first else "a"); first = False
    os.replace(tmp, csv_path)

scale_csv_inplace(TRAIN_CSV, scaler, feature_cols, READ_CHUNK)
scale_csv_inplace(TEST_CSV,  scaler, feature_cols, READ_CHUNK)
gc.collect()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Early label engineering (patient-buffered, csv.writer row by row)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"STEP 6 — Early labels (N={EARLY_HOURS}h)")
print("=" * 60)

def apply_early_labels(in_path, out_path, n_hours, chunk_size):
    tmp_out = out_path + ".tmp"
    out_f   = open(tmp_out, "w", newline="", encoding="utf-8")
    header  = pd.read_csv(in_path, nrows=0).columns.tolist()
    if "EarlyLabel" not in header:
        header.append("EarlyLabel")
    out_w    = csv.writer(out_f); out_w.writerow(header)
    cur_pid  = None; cur_buf = []; added = 0

    def flush(buf):
        nonlocal added
        if not buf: return
        df = pd.DataFrame(buf)
        if "EarlyLabel" not in df.columns:
            df["EarlyLabel"] = df["SepsisLabel"].values.copy()
        sep = pd.to_numeric(df["SepsisLabel"], errors="coerce").fillna(0)
        if sep.max() == 1:
            onset = int(sep.values.argmax())
            start = max(0, onset - n_hours)
            df.iloc[start:onset, df.columns.get_loc("EarlyLabel")] = 1
            added += onset - start
        df = df.reindex(columns=header)
        for row in df.itertuples(index=False):
            out_w.writerow(list(row))
        del df

    for chunk in tqdm(pd.read_csv(in_path, chunksize=chunk_size, low_memory=False),
                      desc=f"  {os.path.basename(in_path)}"):
        for rd in chunk.to_dict("records"):
            pid = rd.get("patient_id")
            if pid != cur_pid:
                flush(cur_buf); cur_pid = pid; cur_buf = []
            cur_buf.append(rd)
    flush(cur_buf)
    out_f.close(); os.replace(tmp_out, out_path)
    return added

added_tr = apply_early_labels(TRAIN_CSV, TRAIN_CSV, EARLY_HOURS, READ_CHUNK)
added_te = apply_early_labels(TEST_CSV,  TEST_CSV,  EARLY_HOURS, READ_CHUNK)
print(f"  Early rows added — train: {added_tr:,}  test: {added_te:,}")
gc.collect()

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Sanity checks and save
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7 — Sanity checks")
print("=" * 60)

sample_tr = pd.read_csv(TRAIN_CSV, nrows=2000)
sample_te = pd.read_csv(TEST_CSV,  nrows=2000)
fc_present = [c for c in feature_cols if c in sample_tr.columns]

assert sample_tr[fc_present].isnull().sum().sum() == 0, "NaNs in train"
assert sample_te[fc_present].isnull().sum().sum() == 0, "NaNs in test"
assert "EarlyLabel" in sample_tr.columns, "EarlyLabel missing"
assert len(train_ids & test_ids) == 0, "Patient leak"
print("  All checks PASSED")

joblib.dump(feature_cols, os.path.join(OUTPUT_DIR, "feature_cols.pkl"))

train_rows = sum(1 for _ in open(TRAIN_CSV, encoding="utf-8")) - 1
test_rows  = sum(1 for _ in open(TEST_CSV,  encoding="utf-8")) - 1

print("\n" + "=" * 60)
print("PHASE 1 COMPLETE")
print("=" * 60)
print(f"  train.csv        : {train_rows:,} rows")
print(f"  test.csv         : {test_rows:,} rows")
print(f"  Feature columns  : {len(feature_cols)}")
print(f"  scale_pos_weight : {ratio:.0f}  (use this in Phase 3)")
print(f"  Artifacts in     : {OUTPUT_DIR}/")
print("=" * 60)
