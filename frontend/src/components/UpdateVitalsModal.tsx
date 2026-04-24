import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Activity, TrendingUp } from 'lucide-react'
import { usePatients } from '../context/PatientContext'
import type { Patient } from '../api/patients'
import styles from './AddPatientModal.module.css'   // reuse same modal styles

interface Props {
  open:    boolean
  onClose: () => void
  patient: Patient
}

/* ── Field lives outside to prevent focus loss on each keystroke ── */
interface FieldProps {
  label: string
  k: string
  form: Record<string, string>
  setF: (k: string, v: string) => void
  min?: number
  max?: number
  step?: number
}

function Field({ label, k, form, setF, min, max, step }: FieldProps) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>{label}</label>
      <input
        className={styles.input}
        type="number"
        value={form[k]}
        onChange={e => setF(k, e.target.value)}
        min={min}
        max={max}
        step={step}
      />
    </div>
  )
}

export default function UpdateVitalsModal({ open, onClose, patient }: Props) {
  const { updateVitals } = usePatients()

  // Pre-fill with patient's current vitals
  const [form, setForm] = useState({
    hr:      String(patient.hr),
    sbp:     String(patient.sbp),
    dbp:     String(patient.dbp),
    map:     String(patient.map),
    temp:    String(patient.temp),
    spo2:    String(patient.spo2),
    rr:      String(patient.rr),
    glucose: String(patient.glucose),
  })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [success, setSuccess] = useState<null | { risk: string; prob: number; prio: number }>(null)

  function setF(k: string, v: string) {
    setForm(p => ({ ...p, [k]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(''); setLoading(true); setSuccess(null)
    try {
      const updated = await updateVitals(patient.id, {
        hr:      parseFloat(form.hr),
        sbp:     parseFloat(form.sbp),
        dbp:     parseFloat(form.dbp),
        map:     parseFloat(form.map),
        temp:    parseFloat(form.temp),
        spo2:    parseFloat(form.spo2),
        rr:      parseFloat(form.rr),
        glucose: parseFloat(form.glucose),
      })
      setSuccess({ risk: updated.risk, prob: updated.sepsis_prob, prio: updated.priority_score })
    } catch (err: any) {
      setError(err.message || 'Failed to update vitals')
    } finally {
      setLoading(false)
    }
  }

  const riskColor = success
    ? success.risk === 'High' ? 'var(--color-red)'
    : success.risk === 'Medium' ? 'var(--color-amber)'
    : 'var(--color-green)'
    : ''

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className={styles.overlay}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={e => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            className={styles.modal}
            initial={{ opacity: 0, scale: 0.94, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 20 }}
            transition={{ duration: 0.25 }}
          >
            {/* Header */}
            <div className={styles.head}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Activity size={18} color="var(--color-cyan)" />
                <div>
                  <span className={styles.title}>Update Vitals</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 10 }}>
                    {patient.id} · {patient.name} · ICU Hour {patient.icu_hour}
                  </span>
                </div>
              </div>
              <button className={styles.closeBtn} onClick={onClose}><X size={16} /></button>
            </div>

            <form onSubmit={handleSubmit} className={styles.body}>
              <div className={styles.section}>New Vital Readings</div>
              <div className={styles.grid4}>
                <Field label="Heart Rate (bpm)"  k="hr"      min={20}  max={300}           form={form} setF={setF} />
                <Field label="SBP (mmHg)"         k="sbp"     min={50}  max={250}           form={form} setF={setF} />
                <Field label="DBP (mmHg)"         k="dbp"     min={20}  max={150}           form={form} setF={setF} />
                <Field label="MAP (mmHg)"         k="map"     min={30}  max={150}           form={form} setF={setF} />
                <Field label="SpO₂ (%)"           k="spo2"    min={50}  max={100}           form={form} setF={setF} />
                <Field label="Resp Rate (br/m)"   k="rr"      min={4}   max={60}            form={form} setF={setF} />
                <Field label="Temperature (°C)"   k="temp"    min={34}  max={43}  step={0.1} form={form} setF={setF} />
                <Field label="Glucose (mg/dL)"    k="glucose" min={50}  max={500}           form={form} setF={setF} />
              </div>

              {/* Result card after successful update */}
              <AnimatePresence>
                {success && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    style={{
                      marginTop: '1rem',
                      padding: '1rem 1.25rem',
                      borderRadius: 10,
                      border: `1.5px solid ${riskColor}`,
                      background: `${riskColor}12`,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '2rem',
                      flexWrap: 'wrap',
                    }}
                  >
                    <TrendingUp size={18} color={riskColor} />
                    <div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        Sepsis Probability
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.6rem', fontWeight: 800, color: riskColor }}>
                        {(success.prob * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        Priority Score
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.6rem', fontWeight: 800, color: riskColor }}>
                        {success.prio.toFixed(3)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        Risk Level
                      </div>
                      <span className={`badge badge-${success.risk.toLowerCase()}`} style={{ fontSize: '0.85rem', padding: '0.3rem 0.9rem' }}>
                        {success.risk}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                      ✅ Vitals recorded & scores updated
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {error && <div className={styles.err}>{error}</div>}

              <div className={styles.actions}>
                <button type="button" className="btn btn-ghost" onClick={onClose}>
                  {success ? 'Close' : 'Cancel'}
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  <Activity size={15} />
                  {loading ? 'Scoring…' : 'Record & Re-Score'}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
