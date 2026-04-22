"""
ml_model.py — XGBoost model loader and hybrid predictor.

Loads xgboost_model.pkl (PhysioNet 2019, 68 features, AUC=0.80) on startup.

DESIGN NOTE — Hybrid scoring:
  The model was trained on PhysioNet time-series (rolling means, deltas, etc.)
  We only have a single vital snapshot, so the raw XGBoost output is compressed
  into a narrow low-probability band (~0.05-0.12). To get a clinically useful
  0-1 range we use a calibrated hybrid:

    final = 0.60 x formula_score  +  0.40 x xgb_calibrated

  Where xgb_calibrated = min(1, xgb_raw / 0.13) re-scales the model's output
  to span 0-1 relative to its observed maximum on snapshot inputs.
  This preserves the XGBoost model's *rank ordering* of patients while the
  formula anchors the absolute severity level.
"""

import os
import warnings
import numpy as np
import joblib
import xgboost as xgb

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_BASE, "Sepsis-Prediction", "xgboost_model.pkl")

# XGBoost's empirical max output on single-snapshot inputs (observed: ~0.12)
_XGB_SNAPSHOT_MAX = 0.13

# ── Load once at import time ───────────────────────────────────────────────────
_model: xgb.Booster | None = None


def _load_model() -> xgb.Booster:
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"XGBoost model not found at: {MODEL_PATH}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _model = joblib.load(MODEL_PATH)
        print(f"[ML] XGBoost model loaded — {len(_model.feature_names)} features")
    return _model


# ── Feature builder ────────────────────────────────────────────────────────────
# Model expects exactly 68 features in this order:
#  [0]  HR       [1]  O2Sat    [2]  Temp     [3]  SBP
#  [4]  MAP      [5]  DBP      [6]  Resp     [7]  Glucose
#  [8]  Age      [9]  Gender   [10] Unit1    [11] Unit2    [12] HospAdmTime
#  [13-18]  HR rolling    (mean3, std3, mean6, std6, delta1, delta2)
#  [19-24]  O2Sat rolling
#  [25-30]  Temp rolling
#  [31-36]  SBP rolling
#  [37-42]  MAP rolling
#  [43-48]  DBP rolling
#  [49-54]  Resp rolling
#  [55-60]  Glucose rolling
#  [61] flag_MAP_low   [62] flag_HR_high  [63] flag_RR_high
#  [64] flag_SBP_low   [65] flag_O2_low
#  [66] shock_index    [67] flag_hemo_instability

def _build_feature_vector(
    hr: float, spo2: float, temp: float, sbp: float,
    map_: float, dbp: float, rr: float, glucose: float,
    age: int, gender: str, unit: str, hosp_adm_time: float = 12.0,
) -> np.ndarray:
    """
    Build the 68-feature vector for the XGBoost model.
    For rolling/delta features we use the current value as a proxy
    (std=0, delta=0) since we only have a single snapshot.
    """
    gender_num = 1.0 if gender.upper() == "M" else 0.0

    unit_upper = unit.upper()
    unit1 = 1.0 if "MICU" in unit_upper else 0.0
    unit2 = 1.0 if ("CCU" in unit_upper or "SICU" in unit_upper) else 0.0

    flag_map_low   = 1.0 if map_  < 65  else 0.0
    flag_hr_high   = 1.0 if hr    > 100 else 0.0
    flag_rr_high   = 1.0 if rr    > 22  else 0.0
    flag_sbp_low   = 1.0 if sbp   < 90  else 0.0
    flag_o2_low    = 1.0 if spo2  < 94  else 0.0
    flag_hemo_inst = 1.0 if (map_ < 65 and hr > 100) else 0.0
    shock_index    = float(np.clip(hr / max(sbp, 1.0), 0.0, 5.0))

    def rolling(val: float):
        """[mean3, std3, mean6, std6, delta1, delta2] — single snapshot proxy."""
        return [val, 0.0, val, 0.0, 0.0, 0.0]

    features = [
        # Base vitals (0-12)
        hr, spo2, temp, sbp, map_, dbp, rr, glucose,
        float(age), gender_num, unit1, unit2, hosp_adm_time,
        # Rolling stats per vital (13-60)
        *rolling(hr),
        *rolling(spo2),
        *rolling(temp),
        *rolling(sbp),
        *rolling(map_),
        *rolling(dbp),
        *rolling(rr),
        *rolling(glucose),
        # Clinical flags (61-65)
        flag_map_low, flag_hr_high, flag_rr_high, flag_sbp_low, flag_o2_low,
        # Derived scores (66-67)
        shock_index, flag_hemo_inst,
    ]

    assert len(features) == 68, f"Expected 68 features, got {len(features)}"
    return np.array(features, dtype=np.float32).reshape(1, -1)


# ── Clinical formula — severity anchor ─────────────────────────────────────────

def _clinical_formula(
    hr: float, sbp: float, spo2: float,
    rr: float, temp: float, map_: float,
) -> float:
    """
    Weighted clinical formula — spans the full 0-1 severity range.
    Used as the primary signal in the hybrid score.
    """
    return min(1.0, max(0.0,
        0.25 * min(1, max(0, (hr   - 60) / 80)) +
        0.20 * min(1, max(0, (100  - sbp) / 50)) +
        0.20 * min(1, max(0, (100  - spo2) / 20)) +
        0.15 * min(1, max(0, (rr   - 12)  / 28)) +
        0.10 * min(1, max(0, (temp - 36)  /  5)) +
        0.10 * min(1, max(0, (70   - map_) / 30))
    ))


# ── Public API ─────────────────────────────────────────────────────────────────

def predict_sepsis_prob(
    hr: float, spo2: float, temp: float, sbp: float,
    map_: float, dbp: float, rr: float, glucose: float,
    age: int, gender: str, unit: str, hosp_adm_time: float = 12.0,
) -> float:
    """
    Hybrid XGBoost + clinical formula score.

    XGBoost provides learned feature interactions and relative rank ordering.
    Clinical formula anchors the result to a meaningful 0-1 severity range.

        final = 0.60 x formula  +  0.40 x xgb_calibrated

    Falls back to formula-only if the model cannot be loaded.
    """
    formula = _clinical_formula(hr, sbp, spo2, rr, temp, map_)

    try:
        model    = _load_model()
        feat     = _build_feature_vector(
            hr, spo2, temp, sbp, map_, dbp, rr, glucose,
            age, gender, unit, hosp_adm_time,
        )
        dmat     = xgb.DMatrix(feat, feature_names=model.feature_names)
        xgb_raw  = float(model.predict(dmat)[0])

        # Re-scale XGBoost to 0-1 relative to its snapshot-input ceiling
        xgb_cal  = min(1.0, xgb_raw / _XGB_SNAPSHOT_MAX)

        # Weighted blend
        hybrid   = 0.60 * formula + 0.40 * xgb_cal
        return round(min(1.0, max(0.0, hybrid)), 4)

    except Exception as e:
        print(f"[ML] Model inference failed ({e}), using clinical formula only")
        return round(formula, 4)


# ── Warm-up: load model eagerly at import time ─────────────────────────────────
try:
    _load_model()
except Exception as e:
    print(f"[ML] WARNING — Could not pre-load model: {e}")
