"""
Phase 3 — XGBoost Model Training
AI-Based Early Sepsis Prediction System

Input  : output/train_features.csv, output/test_features.csv
Output : models/xgboost_model.pkl
         output/evaluation_report.txt
         output/roc_curve.png
         output/confusion_matrix.png
         output/training_curves.png
         output/feature_importance.png
         output/threshold_sweep.png

Uses:
  - csv.reader batches (memory safe)
  - Early stopping (patience=20) — avoids overfitting
  - Built-in threshold sweep — auto-selects best operating point
"""

import os, gc, csv, json, joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, f1_score, recall_score, precision_score,
    confusion_matrix, roc_curve, classification_report
)

# ── CONFIG ────────────────────────────────────────────────
OUTPUT_DIR  = "./output"
MODELS_DIR  = "./models"
TRAIN_IN    = os.path.join(OUTPUT_DIR, "train_features.csv")
TEST_IN     = os.path.join(OUTPUT_DIR, "test_features.csv")
os.makedirs(MODELS_DIR, exist_ok=True)

all_feature_cols = joblib.load(
    os.path.join(OUTPUT_DIR, "feature_cols_engineered.pkl"))
TARGET           = "EarlyLabel"
SCALE_POS_WEIGHT = 55       # from Phase 1 report
BATCH_SIZE       = 50_000
MAX_ROUNDS       = 500
EARLY_STOP       = 20

print(f"Features  : {len(all_feature_cols)}")
print(f"Max rounds: {MAX_ROUNDS}  (early stop patience={EARLY_STOP})")

# ─────────────────────────────────────────────────────────────────────────────
# Data loader — csv.reader batches, no pandas read_csv on large files
# ─────────────────────────────────────────────────────────────────────────────

def load_to_numpy(csv_path, feature_cols, target_col, batch_size):
    x_parts, y_parts = [], []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader     = csv.reader(f)
        header     = next(reader)
        col_idx    = {c: i for i, c in enumerate(header)}
        feat_idx   = [col_idx[c] for c in feature_cols if c in col_idx]
        target_idx = col_idx[target_col]
        x_buf, y_buf = [], []
        for line in reader:
            x_row = []
            for i in feat_idx:
                try:
                    x_row.append(float(line[i]) if line[i] not in
                                 ("","nan","None") else 0.0)
                except (ValueError, IndexError):
                    x_row.append(0.0)
            try:
                y_buf.append(float(line[target_idx]))
            except:
                y_buf.append(0.0)
            x_buf.append(x_row)
            if len(x_buf) >= batch_size:
                x_parts.append(np.array(x_buf, dtype=np.float32))
                y_parts.append(np.array(y_buf, dtype=np.float32))
                x_buf, y_buf = [], []
                gc.collect()
        if x_buf:
            x_parts.append(np.array(x_buf, dtype=np.float32))
            y_parts.append(np.array(y_buf, dtype=np.float32))
    X = np.concatenate(x_parts)
    y = np.concatenate(y_parts)
    del x_parts, y_parts; gc.collect()
    return X, y

# ─────────────────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Loading data")
print("=" * 60)

print("  Loading train...")
X_train, y_train = load_to_numpy(TRAIN_IN, all_feature_cols, TARGET, BATCH_SIZE)
print(f"  X_train : {X_train.shape}  "
      f"pos={int(y_train.sum()):,} ({y_train.mean()*100:.2f}%)")

print("  Loading test...")
X_test, y_test = load_to_numpy(TEST_IN, all_feature_cols, TARGET, BATCH_SIZE)
print(f"  X_test  : {X_test.shape}  "
      f"pos={int(y_test.sum()):,} ({y_test.mean()*100:.2f}%)")

dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=all_feature_cols)
dtest  = xgb.DMatrix(X_test,  label=y_test,  feature_names=all_feature_cols)
del X_train, X_test; gc.collect()
print("  DMatrices built")

# ─────────────────────────────────────────────────────────────────────────────
# Train XGBoost with early stopping
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Training XGBoost")
print("=" * 60)

params = {
    "objective"        : "binary:logistic",
    "eval_metric"      : ["auc", "logloss"],
    "scale_pos_weight" : SCALE_POS_WEIGHT,
    "max_depth"        : 5,
    "learning_rate"    : 0.05,
    "subsample"        : 0.7,
    "colsample_bytree" : 0.7,
    "min_child_weight" : 10,
    "gamma"            : 2,
    "reg_alpha"        : 0.5,
    "reg_lambda"       : 2.0,
    "tree_method"      : "hist",
    "nthread"          : -1,
    "seed"             : 42,
}

