"""
ICU Patient Prioritization Dashboard — Sepsis Prediction System
Run: streamlit run src/dashboard.py
"""

import os, time, random, joblib, warnings
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import xgboost as xgb
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="ICU Sepsis Monitor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Dark clinical theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;background:#0a0e1a;color:#c8d0e7}
.stApp{background:#0a0e1a}
.main .block-container{padding:1.2rem 2rem 2rem;max-width:1600px}
.icu-header{background:linear-gradient(135deg,#0d1526 0%,#111c35 100%);border:1px solid #1e3a5f;border-radius:12px;padding:18px 28px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between}
.icu-title{font-size:22px;font-weight:600;color:#e2ecff;letter-spacing:.5px}
.icu-sub{font-size:12px;color:#5a7ba8;font-family:'IBM Plex Mono',monospace;margin-top:3px}
.sdot{width:9px;height:9px;background:#22c55e;border-radius:50%;display:inline-block;margin-right:6px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.alert-banner{background:linear-gradient(90deg,#2d0a0a,#1a0808);border:1px solid #ef4444;border-left:4px solid #ef4444;border-radius:8px;padding:12px 18px;margin-bottom:14px;font-size:13px;color:#fca5a5}
.alert-title{font-weight:600;color:#f87171}
.patient-table{width:100%;border-collapse:collapse}
.patient-table th{background:#0d1526;color:#5a7ba8;font-size:10px;text-transform:uppercase;letter-spacing:1.2px;padding:10px 14px;text-align:left;border-bottom:1px solid #1e3a5f;font-family:'IBM Plex Mono',monospace}
.patient-table td{padding:10px 14px;border-bottom:1px solid #111c35;font-size:13px;font-family:'IBM Plex Mono',monospace}
.row-high{border-left:3px solid #ef4444}
.row-medium{border-left:3px solid #f59e0b}
.row-low{border-left:3px solid #10b981}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:.5px}
.badge-high{background:rgba(239,68,68,.15);color:#f87171;border:1px solid #ef4444}
.badge-medium{background:rgba(245,158,11,.15);color:#fbbf24;border:1px solid #f59e0b}
.badge-low{background:rgba(16,185,129,.12);color:#34d399;border:1px solid #10b981}
.sbar-bg{background:#1e3a5f;border-radius:4px;height:6px;width:80px;display:inline-block;vertical-align:middle;margin-left:8px}
.detail-panel{background:#0d1526;border:1px solid #1e3a5f;border-radius:12px;padding:20px}
.detail-hdr{font-size:15px;font-weight:600;color:#e2ecff;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #1e3a5f;display:flex;justify-content:space-between;align-items:center}
.vital-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #111c35}
.vital-name{font-size:11px;color:#5a7ba8;text-transform:uppercase;letter-spacing:.8px}
.vital-val{font-size:16px;font-weight:600;font-family:'IBM Plex Mono',monospace}
.vital-unit{font-size:10px;color:#5a7ba8;margin-left:3px}
.sec-title{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#5a7ba8;margin:14px 0 8px;font-family:'IBM Plex Mono',monospace}
.feat-row{display:flex;align-items:center;gap:10px;margin:5px 0}
.feat-name{font-size:11px;color:#8ba4c8;width:145px;flex-shrink:0}
.feat-bg{flex:1;background:#1e3a5f;border-radius:3px;height:5px}
.feat-fill{height:5px;border-radius:3px}
.feat-val{font-size:11px;color:#60a5fa;font-family:'IBM Plex Mono',monospace;width:34px;text-align:right}
.time-badge{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#5a7ba8;background:#0d1526;border:1px solid #1e3a5f;border-radius:6px;padding:4px 10px}
.stTabs [data-baseweb="tab-list"]{background:#0d1526;border-radius:8px;gap:4px}
.stTabs [data-baseweb="tab"]{color:#5a7ba8;background:transparent;border-radius:6px;font-size:12px}
.stTabs [aria-selected="true"]{background:#1e3a5f !important;color:#e2ecff !important}
div[data-testid="stMetric"]{background:#0d1526;border:1px solid #1e3a5f;border-radius:10px;padding:12px 16px}
div[data-testid="stMetric"] label{color:#5a7ba8 !important;font-size:11px !important}
div[data-testid="stMetric"] div[data-testid="stMetricValue"]{color:#e2ecff !important;font-family:'IBM Plex Mono',monospace !important}
hr{border-color:#1e3a5f !important}
.stButton button{background:#1e3a5f !important;color:#e2ecff !important;border:1px solid #2e5a8f !important;border-radius:8px !important;font-size:12px !important}
.stButton button:hover{background:#2e5a8f !important}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS & LOAD MODEL
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BASE_DIR, "output")
MODEL_DIR = os.path.join(BASE_DIR, "models")

@st.cache_resource
def load_model():
    try:
        m  = joblib.load(os.path.join(MODEL_DIR, "xgboost_model.pkl"))
        fc = joblib.load(os.path.join(OUT_DIR,   "feature_cols_engineered.pkl"))
        im = joblib.load(os.path.join(OUT_DIR,   "imputation_means.pkl"))
        return m, fc, im, True
    except:
        return None, [], {}, False

model, feature_cols, imputation_means, model_loaded = load_model()

# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
VITAL_RANGES = {
    "HR":    (45,  160, 80,  12),
    "SBP":   (70,  200, 120, 15),
    "DBP":   (40,  130, 75,  10),
    "MAP":   (50,  140, 90,  12),
    "Temp":  (35.0,41.0,37.0,0.4),
    "SpO2":  (80,  100, 97,  1.5),
    "Resp":  (8,   40,  16,  3),
    "Glucose":(60, 400, 110, 20),
}
PATIENT_IDS = [f"ICU-{100+i:03d}" for i in range(20)]

def make_patients(n=20):
    patients = []
    for pid in PATIENT_IDS[:n]:
        sev = random.random()
        p   = {"patient_id": pid, "severity": sev, "age": random.randint(35,85),
               "gender": random.randint(0,1), "unit1": random.randint(0,1),
               "unit2": random.randint(0,1), "hosp_adm": -random.uniform(2,24),
               "hour": 1, "history": []}
        for v, (lo,hi,mn,sd) in VITAL_RANGES.items():
            drift = sev * 0.4
            if v in ("SBP","DBP","MAP","SpO2"):
                base = mn - drift*(mn-lo)*0.6
            else:
                base = mn + drift*(hi-mn)*0.5
            p[v] = float(np.clip(np.random.normal(base, sd), lo, hi))
        patients.append(p)
    return patients

def step_patient(p):
    sev = p["severity"]
    if random.random() < 0.05:
        p["severity"] = min(1.0, sev + random.uniform(0.05, 0.25))
    sev = p["severity"]
    u   = p.copy()
    u["hour"] = p["hour"] + 1
    for v, (lo,hi,mn,sd) in VITAL_RANGES.items():
        cur = p[v]
        tgt = (mn - sev*(mn-lo)*0.7) if v in ("SBP","DBP","MAP","SpO2") \
              else (mn + sev*(hi-mn)*0.6)
        u[v] = float(np.clip(cur + (tgt-cur)*0.15 + np.random.normal(0,sd*0.3), lo, hi))
    snap = {k: u[k] for k in list(VITAL_RANGES)+["hour"]}
    u["history"] = p["history"][-47:] + [snap]
    return u

def predict_prob(p):
    if model_loaded and model:
        try:
            hist = p.get("history",[]) or []
            df   = pd.DataFrame(hist + [{k: p[k] for k in VITAL_RANGES}])
            for col in VITAL_RANGES:
                df[col] = pd.to_numeric(df[col], errors="coerce").ffill().fillna(
                    imputation_means.get(col,0))
                s = df[col]
                for w in [3,6]:
                    df[f"{col}_mean{w}"] = s.rolling(w,min_periods=1).mean()
                    df[f"{col}_std{w}"]  = s.rolling(w,min_periods=1).std().fillna(0)
                df[f"{col}_delta1"] = s.diff(1).fillna(0)
                df[f"{col}_delta2"] = s.diff(2).fillna(0)
            df["flag_MAP_low"] = (df["MAP"]<65).astype(int)
            df["flag_HR_high"] = (df["HR"]>100).astype(int)
            df["flag_RR_high"] = (df["Resp"]>22).astype(int)
            df["flag_SBP_low"] = (df["SBP"]<90).astype(int)
            df["flag_O2_low"]  = (df["SpO2"]<94).astype(int)
            df["shock_index"]  = (df["HR"]/(df["SBP"].replace(0,np.nan))).fillna(0).clip(upper=5)
            df["flag_hemo_instability"] = ((df["MAP"]<65)&(df["HR"]>100)).astype(int)
            df["Age"]=p["age"]; df["Gender"]=p["gender"]
            df["Unit1"]=p["unit1"]; df["Unit2"]=p["unit2"]
            df["HospAdmTime"]=p["hosp_adm"]
            last = df.iloc[-1]
            vec  = []
            for c in feature_cols:
                try:
                    v2 = float(last[c]) if c in last.index else 0.0
                    vec.append(0.0 if pd.isna(v2) else v2)
                except:
                    vec.append(0.0)
            dmat = xgb.DMatrix(np.array(vec,dtype=np.float32).reshape(1,-1),
                               feature_names=feature_cols)
            return float(model.predict(dmat)[0])
        except:
            pass
    # Fallback clinical formula
    hr=p["HR"]; sbp=p["SBP"]; map_=p["MAP"]
    spo2=p["SpO2"]; resp=p["Resp"]; temp=p["Temp"]
    s = (0.25*min(1,max(0,(hr-60)/80)) +
         0.20*min(1,max(0,(100-sbp)/50)) +
         0.20*min(1,max(0,(100-spo2)/20)) +
         0.15*min(1,max(0,(resp-12)/28)) +
         0.10*min(1,max(0,(temp-36)/5)) +
         0.10*min(1,max(0,(70-map_)/30)))
    return float(np.clip(s + random.uniform(-0.04,0.04), 0, 1))

def priority_score(prob, p):
    hr_r = 1.0 if p["HR"]>100 else 0.0
    bp_r = min(1.0, (1.0 if p["MAP"]<65 else 0.0)+(0.5 if p["SBP"]<90 else 0.0))
    return float(np.clip(0.6*prob + 0.2*hr_r + 0.2*bp_r, 0, 1))

def risk_label(score):
    return "High" if score>0.80 else "Medium" if score>0.50 else "Low"

def get_alerts(p, prob):
    a = []
    if prob>0.85: a.append(("critical","Sepsis prob > 85%"))
    if p["SBP"]<90:   a.append(("high",f"Low SBP: {p['SBP']:.0f} mmHg"))
    if p["MAP"]<65:   a.append(("high",f"Low MAP: {p['MAP']:.0f} mmHg"))
    if p["SpO2"]<92:  a.append(("high",f"Critical SpO₂: {p['SpO2']:.1f}%"))
    if p["HR"]>130:   a.append(("medium",f"Tachycardia: {p['HR']:.0f} bpm"))
    if p["Temp"]>39.5:a.append(("medium",f"Fever: {p['Temp']:.1f}°C"))
    if p["Resp"]>30:  a.append(("medium",f"Tachypnoea: RR {p['Resp']:.0f}"))
    return a

def feature_contribs(p):
    items = {
        "Heart rate"       : min(1,max(0,(p["HR"]-60)/80)),
        "Blood pressure"   : min(1,max(0,(100-p["SBP"])/50)),
        "SpO₂"            : min(1,max(0,(100-p["SpO2"])/20)),
        "Respiratory rate" : min(1,max(0,(p["Resp"]-12)/28)),
        "Temperature"      : min(1,max(0,(p["Temp"]-36)/5)),
        "MAP"              : min(1,max(0,(70-p["MAP"])/30)),
    }
    return sorted(items.items(), key=lambda x: x[1], reverse=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "patients"      not in st.session_state: st.session_state.patients = make_patients(20)
if "selected_pid"  not in st.session_state: st.session_state.selected_pid = PATIENT_IDS[0]
if "auto_refresh"  not in st.session_state: st.session_state.auto_refresh = False
if "refresh_count" not in st.session_state: st.session_state.refresh_count = 0
if "sim_speed"     not in st.session_state: st.session_state.sim_speed = 3

# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL SCORES
# ─────────────────────────────────────────────────────────────────────────────
rows = []
for p in st.session_state.patients:
    prob = predict_prob(p)
    pri  = priority_score(prob, p)
    risk = risk_label(pri)
    rows.append({
        "patient": p, "pid": p["patient_id"],
        "HR": p["HR"], "SBP": p["SBP"], "MAP": p["MAP"],
        "Temp": p["Temp"], "SpO2": p["SpO2"], "Resp": p["Resp"],
        "prob": prob, "priority": pri, "risk": risk,
        "alerts": get_alerts(p, prob), "hour": p["hour"],
    })
df = pd.DataFrame(rows).sort_values("priority", ascending=False).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
now_str  = pd.Timestamp.now().strftime("%Y-%m-%d  %H:%M:%S")
hour_max = max(p["hour"] for p in st.session_state.patients)
mode_str = "MODEL ONLINE" if model_loaded else "FALLBACK MODE"

st.markdown(f"""
<div class="icu-header">
  <div>
    <div class="icu-title">🏥 ICU Sepsis Monitoring System</div>
    <div class="icu-sub">
      <span class="sdot"></span>
      LIVE &nbsp;·&nbsp; {len(df)} patients &nbsp;·&nbsp; Hour {hour_max} &nbsp;·&nbsp; {mode_str}
    </div>
  </div>
  <div style="text-align:right">
    <div class="time-badge">{now_str}</div>
    <div style="font-size:10px;color:#5a7ba8;margin-top:4px;
                font-family:'IBM Plex Mono',monospace">
      Cycle #{st.session_state.refresh_count}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ALERT BANNER
# ─────────────────────────────────────────────────────────────────────────────
crits = [(r["pid"], a[1]) for _, r in df.iterrows()
         for a in r["alerts"] if a[0] == "critical"]
if crits:
    msg = " &nbsp;|&nbsp; ".join(
        f"<b>{pid}</b>: {m}" for pid, m in crits[:4])
    st.markdown(f"""
    <div class="alert-banner">
      <span class="alert-title">⚠ CRITICAL ALERT &nbsp;</span>{msg}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# METRIC CARDS
# ─────────────────────────────────────────────────────────────────────────────
n_hi  = int((df["risk"]=="High").sum())
n_med = int((df["risk"]=="Medium").sum())
n_lo  = int((df["risk"]=="Low").sum())
n_alr = int(df["alerts"].apply(len).sum())

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("Total Patients",  len(df))
c2.metric("🔴 High Risk",    n_hi)
c3.metric("🟡 Medium Risk",  n_med)
c4.metric("🟢 Low Risk",     n_lo)
c5.metric("⚠ Active Alerts", n_alr)
c6.metric("ICU Hour",        hour_max)

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONTROLS
# ─────────────────────────────────────────────────────────────────────────────
ct1,ct2,ct3,ct4,ct5 = st.columns([2,2,1,1,2])
with ct1:
    risk_filter = st.multiselect("Risk", ["High","Medium","Low"],
        default=["High","Medium","Low"], label_visibility="collapsed")
with ct2:
    sort_by = st.selectbox("Sort",
        ["Priority Score","Sepsis Prob","Heart Rate","Temperature"],
        label_visibility="collapsed")
with ct3:
    n_show = st.selectbox("Show",[10,15,20],index=2,
                           label_visibility="collapsed")
with ct4:
    st.session_state.sim_speed = st.selectbox(
        "Speed",[1,2,3,5],index=2,label_visibility="collapsed")
with ct5:
    b1,b2,b3 = st.columns(3)
    with b1:
        if st.button(
            "▶ Start" if not st.session_state.auto_refresh else "⏸ Pause",
            use_container_width=True):
            st.session_state.auto_refresh = not st.session_state.auto_refresh
            st.rerun()
    with b2:
        if st.button("⏭ Step", use_container_width=True):
            st.session_state.patients = [step_patient(p)
                for p in st.session_state.patients]
            st.session_state.refresh_count += 1
            st.rerun()
    with b3:
        if st.button("↺ Reset", use_container_width=True):
            st.session_state.patients = make_patients(20)
            st.session_state.refresh_count = 0
            st.session_state.auto_refresh  = False
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
left_col, right_col = st.columns([3, 1.6], gap="medium")

# ── Filter & sort ─────────────────────────────────────────
sort_map = {"Priority Score":"priority","Sepsis Prob":"prob",
            "Heart Rate":"HR","Temperature":"Temp"}
df_show  = (df[df["risk"].isin(risk_filter)] if risk_filter else df) \
           .sort_values(sort_map[sort_by], ascending=False).head(n_show)

# ── Patient Table ─────────────────────────────────────────
with left_col:
    st.markdown("<div class='sec-title'>Patient Rankings</div>",
                unsafe_allow_html=True)

    tbody = ""
    for rank, (_, row) in enumerate(df_show.iterrows(), 1):
        risk    = row["risk"]
        prob    = row["prob"]
        pri     = row["priority"]
        n_alrts = len(row["alerts"])
        is_sel  = row["pid"] == st.session_state.selected_pid
        is_crit = risk=="High" and prob>0.85

        sel_bg  = "background:#111c35;" if is_sel else ""
        crit_bg = "background:rgba(239,68,68,0.06);" if is_crit else ""
        rk_html = f'<b style="color:#ef4444">{rank}</b>' if rank<=3 else str(rank)
        bc      = "#ef4444" if risk=="High" else "#f59e0b" if risk=="Medium" else "#10b981"
        alrt_h  = (f'<span style="color:#f87171;font-size:11px">⚠ {n_alrts}</span>'
                   if n_alrts else '<span style="color:#1e3a5f">—</span>')

        tbody += f"""<tr class="row-{risk.lower()}" style="{sel_bg}{crit_bg}">
          <td>{rk_html}</td>
          <td style="color:#e2ecff;font-weight:600">{row['pid']}</td>
          <td>{'<span style="color:#f87171">' if row['HR']>100 else ''}{row['HR']:.0f}{'</span>' if row['HR']>100 else ''} <span style="color:#5a7ba8;font-size:10px">bpm</span></td>
          <td>{'<span style="color:#f87171">' if row['SBP']<90 else ''}{row['SBP']:.0f}{'</span>' if row['SBP']<90 else ''}/{row['MAP']:.0f} <span style="color:#5a7ba8;font-size:10px">mmHg</span></td>
          <td>{'<span style="color:#f87171">' if row['Temp']>38.3 or row['Temp']<36 else ''}{row['Temp']:.1f}°C{'</span>' if row['Temp']>38.3 or row['Temp']<36 else ''}</td>
          <td>{'<span style="color:#f87171">' if row['SpO2']<94 else ''}{row['SpO2']:.1f}%{'</span>' if row['SpO2']<94 else ''}</td>
          <td>
            <span style="color:{'#ef4444' if prob>0.8 else '#fbbf24' if prob>0.5 else '#34d399'};font-weight:600">{prob:.2f}</span>
            <div class="sbar-bg"><div style="width:{int(prob*100)}%;height:6px;border-radius:4px;background:{bc}"></div></div>
          </td>
          <td><span class="badge badge-{risk.lower()}">{risk}</span></td>
          <td>{alrt_h}</td>
        </tr>"""

    st.markdown(f"""
    <div style="background:#0d1526;border:1px solid #1e3a5f;border-radius:10px;overflow:hidden">
      <table class="patient-table">
        <thead><tr>
          <th>#</th><th>Patient ID</th><th>Heart Rate</th><th>BP / MAP</th>
          <th>Temp</th><th>SpO₂</th><th>Sepsis Risk</th><th>Priority</th><th>Alerts</th>
        </tr></thead>
        <tbody>{tbody}</tbody>
      </table>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    pid_opts = df_show["pid"].tolist()
    sel = st.selectbox("Select patient for detail view", pid_opts,
        index=0 if st.session_state.selected_pid not in pid_opts
              else pid_opts.index(st.session_state.selected_pid))
    if sel != st.session_state.selected_pid:
        st.session_state.selected_pid = sel
        st.rerun()

# ── Detail Panel ──────────────────────────────────────────
with right_col:
    sr   = df[df["pid"]==st.session_state.selected_pid]
    if sr.empty: sr = df.iloc[[0]]
    sr   = sr.iloc[0]
    sp   = sr["patient"]
    rc   = "#ef4444" if sr["risk"]=="High" else "#f59e0b" if sr["risk"]=="Medium" else "#10b981"

    st.markdown(f"""
    <div class="detail-panel">
      <div class="detail-hdr">
        <div>
          <span style="color:#e2ecff;font-size:16px;font-weight:600">{sr['pid']}</span>
          <div style="font-size:11px;color:#5a7ba8;font-family:'IBM Plex Mono',monospace;margin-top:2px">
            Hour {sp['hour']} · Age {sp['age']} · {"Male" if sp["gender"] else "Female"}
          </div>
        </div>
        <span class="badge badge-{sr['risk'].lower()}">{sr['risk']}</span>
      </div>

      <div style="display:flex;gap:10px;margin-bottom:14px">
        <div style="flex:1;background:#111c35;border-radius:8px;padding:10px;text-align:center">
          <div style="font-size:22px;font-weight:700;color:{rc};font-family:'IBM Plex Mono',monospace">{sr['prob']:.0%}</div>
          <div style="font-size:10px;color:#5a7ba8;text-transform:uppercase;letter-spacing:.8px;margin-top:2px">Sepsis Prob</div>
        </div>
        <div style="flex:1;background:#111c35;border-radius:8px;padding:10px;text-align:center">
          <div style="font-size:22px;font-weight:700;color:{rc};font-family:'IBM Plex Mono',monospace">{sr['priority']:.2f}</div>
          <div style="font-size:10px;color:#5a7ba8;text-transform:uppercase;letter-spacing:.8px;margin-top:2px">Priority</div>
        </div>
      </div>

      <div class="sec-title">Current Vitals</div>
    """, unsafe_allow_html=True)

    vitals_meta = [
        ("Heart Rate", sp["HR"],   "bpm",  60,  100),
        ("SBP",        sp["SBP"],  "mmHg", 90,  140),
        ("MAP",        sp["MAP"],  "mmHg", 65,  100),
        ("Temperature",sp["Temp"],"°C",   36,  38.3),
        ("SpO₂",      sp["SpO2"],"%",    94,  100),
        ("Resp Rate",  sp["Resp"],"br/m", 12,  20),
        ("Glucose",    sp["Glucose"],"mg/dL",70,180),
    ]

    vh = ""
    for nm, val, unit, lo_n, hi_n in vitals_meta:
        abn   = val<lo_n or val>hi_n
        vc    = "#f87171" if abn else "#34d399"
        arrow = "↑" if val>hi_n else "↓" if val<lo_n else ""
        vh += f"""<div class="vital-row">
          <span class="vital-name">{nm}</span>
          <span>
            <span class="vital-val" style="color:{vc}">{val:.1f}</span>
            <span class="vital-unit">{unit}</span>
            <span style="color:{vc};font-size:11px;margin-left:3px">{arrow}</span>
          </span>
        </div>"""
    st.markdown(vh, unsafe_allow_html=True)

    if sr["alerts"]:
        ah = '<div class="sec-title" style="margin-top:12px">Active Alerts</div>'
        for sev, msg in sr["alerts"]:
            ac = "#ef4444" if sev=="critical" else "#f59e0b"
            ah += f"""<div style="background:rgba({'239,68,68' if sev=='critical' else '245,158,11'},.1);
                       border-left:3px solid {ac};border-radius:0 6px 6px 0;
                       padding:6px 10px;margin:4px 0;font-size:12px;color:{ac}">⚠ {msg}</div>"""
        st.markdown(ah, unsafe_allow_html=True)

    contribs = feature_contribs(sp)
    mx = max(v for _,v in contribs) or 1
    fh = '<div class="sec-title" style="margin-top:12px">Top Risk Factors</div>'
    for fname, fval in contribs:
        pct = fval / mx
        bc  = "#ef4444" if pct>0.7 else "#f59e0b" if pct>0.4 else "#3b82f6"
        fh += f"""<div class="feat-row">
          <span class="feat-name">{fname}</span>
          <div class="feat-bg"><div class="feat-fill" style="width:{int(pct*100)}%;background:{bc}"></div></div>
          <span class="feat-val">{fval:.2f}</span>
        </div>"""
    st.markdown(fh + "</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS — Charts / Risk Trend / Manual Predict
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📈 Vitals History", "🔬 Risk Trend", "🔬 Manual Prediction"])

with tab1:
    history = sp.get("history",[])
    if len(history) < 2:
        st.info("Step the simulation forward to build vitals history.")
    else:
        hdf  = pd.DataFrame(history)
        cols = [c for c in ["HR","SBP","MAP","Temp","SpO2","Resp"] if c in hdf.columns]
        vmeta = {
            "HR":  ("#60a5fa",[60,100],"bpm"),
            "SBP": ("#a78bfa",[90,140],"mmHg"),
            "MAP": ("#34d399",[65,100],"mmHg"),
            "Temp":("#f59e0b",[36,38.3],"°C"),
            "SpO2":("#22d3ee",[94,100],"%"),
            "Resp":("#f87171",[12,20],"br/m"),
        }
        fig, axes = plt.subplots(2,3,figsize=(13,5))
        fig.patch.set_facecolor("#0a0e1a")
        axes = axes.flatten()
        for i,(col,ax) in enumerate(zip(cols[:6],axes)):
            clr,nrng,unit = vmeta.get(col,("#60a5fa",[0,100],""))
            ax.set_facecolor("#0d1526")
            for sp2 in ax.spines.values(): sp2.set_edgecolor("#1e3a5f")
            vals  = pd.to_numeric(hdf[col],errors="coerce")
            hrs   = hdf["hour"] if "hour" in hdf.columns else range(len(vals))
            ax.plot(hrs,vals,color=clr,lw=2,zorder=3)
            ax.fill_between(hrs,vals,alpha=0.12,color=clr)
            ax.axhspan(nrng[0],nrng[1],alpha=0.08,color="#10b981")
            ax.set_title(f"{col} ({unit})",color="#8ba4c8",fontsize=10,fontfamily="monospace")
            ax.tick_params(colors="#5a7ba8",labelsize=8)
            ax.grid(color="#1e3a5f",alpha=0.5)
        for j in range(len(cols),len(axes)): axes[j].set_visible(False)
        plt.tight_layout(pad=1.2)
        st.pyplot(fig, use_container_width=True)
        plt.close()

with tab2:
    history = sp.get("history",[])
    if len(history) < 2:
        st.info("Step the simulation forward to build risk trend.")
    else:
        prob_hist = []
        for i in range(1, len(history)+1):
            snap = dict(history[i-1])
            snap.update({k: sp[k] for k in ["age","gender","unit1","unit2","hosp_adm"]})
            snap["history"] = history[:i-1]
            prob_hist.append(predict_prob(snap))
        hrs = [h.get("hour",i+1) for i,h in enumerate(history)]

        fig, ax = plt.subplots(figsize=(13,3.5))
        fig.patch.set_facecolor("#0a0e1a")
        ax.set_facecolor("#0d1526")
        for sp2 in ax.spines.values(): sp2.set_edgecolor("#1e3a5f")
        ax.plot(hrs, prob_hist, color="#ef4444", lw=2.5, zorder=4)
        ax.fill_between(hrs, prob_hist, alpha=0.15, color="#ef4444")
        ax.axhline(0.85, color="#ef4444", linestyle="--", alpha=0.6, lw=1.5,
                   label="Critical (0.85)")
        ax.axhline(0.50, color="#f59e0b", linestyle="--", alpha=0.5, lw=1.2,
                   label="Medium (0.50)")
        ax.axhspan(0.85,1.0,alpha=0.06,color="#ef4444")
        ax.axhspan(0.50,0.85,alpha=0.04,color="#f59e0b")
        ax.set_xlabel("ICU Hour",color="#5a7ba8",fontsize=10)
        ax.set_ylabel("Sepsis Probability",color="#5a7ba8",fontsize=10)
        ax.set_ylim(0,1)
        ax.tick_params(colors="#5a7ba8",labelsize=9)
        ax.grid(color="#1e3a5f",alpha=0.5)
        ax.legend(fontsize=9,facecolor="#0d1526",labelcolor="#8ba4c8",edgecolor="#1e3a5f")
        ax.set_title(f"Sepsis Probability — {st.session_state.selected_pid}",
                     color="#8ba4c8",fontsize=11)
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close()

with tab3:
    st.markdown(
        "<div style='font-size:12px;color:#5a7ba8;margin-bottom:10px'>"
        "Enter patient vitals manually for an instant prediction.</div>",
        unsafe_allow_html=True)
    with st.form("manual_form"):
        mc1,mc2,mc3,mc4 = st.columns(4)
        with mc1:
            m_hr  = st.number_input("Heart Rate (bpm)",0,300,88)
            m_sp  = st.number_input("SpO₂ (%)",50,100,96)
        with mc2:
            m_sbp = st.number_input("SBP (mmHg)",50,250,115)
            m_dbp = st.number_input("DBP (mmHg)",20,150,72)
        with mc3:
            m_map = st.number_input("MAP (mmHg)",30,150,86)
            m_rr  = st.number_input("Resp Rate",4,60,18)
        with mc4:
            m_tmp = st.number_input("Temp (°C)",34.0,43.0,37.2,step=0.1)
            m_glu = st.number_input("Glucose (mg/dL)",50,500,115)
        sub = st.form_submit_button("🔍 Predict Sepsis Risk", use_container_width=True)

    if sub:
        mp = {"HR":m_hr,"SBP":m_sbp,"DBP":m_dbp,"MAP":m_map,
              "Temp":m_tmp,"SpO2":m_sp,"Resp":m_rr,"Glucose":m_glu,
              "severity":0.5,"age":65,"gender":1,"unit1":1,"unit2":0,
              "hosp_adm":-6.0,"hour":1,"history":[]}
        m_prob = predict_prob(mp)
        m_pri  = priority_score(m_prob, mp)
        m_risk = risk_label(m_pri)
        m_alr  = get_alerts(mp, m_prob)
        m_cont = feature_contribs(mp)
        rc2    = "#ef4444" if m_risk=="High" else "#f59e0b" if m_risk=="Medium" else "#10b981"

        r1,r2,r3 = st.columns(3)
        r1.metric("Sepsis Probability", f"{m_prob:.1%}")
        r2.metric("Priority Score",     f"{m_pri:.3f}")
        r3.metric("Risk Level",         m_risk)

        st.markdown(f"""
        <div style="background:rgba({'239,68,68' if m_risk=='High' else '245,158,11' if m_risk=='Medium' else '16,185,129'},.1);
             border-left:4px solid {rc2};border-radius:0 8px 8px 0;padding:14px 18px;margin:10px 0">
          <b style="color:{rc2};font-size:16px">{m_risk} Risk</b>
          <span style="color:#8ba4c8;font-size:13px;margin-left:12px">
            P(sepsis) = {m_prob:.1%} · Priority = {m_pri:.3f}
          </span>
        </div>""", unsafe_allow_html=True)

        if m_alr:
            for sev,msg in m_alr:
                ac = "#ef4444" if sev=="critical" else "#f59e0b"
                st.markdown(f'<div style="color:{ac};font-size:12px;padding:3px 0">⚠ {msg}</div>',
                            unsafe_allow_html=True)

        mx2 = max(v for _,v in m_cont) or 1
        fh2 = '<div class="sec-title" style="margin-top:10px">Risk Factors</div>'
        for fn2,fv2 in m_cont:
            p2  = fv2/mx2
            bc2 = "#ef4444" if p2>0.7 else "#f59e0b" if p2>0.4 else "#3b82f6"
            fh2 += f"""<div class="feat-row">
              <span class="feat-name">{fn2}</span>
              <div class="feat-bg"><div class="feat-fill" style="width:{int(p2*100)}%;background:{bc2}"></div></div>
              <span class="feat-val">{fv2:.2f}</span>
            </div>"""
        st.markdown(fh2, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-REFRESH
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.auto_refresh:
    time.sleep(st.session_state.sim_speed)
    st.session_state.patients = [step_patient(p) for p in st.session_state.patients]
    st.session_state.refresh_count += 1
    st.rerun()