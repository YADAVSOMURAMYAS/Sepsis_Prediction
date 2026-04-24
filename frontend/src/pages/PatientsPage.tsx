import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { Activity, Brain, ChevronDown, RefreshCw } from 'lucide-react'
import { usePatients } from '../context/PatientContext'
import type { Patient } from '../api/patients'
import UpdateVitalsModal from '../components/UpdateVitalsModal'
import styles from './PatientsPage.module.css'

/* ── Custom Tooltip ─────────────────────────────────── */
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>Hour {label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className={styles.tooltipRow} style={{ color: p.color }}>
          <span>{p.name}:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {typeof p.value === 'number' ? p.value.toFixed(p.name === 'Sepsis%' ? 1 : 0) : p.value}
            {p.name === 'Sepsis%' ? '%' : ''}
          </span>
        </div>
      ))}
    </div>
  )
}



/* ── Vitals Chart Panel ──────────────────────────────── */
function VitalsCharts({ patient }: { patient: Patient }) {
  const hist = patient.history

  const chartConfigs = [
    { key: 'hr',   label: 'Heart Rate',   unit: 'bpm',    color: '#60a5fa', lo: 60,  hi: 100 },
    { key: 'sbp',  label: 'SBP',         unit: 'mmHg',   color: '#a78bfa', lo: 90,  hi: 140 },
    { key: 'map',  label: 'MAP',         unit: 'mmHg',   color: '#34d399', lo: 65,  hi: 100 },
    { key: 'temp', label: 'Temperature', unit: '°C',     color: '#f59e0b', lo: 36,  hi: 38.3 },
    { key: 'spo2', label: 'SpO₂',        unit: '%',      color: '#22d3ee', lo: 94,  hi: 100 },
    { key: 'rr',   label: 'Resp Rate',   unit: 'br/m',   color: '#f87171', lo: 12,  hi: 20 },
  ]

  return (
    <div className={styles.vitalsGrid}>
      {chartConfigs.map(({ key, label, unit, color, lo, hi }) => (
        <motion.div
          key={key}
          className={styles.chartCard}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className={styles.chartHead}>
            <span className={styles.chartLabel}>{label}</span>
            <span className={`font-mono ${styles.chartUnit}`}>{unit}</span>
          </div>
          <ResponsiveContainer width="100%" height={130}>
            <AreaChart data={hist} margin={{ top: 4, right: 4, bottom: 0, left: -28 }}>
              <defs>
                <linearGradient id={`g-${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={color} stopOpacity={0.18} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="hour" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={lo} stroke={color} strokeDasharray="4 4" strokeOpacity={0.35} />
              <ReferenceLine y={hi} stroke={color} strokeDasharray="4 4" strokeOpacity={0.35} />
              <Area
                type="monotone"
                dataKey={key}
                name={label}
                stroke={color}
                strokeWidth={2}
                fill={`url(#g-${key})`}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>
      ))}
    </div>
  )
}

/* ── Risk Trend Chart ────────────────────────────────── */
function RiskTrend({ patient }: { patient: Patient }) {
  const data = patient.history.map(h => ({ hour: h.hour, 'Sepsis%': +(h.prob * 100).toFixed(2) }))
  return (
    <div className={styles.chartCard} style={{ marginTop: '1.5rem' }}>
      <div className={styles.chartHead} style={{ marginBottom: 12 }}>
        <span className={styles.chartLabel} style={{ fontSize: '0.95rem' }}>Sepsis Probability Trend</span>
        <span className="badge badge-high">
          Current: {(patient.sepsis_prob * 100).toFixed(0)}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="probGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="var(--color-red)" stopOpacity={0.25} />
              <stop offset="100%" stopColor="var(--color-red)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="hour" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} label={{ value: 'ICU Hour', position: 'insideBottom', offset: -4, style: { fill: 'var(--text-muted)', fontSize: 9 } }} />
          <YAxis  tick={{ fontSize: 10, fill: 'var(--text-muted)' }} domain={[0, 100]} unit="%" />
          <Tooltip content={<ChartTooltip />} />
          <ReferenceLine y={85} stroke="var(--color-red)"   strokeDasharray="5 3" label={{ value: 'Critical (85%)', fill: 'var(--color-red)', fontSize: 9 }} />
          <ReferenceLine y={50} stroke="var(--color-amber)"  strokeDasharray="5 3" label={{ value: 'Medium (50%)', fill: 'var(--color-amber)', fontSize: 9 }} />
          <Area type="monotone" dataKey="Sepsis%" stroke="var(--color-red)" strokeWidth={2.5} fill="url(#probGrad)" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

/* ── Manual Prediction Form ──────────────────────────── */
interface ManualInputs {
  hr: number; sbp: number; dbp: number; map: number
  temp: number; spo2: number; rr: number; glucose: number
}

function ManualPrediction() {
  const [inputs, setInputs] = useState<ManualInputs>({ hr: 88, sbp: 115, dbp: 72, map: 86, temp: 37.2, spo2: 96, rr: 18, glucose: 115 })
  const [result, setResult] = useState<null | { prob: number; risk: string; priority: number }>(null)

  const predict = () => {
    const { hr, sbp, spo2, rr, temp, map } = inputs
    const prob = Math.min(1, Math.max(0,
      0.25 * Math.min(1, Math.max(0, (hr - 60) / 80)) +
      0.20 * Math.min(1, Math.max(0, (100 - sbp) / 50)) +
      0.20 * Math.min(1, Math.max(0, (100 - spo2) / 20)) +
      0.15 * Math.min(1, Math.max(0, (rr - 12) / 28)) +
      0.10 * Math.min(1, Math.max(0, (temp - 36) / 5)) +
      0.10 * Math.min(1, Math.max(0, (70 - map) / 30))
    ))
    const hr_r  = hr > 100 ? 1 : 0
    const bp_r  = (map < 65 ? 1 : 0) + (sbp < 90 ? 0.5 : 0)
    const priority = Math.min(1, 0.6 * prob + 0.2 * hr_r + 0.2 * Math.min(1, bp_r))
    const risk = priority > 0.8 ? 'High' : priority > 0.5 ? 'Medium' : 'Low'
    setResult({ prob, risk, priority })
  }

  function Field({ label, k, min, max, step }: { label: string; k: keyof ManualInputs; min: number; max: number; step?: number }) {
    return (
      <div className={styles.field}>
        <label htmlFor={`manual-${k}`} className="section-label">{label}</label>
        <input
          id={`manual-${k}`}
          type="number"
          className={styles.input}
          value={inputs[k]}
          min={min}
          max={max}
          step={step || 1}
          onChange={e => setInputs(p => ({ ...p, [k]: parseFloat(e.target.value) || 0 }))}
        />
      </div>
    )
  }

  const rc = result ? (result.risk === 'High' ? 'var(--color-red)' : result.risk === 'Medium' ? 'var(--color-amber)' : 'var(--color-green)') : ''

  return (
    <div className={styles.manualForm}>
      <div className={styles.chartHead} style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Brain size={18} color="var(--color-cyan)" />
          <span className={styles.chartLabel} style={{ fontSize: '0.95rem' }}>Manual Clinical Prediction</span>
        </div>
        <span className="section-label">Enter vitals for instant XGBoost-based risk estimate</span>
      </div>

      <div className={styles.fieldGrid}>
        <Field label="Heart Rate (bpm)"   k="hr"      min={0}    max={300} />
        <Field label="SBP (mmHg)"         k="sbp"     min={50}   max={250} />
        <Field label="DBP (mmHg)"         k="dbp"     min={20}   max={150} />
        <Field label="MAP (mmHg)"         k="map"     min={30}   max={150} />
        <Field label="SpO₂ (%)"           k="spo2"    min={50}   max={100} />
        <Field label="Resp Rate (br/m)"   k="rr"      min={4}    max={60}  />
        <Field label="Temperature (°C)"   k="temp"    min={34}   max={43}  step={0.1} />
        <Field label="Glucose (mg/dL)"    k="glucose" min={50}   max={500} />
      </div>

      <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
        onClick={predict} id="manual-predict-btn">
        <Activity size={16} /> Predict Sepsis Risk
      </button>

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className={styles.resultBox}
            style={{ borderColor: rc, background: `${rc}12` }}
          >
            <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <div className="section-label" style={{ marginBottom: 4 }}>Sepsis Probability</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2.2rem', fontWeight: 800, color: rc }}>
                  {(result.prob * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="section-label" style={{ marginBottom: 4 }}>Priority Score</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2.2rem', fontWeight: 800, color: rc }}>
                  {result.priority.toFixed(3)}
                </div>
              </div>
              <div>
                <div className="section-label" style={{ marginBottom: 4 }}>Risk Level</div>
                <span className={`badge badge-${result.risk.toLowerCase()}`} style={{ fontSize: '0.85rem', padding: '0.35rem 1rem' }}>
                  {result.risk}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ── Population Stats ────────────────────────────────── */
function PopulationStats() {
  const { patients } = usePatients()
  const riskDist = [
    { name: 'High',   count: patients.filter(p => p.risk === 'High').length,   fill: 'var(--color-red)' },
    { name: 'Medium', count: patients.filter(p => p.risk === 'Medium').length, fill: 'var(--color-amber)' },
    { name: 'Low',    count: patients.filter(p => p.risk === 'Low').length,    fill: 'var(--color-green)' },
  ]

  const binData = Array.from({ length: 10 }, (_, i) => {
    const lo = i / 10, hi = (i + 1) / 10
    return {
      bin: `${Math.round(lo * 100)}-${Math.round(hi * 100)}%`,
      count: patients.filter(p => p.sepsis_prob >= lo && p.sepsis_prob < hi).length,
    }
  })

  return (
    <div className={styles.popGrid}>
      <div className={styles.chartCard}>
        <div className={styles.chartHead} style={{ marginBottom: 12 }}>
          <span className={styles.chartLabel}>Risk Distribution</span>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={riskDist} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="count" name="Patients" radius={[4, 4, 0, 0]}>
              {riskDist.map((d, i) => (
                <rect key={i} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className={styles.chartCard}>
        <div className={styles.chartHead} style={{ marginBottom: 12 }}>
          <span className={styles.chartLabel}>Sepsis Probability Distribution</span>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={binData} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
            <XAxis dataKey="bin" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
            <Tooltip content={<ChartTooltip />} />
            <Bar dataKey="count" name="Patients" fill="var(--color-cyan)" radius={[4, 4, 0, 0]} opacity={0.8} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/* ── Main Page ───────────────────────────────────────── */
export default function PatientsPage() {
  const { patients } = usePatients()
  const [params] = useSearchParams()
  const initId = params.get('id') || patients[0]?.id || ''

  const [selectedId,      setSelectedId]      = useState(initId)
  const [activeTab,       setActiveTab]       = useState<'vitals' | 'trend' | 'predict' | 'population'>('vitals')
  const [dropOpen,        setDropOpen]        = useState(false)
  const [updateModalOpen, setUpdateModalOpen] = useState(false)

  const patient = useMemo(() => patients.find(p => p.id === selectedId) || patients[0], [selectedId, patients])

  const tabs = [
    { id: 'vitals'     as const, label: 'Vitals History',    icon: Activity },
    { id: 'trend'      as const, label: 'Risk Trend',        icon: Activity },
    { id: 'predict'    as const, label: 'Manual Prediction', icon: Brain },
    { id: 'population' as const, label: 'Population Stats',  icon: Activity },
  ]

  return (
    <div className={styles.page}>
      <div className="container" style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>

        {/* Header */}
        <motion.div className={styles.header} initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <div>
            <h1 className={`font-display ${styles.title}`}>Patient Analytics</h1>
            <div className={styles.titleSub}>Deep vitals, risk trends &amp; model explainability</div>
          </div>

          {/* Patient selector */}
          <div className={styles.selectorWrap}>
            <button
              id="patient-selector-btn"
              className={styles.selector}
              onClick={() => setDropOpen(d => !d)}
            >
              <div>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{patient?.id}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{patient?.name} · {patient?.unit}</div>
              </div>
              <ChevronDown size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            </button>

            <AnimatePresence>
              {dropOpen && (
                <motion.div
                  className={styles.dropdown}
                  initial={{ opacity: 0, y: -6, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.97 }}
                  transition={{ duration: 0.18 }}
                >
                  {patients.map(p => (
                    <button
                      key={p.id}
                      id={`select-${p.id}`}
                      className={`${styles.dropItem} ${p.id === selectedId ? styles.dropItemActive : ''}`}
                      onClick={() => { setSelectedId(p.id); setDropOpen(false) }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 600 }}>{p.id}</span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{p.name}</span>
                      </div>
                      <span className={`badge badge-${p.risk.toLowerCase()}`}>{p.risk}</span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Patient summary strip */}
        {patient && (
          <motion.div
            className={styles.summaryStrip}
            key={patient.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className={styles.summaryItem}>
              <span className="section-label">Patient</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{patient.id}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className="section-label">Age / Gender</span>
              <span>{patient.age} / {patient.gender}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className="section-label">ICU Hour</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>H{patient.icu_hour}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className="section-label">Sepsis Risk</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: patient.sepsis_prob > 0.7 ? 'var(--color-red)' : 'var(--color-green)' }}>
                {(patient.sepsis_prob * 100).toFixed(0)}%
              </span>
            </div>
            <div className={styles.summaryItem}>
              <span className="section-label">Priority</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{patient.priority_score.toFixed(3)}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className="section-label">Risk Level</span>
              <span className={`badge badge-${patient.risk.toLowerCase()}`}>{patient.risk}</span>
            </div>
            {/* Update Vitals button */}
            <button
              id="update-vitals-btn"
              className="btn btn-primary"
              style={{ marginLeft: 'auto', gap: 6 }}
              onClick={() => setUpdateModalOpen(true)}
            >
              <RefreshCw size={14} /> Update Vitals
            </button>
          </motion.div>
        )}

        {/* Update Vitals Modal */}
        {patient && (
          <UpdateVitalsModal
            open={updateModalOpen}
            onClose={() => setUpdateModalOpen(false)}
            patient={patient}
          />
        )}

        {/* Tabs */}
        <div className={styles.tabs}>
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`tab-${id}`}
              className={`${styles.tab} ${activeTab === id ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(id)}
            >
              <Icon size={14} />
              {label}
              {activeTab === id && (
                <motion.div className={styles.tabIndicator} layoutId="tab-indicator"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }} />
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          {patient && (
            <motion.div
              key={`${activeTab}-${patient.id}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.25 }}
            >
              {activeTab === 'vitals'     && <VitalsCharts   patient={patient} />}
              {activeTab === 'trend'      && <RiskTrend      patient={patient} />}
              {activeTab === 'predict'    && <ManualPrediction />}
              {activeTab === 'population' && <PopulationStats />}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