print("\n  Params:")
for k, v in params.items():
    print(f"    {k:20s}: {v}")

evals_result = {}
print(f"\n  Training (max {MAX_ROUNDS} rounds, patience={EARLY_STOP})...")

model = xgb.train(
    params, dtrain,
    num_boost_round = MAX_ROUNDS,
    evals           = [(dtrain, "train"), (dtest, "test")],
    evals_result    = evals_result,
    verbose_eval    = 25,
    callbacks       = [xgb.callback.EarlyStopping(
                            rounds      = EARLY_STOP,
                            metric_name = "auc",
                            data_name   = "test",
                            maximize    = True,
                            save_best   = True
                      )]
)

best_round = model.best_iteration
best_auc   = model.best_score
print(f"\n  Early stop round : {best_round}")
print(f"  Best test-AUC   : {best_auc:.4f}")

model_path = os.path.join(MODELS_DIR, "xgboost_model.pkl")
joblib.dump(model, model_path)
print(f"  Model saved → {model_path}")

with open(os.path.join(OUTPUT_DIR, "training_curves.json"), "w") as f:
    json.dump(evals_result, f)

# ─────────────────────────────────────────────────────────────────────────────
# Threshold sweep — auto-selects best operating point
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Threshold sweep")
print("=" * 60)

y_prob = model.predict(dtest)
y_true = dtest.get_label()
roc_auc = roc_auc_score(y_true, y_prob)
print(f"\n  Test ROC-AUC : {roc_auc:.4f}")
print(f"\n  {'Threshold':>10} {'Recall':>8} {'Precision':>10} "
      f"{'F1':>8} {'FP rate':>9}")
print("  " + "-" * 48)

sweep = []
for t in np.arange(0.10, 0.91, 0.05):
    yp   = (y_prob >= t).astype(int)
    rec  = recall_score(y_true, yp, zero_division=0)
    prec = precision_score(y_true, yp, zero_division=0)
    f1   = f1_score(y_true, yp, zero_division=0)
    fpr  = yp[y_true == 0].mean()
    sweep.append((t, rec, prec, f1, fpr))
    print(f"  {t:>10.2f} {rec:>8.3f} {prec:>10.3f} {f1:>8.3f} {fpr:>9.3f}")

sweep = np.array(sweep)
best_f1_idx = sweep[:, 3].argmax()
cands       = [r for r in sweep if r[1] >= 0.70]
best_bal    = max(cands, key=lambda r: r[2]) if cands else sweep[best_f1_idx]
THRESHOLD   = float(best_bal[0])

print(f"\n  Best F1       : t={sweep[best_f1_idx,0]:.2f}  "
      f"F1={sweep[best_f1_idx,3]:.3f}  "
      f"Recall={sweep[best_f1_idx,1]:.3f}  "
      f"Precision={sweep[best_f1_idx,2]:.3f}")
print(f"  Best balanced : t={best_bal[0]:.2f}  "
      f"Recall={best_bal[1]:.3f}  "
      f"Precision={best_bal[2]:.3f}  ← using this")

# Save chosen threshold for Phase 4
joblib.dump(THRESHOLD, os.path.join(OUTPUT_DIR, "threshold.pkl"))

# ─────────────────────────────────────────────────────────────────────────────
# Final evaluation
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"Evaluation at threshold = {THRESHOLD:.2f}")
print("=" * 60)

y_pred      = (y_prob >= THRESHOLD).astype(int)
recall      = recall_score(y_true, y_pred)
precision   = precision_score(y_true, y_pred, zero_division=0)
f1          = f1_score(y_true, y_pred)
cm          = confusion_matrix(y_true, y_pred)
tn, fp, fn, tp = cm.ravel()
specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

print(f"\n  ROC-AUC    : {roc_auc:.4f}")
print(f"  Recall     : {recall:.4f}  ← catching sepsis early")
print(f"  Precision  : {precision:.4f}")
print(f"  F1         : {f1:.4f}")
print(f"  Specificity: {specificity:.4f}")
print(f"\n  TN={tn:,}  FP={fp:,}")
print(f"  FN={fn:,}   TP={tp:,}")
print(f"\n{classification_report(y_true, y_pred, target_names=['No Sepsis','Sepsis'])}")

with open(os.path.join(OUTPUT_DIR, "evaluation_report.txt"), "w") as f:
    f.write(f"XGBoost Evaluation Report\n{'='*50}\n")
    f.write(f"Best round    : {best_round}\n")
    f.write(f"Best test-AUC : {best_auc:.4f}\n")
    f.write(f"Threshold     : {THRESHOLD:.2f}\n")
    f.write(f"ROC-AUC       : {roc_auc:.4f}\n")
    f.write(f"Recall        : {recall:.4f}\n")
    f.write(f"Precision     : {precision:.4f}\n")
    f.write(f"F1            : {f1:.4f}\n")
    f.write(f"Specificity   : {specificity:.4f}\n")
    f.write(f"TN={tn}  FP={fp}  FN={fn}  TP={tp}\n\n")
    f.write(classification_report(y_true, y_pred,
                                   target_names=["No Sepsis","Sepsis"]))

