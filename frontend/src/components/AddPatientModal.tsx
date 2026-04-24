import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, UserPlus } from 'lucide-react'
import { usePatients } from '../context/PatientContext'
import { useAuth } from '../context/AuthContext'
import styles from './AddPatientModal.module.css'

interface Props { open: boolean; onClose: () => void }

/* ── Field MUST live outside AddPatientModal ────────────────────────────
   If defined inside, React sees a brand-new component type on every render,
   unmounts + remounts the <input>, and the cursor is lost after each keystroke. */
interface FieldProps {
  label: string
  k: string
  form: Record<string, string>
  setF: (k: string, v: string) => void
  type?: string
  min?: number
  max?: number
  step?: number
}

function Field({ label, k, form, setF, type = 'number', min, max, step }: FieldProps) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>{label}</label>
      <input
        className={styles.input}
        type={type}
        value={form[k]}
        onChange={e => setF(k, e.target.value)}
        min={min}
        max={max}
        step={step}
      />
    </div>
  )
}

export default function AddPatientModal({ open, onClose }: Props) {
  const { addPatient } = usePatients()
  const { hospital }   = useAuth()

  const [form, setForm] = useState({
    name: '', age: '', gender: 'M', unit: hospital?.units[0] || 'MICU',
    diagnosis: '', hr: '80', sbp: '120', dbp: '75', map: '90',
    temp: '37.0', spo2: '98', rr: '16', glucose: '100',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  function setF(k: string, v: string) {
    setForm(p => ({ ...p, [k]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim() || !form.age) {
      setError('Name and age are required')
      return
    }
    setError(''); setLoading(true)
    try {
      await addPatient({
        name: form.name.trim(),
        age: parseInt(form.age),
        gender: form.gender,
        unit: form.unit,
        diagnosis: form.diagnosis || 'Pending',
        hr: parseFloat(form.hr), sbp: parseFloat(form.sbp),
        dbp: parseFloat(form.dbp), map: parseFloat(form.map),
        temp: parseFloat(form.temp), spo2: parseFloat(form.spo2),
        rr: parseFloat(form.rr), glucose: parseFloat(form.glucose),
      })
      onClose()
      setForm({ name: '', age: '', gender: 'M', unit: hospital?.units[0] || 'MICU',
        diagnosis: '', hr: '80', sbp: '120', dbp: '75', map: '90',
        temp: '37.0', spo2: '98', rr: '16', glucose: '100' })
    } catch (err: any) {
      setError(err.message || 'Failed to add patient')
    } finally {
      setLoading(false)
    }
  }

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
                <UserPlus size={18} color="var(--color-cyan)" />
                <span className={styles.title}>Admit New Patient</span>
              </div>
              <button className={styles.closeBtn} onClick={onClose}><X size={16} /></button>
            </div>

            <form onSubmit={handleSubmit} className={styles.body}>
              {/* Demographics */}
              <div className={styles.section}>Patient Information</div>
              <div className={styles.grid3}>
                <Field label="Full Name" k="name" type="text" form={form} setF={setF} />
                <Field label="Age"       k="age"  min={0} max={120} form={form} setF={setF} />
                <div className={styles.field}>
                  <label className={styles.label}>Gender</label>
                  <select className={styles.input} value={form.gender} onChange={e => setF('gender', e.target.value)}>
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                  </select>
                </div>
              </div>

              <div className={styles.grid2}>
                <div className={styles.field}>
                  <label className={styles.label}>ICU Unit</label>
                  <select className={styles.input} value={form.unit} onChange={e => setF('unit', e.target.value)}>
                    {(hospital?.units || ['MICU','SICU','CCU']).map(u => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>
                <Field label="Diagnosis" k="diagnosis" type="text" form={form} setF={setF} />
              </div>

              {/* Vitals */}
              <div className={styles.section}>Initial Vitals</div>
              <div className={styles.grid4}>
                <Field label="Heart Rate (bpm)"  k="hr"      min={20} max={300}           form={form} setF={setF} />
                <Field label="SBP (mmHg)"         k="sbp"     min={50} max={250}           form={form} setF={setF} />
                <Field label="DBP (mmHg)"         k="dbp"     min={20} max={150}           form={form} setF={setF} />
                <Field label="MAP (mmHg)"         k="map"     min={30} max={150}           form={form} setF={setF} />
                <Field label="SpO₂ (%)"           k="spo2"    min={50} max={100}           form={form} setF={setF} />
                <Field label="Resp Rate (br/m)"   k="rr"      min={4}  max={60}            form={form} setF={setF} />
                <Field label="Temperature (°C)"   k="temp"    min={34} max={43}  step={0.1} form={form} setF={setF} />
                <Field label="Glucose (mg/dL)"    k="glucose" min={50} max={500}           form={form} setF={setF} />
              </div>

              {error && <div className={styles.err}>{error}</div>}

              <div className={styles.actions}>
                <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
                <button id="admit-submit" type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Admitting…' : 'Admit Patient'}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
