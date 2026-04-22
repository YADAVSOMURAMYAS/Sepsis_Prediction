import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Search, SlidersHorizontal, ChevronUp, ChevronDown, ArrowRight,
  AlertTriangle, Activity, Users, ShieldAlert, CheckCircle2, LogOut as DischargeIcon } from 'lucide-react'
import type { Patient } from '../api/patients'
import { usePatients } from '../context/PatientContext'
import AlertBanner from '../components/AlertBanner'
import KpiCard from '../components/KpiCard'
import styles from './Dashboard.module.css'

type Risk = Patient['risk']
type SortKey = 'priority_score' | 'sepsis_prob' | 'hr'

/* ── Vital cell ─────────────────────────────────────── */
function Vital({ value, unit, lo, hi }: { value: number; unit: string; lo: number; hi: number }) {
  const abn = value < lo || value > hi
  return (
    <span style={{ color: abn ? 'var(--color-red)' : 'currentcolor', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
      {value.toFixed(1)}<span style={{ color: 'var(--text-muted)', fontSize: '0.68rem', marginLeft: 2 }}>{unit}</span>
    </span>
  )
}

function RiskBadge({ risk }: { risk: Risk }) {
  return <span className={`badge badge-${risk.toLowerCase()}`}>{risk === 'High' ? '🔴' : risk === 'Medium' ? '🟡' : '🟢'} {risk}</span>
}

function ProbBar({ prob }: { prob: number }) {
  const color = prob > 0.8 ? 'var(--color-red)' : prob > 0.5 ? 'var(--color-amber)' : 'var(--color-green)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color }}>{(prob * 100).toFixed(0)}%</span>
      <div className="stat-bar-track" style={{ width: 60 }}>
        <div className="stat-bar-fill" style={{ width: `${prob * 100}%`, background: color }} />
      </div>
    </div>
  )
}

/* ── Detail Panel ───────────────────────────────────── */
function DetailPanel({ patient, onClose }: { patient: Patient; onClose: () => void }) {
  const navigate = useNavigate()
  const { dischargePatient } = usePatients()
  const [discharging, setDischarging] = useState(false)

  const rc = patient.risk === 'High' ? 'var(--color-red)' : patient.risk === 'Medium' ? 'var(--color-amber)' : 'var(--color-green)'

  const vitals = [
    { label: 'Heart Rate',  val: patient.hr,      unit: 'bpm',   lo: 60, hi: 100 },
    { label: 'SBP',         val: patient.sbp,     unit: 'mmHg',  lo: 90, hi: 140 },
    { label: 'MAP',         val: patient.map,     unit: 'mmHg',  lo: 65, hi: 100 },
    { label: 'Temperature', val: patient.temp,    unit: '°C',    lo: 36, hi: 38.3 },
    { label: 'SpO₂',        val: patient.spo2,    unit: '%',     lo: 94, hi: 100 },
    { label: 'Resp Rate',   val: patient.rr,      unit: 'br/m',  lo: 12, hi: 20 },
    { label: 'Glucose',     val: patient.glucose, unit: 'mg/dL', lo: 70, hi: 180 },
  ]

  const contribs = [
    { name: 'Heart Rate',     val: Math.min(1, Math.max(0, (patient.hr - 60) / 80)) },
    { name: 'Blood Pressure', val: Math.min(1, Math.max(0, (100 - patient.sbp) / 50)) },
    { name: 'SpO₂',           val: Math.min(1, Math.max(0, (100 - patient.spo2) / 20)) },
    { name: 'Resp Rate',      val: Math.min(1, Math.max(0, (patient.rr - 12) / 28)) },
    { name: 'Temperature',    val: Math.min(1, Math.max(0, (patient.temp - 36) / 5)) },
    { name: 'MAP',            val: Math.min(1, Math.max(0, (70 - patient.map) / 30)) },
  ].sort((a, b) => b.val - a.val)
  const maxContrib = contribs[0].val || 1

  async function handleDischarge() {
    if (!confirm(`Discharge ${patient.name} (${patient.id})?`)) return
    setDischarging(true)
    try {
      await dischargePatient(patient.id)
      onClose()
    } finally {
      setDischarging(false)
    }
  }

  return (
    <motion.div
      className={styles.detailPanel}
      initial={{ opacity: 0, x: 30 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 30 }}
      transition={{ duration: 0.3 }}
    >
      <div className={styles.detailHead}>
        <div>
          <div className={styles.detailName}>{patient.id}</div>
          <div className={styles.detailSub}>
            {patient.name} · H{patient.icu_hour} · Age {patient.age} · {patient.gender === 'M' ? 'Male' : 'Female'} · {patient.unit}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <RiskBadge risk={patient.risk} />
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>
      </div>

      <div className={styles.probRow}>
        <div className={styles.probBox} style={{ borderColor: `${rc}40` }}>
          <div className={styles.probBig} style={{ color: rc }}>{(patient.sepsis_prob * 100).toFixed(0)}%</div>
          <div className="section-label">Sepsis Probability</div>
        </div>
        <div className={styles.probBox} style={{ borderColor: `${rc}40` }}>
          <div className={styles.probBig} style={{ color: rc }}>{patient.priority_score.toFixed(2)}</div>
          <div className="section-label">Priority Score</div>
        </div>
      </div>

      <div className="section-label" style={{ marginBottom: 8 }}>Current Vitals</div>
      <div className={styles.vitalList}>
        {vitals.map(({ label, val, unit, lo, hi }) => {
          const abn = val < lo || val > hi
          return (
            <div key={label} className={styles.vitalRow}>
              <span className={styles.vitalLab}>{label}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.95rem', fontWeight: 600, color: abn ? 'var(--color-red)' : 'var(--color-green)' }}>
                {val.toFixed(1)}
                <span style={{ fontSize: '0.68rem', fontWeight: 400, color: 'var(--text-muted)', marginLeft: 3}}>{unit}</span>
                {abn && <span style={{ marginLeft: 4, fontSize: '0.7rem' }}>{val > hi ? '↑' : '↓'}</span>}
              </span>
            </div>
          )
        })}
      </div>

      {patient.alerts.length > 0 && (
        <>
          <div className="section-label" style={{ marginTop: 12, marginBottom: 8 }}>Active Alerts</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {patient.alerts.map((a, i) => (
              <div key={i} className={styles.alertItem}><AlertTriangle size={12} /> {a}</div>
            ))}
          </div>
        </>
      )}

      <div className="section-label" style={{ marginTop: 12, marginBottom: 8 }}>Top Risk Factors</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {contribs.map(({ name, val }) => {
          const pct = val / maxContrib
          const bc = pct > 0.7 ? 'var(--color-red)' : pct > 0.4 ? 'var(--color-amber)' : 'var(--color-blue)'
          return (
            <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', width: 120, flexShrink: 0 }}>{name}</span>
              <div className="stat-bar-track" style={{ flex: 1 }}>
                <motion.div className="stat-bar-fill" style={{ background: bc }}
                  initial={{ width: 0 }} animate={{ width: `${pct * 100}%` }}
                  transition={{ duration: 0.6, delay: 0.1 }} />
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)', width: 32, textAlign: 'right' }}>{val.toFixed(2)}</span>
            </div>
          )
        })}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }}
          onClick={() => navigate(`/patients?id=${patient.id}`)} id={`detail-view-${patient.id}`}>
          Full Analytics <ArrowRight size={14} />
        </button>
        <button
          id={`discharge-${patient.id}`}
          className="btn btn-ghost"
          style={{ color: 'var(--color-amber)', borderColor: 'var(--color-amber)', gap: 5 }}
          onClick={handleDischarge}
          disabled={discharging}
        >
          <DischargeIcon size={13} /> {discharging ? 'Discharging…' : 'Discharge'}
        </button>
      </div>
    </motion.div>
  )
}