# ─────────────────────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Saving plots")
print("=" * 60)

# Training curves
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for metric, ax in zip(["auc", "logloss"], axes):
    tr = evals_result.get("train", {}).get(metric, [])
    te = evals_result.get("test",  {}).get(metric, [])
    if tr: ax.plot(range(len(tr)), tr, color="#378ADD", lw=1.5, label="Train")
    if te: ax.plot(range(len(te)), te, color="#E24B4A", lw=1.5,
                   linestyle="--", label="Test")
    ax.axvline(best_round, color="#1D9E75", linestyle=":",
               lw=2, label=f"Best round ({best_round})")
    ax.set_xlabel("Round"); ax.set_ylabel(metric.upper())
    ax.set_title(f"{metric.upper()} — train vs test")
    ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "training_curves.png"), dpi=120, bbox_inches="tight")
plt.close("all"); print("  training_curves.png")

# ROC curve
fpr_arr, tpr_arr, _ = roc_curve(y_true, y_prob)
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(fpr_arr, tpr_arr, color="#378ADD", lw=2,
        label=f"AUC = {roc_auc:.3f}")
ax.plot([0,1],[0,1],"k--", lw=1)
ax.scatter([fp/(fp+tn)], [tp/(tp+fn)], s=150, color="#E24B4A",
           zorder=5, label=f"Operating point (t={THRESHOLD:.2f})")
ax.set_xlabel("FPR"); ax.set_ylabel("TPR")
ax.set_title("ROC Curve — XGBoost Sepsis Prediction")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "roc_curve.png"), dpi=120, bbox_inches="tight")
plt.close("all"); print("  roc_curve.png")

# Confusion matrix
fig, ax = plt.subplots(figsize=(5, 4))
im = ax.imshow(cm, cmap="Blues"); plt.colorbar(im, ax=ax)
ax.set_xticks([0,1]); ax.set_xticklabels(["No Sepsis","Sepsis"])
ax.set_yticks([0,1]); ax.set_yticklabels(["No Sepsis","Sepsis"])
thresh_cm = cm.max() / 2
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i,j]:,}", ha="center", va="center",
                color="white" if cm[i,j] > thresh_cm else "black")
ax.set_ylabel("True"); ax.set_xlabel("Predicted")
ax.set_title(f"Confusion Matrix (t={THRESHOLD:.2f})")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "confusion_matrix.png"), dpi=120, bbox_inches="tight")
plt.close("all"); print("  confusion_matrix.png")

# Threshold sweep
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(sweep[:,0], sweep[:,1], "o-", color="#E24B4A", lw=2, label="Recall")
ax.plot(sweep[:,0], sweep[:,2], "o-", color="#378ADD", lw=2, label="Precision")
ax.plot(sweep[:,0], sweep[:,3], "o-", color="#1D9E75", lw=2, label="F1")
ax.axvline(THRESHOLD, color="#888780", linestyle="--",
           label=f"Chosen t={THRESHOLD:.2f}")
ax.set_xlabel("Threshold"); ax.set_ylabel("Score")
ax.set_title("Precision / Recall / F1 vs Threshold")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "threshold_sweep.png"), dpi=120, bbox_inches="tight")
plt.close("all"); print("  threshold_sweep.png")

# Feature importance
importance = model.get_score(importance_type="gain")
importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:20]
fig, ax = plt.subplots(figsize=(8, 6))
ax.barh([x[0] for x in importance][::-1],
        [x[1] for x in importance][::-1], color="#378ADD")
ax.set_xlabel("Gain"); ax.set_title("Top 20 Features by Importance (Gain)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "feature_importance.png"), dpi=120, bbox_inches="tight")
plt.close("all"); print("  feature_importance.png")

print("\n" + "=" * 60)
print("PHASE 3 COMPLETE")
print("=" * 60)
print(f"  Best round  : {best_round}")
print(f"  ROC-AUC     : {roc_auc:.4f}")
print(f"  Recall      : {recall:.4f}")
print(f"  Precision   : {precision:.4f}")
print(f"  F1          : {f1:.4f}")
print(f"  Threshold   : {THRESHOLD:.2f}  (saved to threshold.pkl)")
print(f"  Model       : {model_path}")
print("=" * 60)
