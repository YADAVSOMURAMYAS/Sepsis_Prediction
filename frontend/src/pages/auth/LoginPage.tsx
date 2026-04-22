import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Eye, EyeOff, Building2, Lock, Mail, MapPin, Hash, Users } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { authApi } from '../../api/auth'
import type { HospitalListItem } from '../../api/auth'
import styles from './LoginPage.module.css'

type Tab = 'login' | 'register'

function InputField({
  id, label, type = 'text', value, onChange, placeholder, icon: Icon, required = true,
}: {
  id: string; label: string; type?: string; value: string
  onChange: (v: string) => void; placeholder?: string
  icon?: React.ElementType; required?: boolean
}) {
  const [show, setShow] = useState(false)
  const isPass = type === 'password'
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <div className={styles.inputWrap}>
        {Icon && <Icon size={15} className={styles.inputIcon} />}
        <input
          id={id}
          className={styles.input}
          style={{ paddingLeft: Icon ? '2.4rem' : '0.9rem' }}
          type={isPass && show ? 'text' : type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          required={required}
          autoComplete={isPass ? 'current-password' : 'off'}
        />
        {isPass && (
          <button type="button" className={styles.eyeBtn} onClick={() => setShow(s => !s)}>
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
    </div>
  )
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, register, isAuthenticated } = useAuth()

  const [tab, setTab]         = useState<Tab>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [hospitals, setHospitals] = useState<HospitalListItem[]>([])

  // Login form
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPass,  setLoginPass]  = useState('')

  // Register form
  const [regId,      setRegId]      = useState('')
  const [regName,    setRegName]    = useState('')
  const [regCity,    setRegCity]    = useState('')
  const [regAddress, setRegAddress] = useState('')
  const [regEmail,   setRegEmail]   = useState('')
  const [regPass,    setRegPass]    = useState('')
  const [regBeds,    setRegBeds]    = useState('100')
  const [regUnits,   setRegUnits]   = useState('MICU, SICU, CCU')

  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true })
  }, [isAuthenticated, navigate])

  useEffect(() => {
    authApi.listHospitals().then(setHospitals).catch(() => {})
  }, [])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await login(loginEmail, loginPass)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    if (!regId.match(/^[A-Z0-9]{2,8}$/)) {
      setError('Hospital ID must be 2-8 uppercase letters (e.g. MGH)')
      return
    }
    setError(''); setLoading(true)
    try {
      await register({
        id: regId.toUpperCase(),
        name: regName, city: regCity, address: regAddress,
        admin_email: regEmail, password: regPass,
        units: regUnits.split(',').map(u => u.trim()).filter(Boolean),
        beds_total: parseInt(regBeds) || 100,
      })
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  function quickFill(h: HospitalListItem) {
    setLoginEmail(h.admin_email)
    setLoginPass('SepsisAI2024')
    setError('')
  }

  return (
    <div className={styles.page}>
      {/* Background blobs */}
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.center}>
        {/* Logo */}
        <motion.div
          className={styles.logo}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles.logoIcon}><Activity size={22} /></div>
          <span className={`font-display ${styles.logoText}`}>SepsisAI</span>
        </motion.div>

        {/* Card */}
        <motion.div
          className={styles.card}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          {/* Tabs */}
          <div className={styles.tabs}>
            {(['login', 'register'] as Tab[]).map(t => (
              <button
                key={t}
                id={`tab-${t}`}
                className={`${styles.tab} ${tab === t ? styles.tabActive : ''}`}
                onClick={() => { setTab(t); setError('') }}
              >
                {t === 'login' ? 'Sign In' : 'Register Hospital'}
                {tab === t && <motion.div className={styles.tabLine} layoutId="login-tab-line" />}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {tab === 'login' ? (
              <motion.form
                key="login"
                onSubmit={handleLogin}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
                className={styles.form}
              >
                <p className={styles.formSub}>Sign in to your hospital's clinical dashboard.</p>

                <InputField id="login-email" label="Admin Email" type="email"
                  value={loginEmail} onChange={setLoginEmail}
                  placeholder="admin@hospital.com" icon={Mail} />
                <InputField id="login-pass" label="Password" type="password"
                  value={loginPass} onChange={setLoginPass}
                  placeholder="••••••••" icon={Lock} />

                {error && <div className={styles.err}>{error}</div>}

                <button id="login-submit" type="submit" className={`btn btn-primary ${styles.submitBtn}`} disabled={loading}>
                  {loading ? 'Signing in…' : 'Sign In'}
                </button>

                {/* Quick-fill chips */}
                {hospitals.length > 0 && (
                  <div className={styles.quickFill}>
                    <span className={styles.quickLabel}>Demo hospitals:</span>
                    <div className={styles.chips}>
                      {hospitals.map(h => (
                        <button
                          key={h.id}
                          type="button"
                          id={`quick-${h.id}`}
                          className={styles.chip}
                          style={{ borderColor: h.accent_color, color: h.accent_color }}
                          onClick={() => quickFill(h)}
                          title={`${h.name} — ${h.city}`}
                        >
                          {h.id}
                        </button>
                      ))}
                    </div>
                    <span className={styles.quickHint}>Click any chip → auto-fills with demo credentials</span>
                  </div>
                )}
              </motion.form>
            ) : (
              <motion.form
                key="register"
                onSubmit={handleRegister}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className={styles.form}
              >
                <p className={styles.formSub}>Register your hospital to activate the SepsisAI platform.</p>

                <div className={styles.row2}>
                  <InputField id="reg-id"   label="Hospital ID (2-8 chars)"  value={regId}   onChange={v => setRegId(v.toUpperCase())}  placeholder="MGH"            icon={Hash} />
                  <InputField id="reg-beds" label="Total ICU Beds"            value={regBeds} onChange={setRegBeds}                        placeholder="100"            icon={Users} />
                </div>
                <InputField id="reg-name"    label="Hospital Name"    value={regName}    onChange={setRegName}    placeholder="Massachusetts General Hospital" icon={Building2} />
                <InputField id="reg-city"    label="City, State"      value={regCity}    onChange={setRegCity}    placeholder="Boston, MA"   icon={MapPin} />
                <InputField id="reg-address" label="Full Address"     value={regAddress} onChange={setRegAddress} placeholder="55 Fruit St, Boston, MA 02114" icon={MapPin} />
                <InputField id="reg-units"   label="ICU Units (comma-separated)" value={regUnits} onChange={setRegUnits} placeholder="MICU, SICU, CCU" icon={Building2} />
                <InputField id="reg-email"   label="Admin Email"      value={regEmail}   onChange={setRegEmail}  type="email" placeholder="admin@hospital.com" icon={Mail} />
                <InputField id="reg-pass"    label="Password"         value={regPass}    onChange={setRegPass}   type="password" placeholder="••••••••" icon={Lock} />

                {error && <div className={styles.err}>{error}</div>}

                <button id="register-submit" type="submit" className={`btn btn-primary ${styles.submitBtn}`} disabled={loading}>
                  {loading ? 'Registering…' : 'Register & Enter Dashboard'}
                </button>
              </motion.form>
            )}
          </AnimatePresence>
        </motion.div>

        <motion.p
          className={styles.footer}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          SepsisAI Clinical Intelligence Platform · All hospital data is encrypted at rest
        </motion.p>
      </div>
    </div>
  )
}