/* ── Main Dashboard ──────────────────────────────────── */
export default function Dashboard() {
  const { patients, loading, error } = usePatients()
  const [search, setSearch]         = useState('')
  const [riskFilter, setRiskFilter] = useState<Set<Risk>>(new Set(['High','Medium','Low']))
  const [sortKey, setSortKey]       = useState<SortKey>('priority_score')
  const [sortAsc, setSortAsc]       = useState(false)
  const [selected, setSelected]     = useState<Patient | null>(null)
  const [showFilters, setShowFilters] = useState(false)

  const criticalAlerts = useMemo(() =>
    patients.flatMap(p => p.alerts.filter(a => a.includes('85%') || a.includes('SpO')).map(a => ({ patientId: p.id, message: a }))),
  [patients])

  const stats = useMemo(() => ({
    total: patients.length,
    high: patients.filter(p => p.risk === 'High').length,
    medium: patients.filter(p => p.risk === 'Medium').length,
    low: patients.filter(p => p.risk === 'Low').length,
    alerts: patients.reduce((s, p) => s + p.alerts.length, 0),
    avgProb: patients.length ? patients.reduce((s, p) => s + p.sepsis_prob, 0) / patients.length : 0,
  }), [patients])

  function toggleRisk(r: Risk) {
    setRiskFilter(prev => { const n = new Set(prev); n.has(r) ? n.delete(r) : n.add(r); return n })
  }
  function handleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(false) }
  }

  const filtered = useMemo(() => {
    let list = patients.filter(p => {
      const q = search.toLowerCase()
      return riskFilter.has(p.risk) &&
        (p.id.toLowerCase().includes(q) || p.name.toLowerCase().includes(q) || p.unit.toLowerCase().includes(q))
    })
    return list.sort((a, b) => {
      const va = sortKey === 'hr' ? a.hr : sortKey === 'sepsis_prob' ? a.sepsis_prob : a.priority_score
      const vb = sortKey === 'hr' ? b.hr : sortKey === 'sepsis_prob' ? b.sepsis_prob : b.priority_score
      return sortAsc ? va - vb : vb - va
    })
  }, [patients, search, riskFilter, sortKey, sortAsc])

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return null
    return sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />
  }

  return (
    <div className={styles.page}>
      <div className="container" style={{ paddingTop: '5.5rem', paddingBottom: '3rem' }}>
        <motion.div className={styles.header} initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <div>
            <h1 className={`font-display ${styles.title}`}>ICU Patient Dashboard</h1>
            <div className={styles.titleSub}>
              <span className="live-dot" />
              <span className="font-mono" style={{ fontSize: '0.7rem', letterSpacing: '0.08em' }}>
                LIVE · {patients.length} Patients · Real DB
              </span>
            </div>
          </div>
        </motion.div>

        <div className={styles.kpiGrid}>
          <KpiCard label="Total Patients"  value={stats.total}                                icon={<Users size={16}/>}         delay={0} />
          <KpiCard label="High Risk"       value={stats.high}    color="red"                 icon={<ShieldAlert size={16}/>}   delay={0.05} />
          <KpiCard label="Medium Risk"     value={stats.medium}  color="amber"                                                 delay={0.1} />
          <KpiCard label="Low Risk"        value={stats.low}     color="green"               icon={<CheckCircle2 size={16}/>}  delay={0.15} />
          <KpiCard label="Active Alerts"   value={stats.alerts}  color="red"                 icon={<AlertTriangle size={16}/>} delay={0.2} />
          <KpiCard label="Avg Sepsis Prob" value={`${(stats.avgProb*100).toFixed(0)}%`} color="cyan" icon={<Activity size={16}/>} delay={0.25} />
        </div>

        <AlertBanner alerts={criticalAlerts} />

        {error && <div style={{ color: 'var(--color-red)', padding: '0.75rem 1rem', background: 'var(--color-red-dim)', borderRadius: 8, marginBottom: 12 }}>{error}</div>}

        <div className={styles.controls}>
          <div className={styles.searchWrap}>
            <Search size={15} className={styles.searchIcon} />
            <input id="patient-search" className={styles.searchInput}
              placeholder="Search patient ID, name, unit…"
              value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <button className={`btn btn-ghost btn-sm ${styles.filterBtn}`}
            onClick={() => setShowFilters(f => !f)} id="toggle-filters">
            <SlidersHorizontal size={14} /> Filters
          </button>
        </div>

        <AnimatePresence>
          {showFilters && (
            <motion.div className={styles.filterRow}
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25 }}>
              <span className="section-label">Risk level:</span>
              {(['High','Medium','Low'] as Risk[]).map(r => (
                <button key={r} id={`filter-${r.toLowerCase()}`}
                  className={`badge badge-${r.toLowerCase()} ${styles.filterChip} ${!riskFilter.has(r) ? styles.filterChipOff : ''}`}
                  onClick={() => toggleRisk(r)}>{r}</button>
              ))}
              <span className="section-label" style={{ marginLeft: 12 }}>Sort by:</span>
              {[
                { k: 'priority_score' as SortKey, l: 'Priority' },
                { k: 'sepsis_prob'    as SortKey, l: 'Sepsis %' },
                { k: 'hr'            as SortKey, l: 'Heart Rate' },
              ].map(({ k, l }) => (
                <button key={k} id={`sort-${k}`}
                  className={`badge badge-info ${styles.filterChip} ${sortKey === k ? styles.filterChipActive : ''}`}
                  onClick={() => handleSort(k)}>
                  {l} <SortIcon k={k} />
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className={`${styles.main} ${selected ? styles.mainWithDetail : ''}`}>
          <div className={styles.tableWrap}>
            <div className={styles.tableScroll}>
              {loading ? (
                <div className={styles.empty} style={{ padding: '4rem' }}>Loading patients from database…</div>
              ) : (
                <table className={styles.table} id="patient-table">
                  <thead><tr>
                    <th>#</th><th>Patient</th><th>Unit</th><th>HR</th>
                    <th>BP / MAP</th><th>Temp</th><th>SpO₂</th>
                    <th onClick={() => handleSort('sepsis_prob')} className={styles.sortable}>Sepsis Risk <SortIcon k="sepsis_prob" /></th>
                    <th onClick={() => handleSort('priority_score')} className={styles.sortable}>Priority <SortIcon k="priority_score" /></th>
                    <th>Alerts</th>
                  </tr></thead>
                  <tbody>
                    <AnimatePresence>
                      {filtered.map((p, idx) => {
                        const isSel  = selected?.id === p.id
                        const isCrit = p.risk === 'High'
                        return (
                          <motion.tr key={p.id} id={`row-${p.id}`}
                            className={`${styles.row} ${isSel ? styles.rowSelected : ''} ${isCrit ? styles.rowCrit : ''}`}
                            onClick={() => setSelected(isSel ? null : p)}
                            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.25, delay: idx * 0.02 }} layout>
                            <td><span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
                              color: idx < 3 ? 'var(--color-red)' : 'var(--text-muted)', fontWeight: idx < 3 ? 700 : 400 }}>{idx + 1}</span></td>
                            <td>
                              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.id}</div>
                              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{p.name}</div>
                            </td>
                            <td><span className="badge badge-info">{p.unit}</span></td>
                            <td><Vital value={p.hr}   unit="bpm"  lo={60} hi={100} /></td>
                            <td>
                              <Vital value={p.sbp} unit="mmHg" lo={90} hi={140} />
                              <span style={{ color:'var(--text-muted)', margin:'0 3px' }}>/</span>
                              <Vital value={p.map} unit=""     lo={65} hi={100} />
                            </td>
                            <td><Vital value={p.temp} unit="°C"  lo={36} hi={38.3} /></td>
                            <td><Vital value={p.spo2} unit="%"   lo={94} hi={100} /></td>
                            <td><ProbBar prob={p.sepsis_prob} /></td>
                            <td><RiskBadge risk={p.risk} /></td>
                            <td>{p.alerts.length > 0
                              ? <span style={{ color:'var(--color-red)', fontSize:'0.78rem', display:'flex', alignItems:'center', gap:3 }}>
                                  <AlertTriangle size={11} /> {p.alerts.length}
                                </span>
                              : <span style={{ color:'var(--text-muted)' }}>—</span>}
                            </td>
                          </motion.tr>
                        )
                      })}
                    </AnimatePresence>
                  </tbody>
                </table>
              )}
              {!loading && filtered.length === 0 && <div className={styles.empty}>No patients match your filters.</div>}
            </div>
            <div className={styles.tableFooter}>Showing {filtered.length} of {patients.length} patients</div>
          </div>

          <AnimatePresence>
            {selected && <DetailPanel key={selected.id} patient={selected} onClose={() => setSelected(null)} />}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
