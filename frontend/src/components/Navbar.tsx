import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Sun, Moon, Activity, LayoutDashboard, Users, Home, LogOut, UserPlus, Building2 } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'
import AddPatientModal from './AddPatientModal'
import styles from './Navbar.module.css'

const navLinks = [
  { path: '/',          label: 'Home',      icon: Home },
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/patients',  label: 'Analytics', icon: Users },
]

export default function Navbar() {
  const { theme, toggleTheme }       = useTheme()
  const { isAuthenticated, hospital, logout } = useAuth()
  const location  = useLocation()
  const navigate  = useNavigate()
  const [addOpen, setAddOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <>
      <motion.nav
        className={styles.navbar}
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <div className={`container ${styles.inner}`}>
          {/* Logo */}
          <Link to="/" className={styles.logo}>
            <motion.div
              className={styles.logoIcon}
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Activity size={20} />
            </motion.div>
            <span className={`font-display font-bold ${styles.logoText}`}>SepsisAI</span>
            <span className={styles.logoBadge}>BETA</span>
          </Link>

          {/* Nav links */}
          <div className={styles.links}>
            {navLinks.map(({ path, label, icon: Icon }) => {
              const active = location.pathname === path
              return (
                <Link key={path} to={path} className={`${styles.link} ${active ? styles.linkActive : ''}`}>
                  <Icon size={15} />
                  <span>{label}</span>
                  {active && (
                    <motion.div
                      className={styles.linkUnderline}
                      layoutId="nav-underline"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                </Link>
              )
            })}
          </div>

          {/* Right */}
          <div className={styles.right}>
            {/* Hospital name badge */}
            {isAuthenticated && hospital && (
              <div className={styles.hospitalChip} style={{ borderColor: `${hospital.accent_color}40` }}>
                <Building2 size={12} style={{ color: hospital.accent_color }} />
                <span style={{ color: hospital.accent_color, fontFamily: 'var(--font-mono)', fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.04em' }}>
                  {hospital.id}
                </span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {hospital.name}
                </span>
              </div>
            )}

            {/* Add patient button — shown on dashboard only */}
            {isAuthenticated && location.pathname === '/dashboard' && (
              <button
                id="navbar-add-patient"
                className={`btn btn-primary btn-sm`}
                onClick={() => setAddOpen(true)}
                style={{ gap: 5 }}
              >
                <UserPlus size={13} /> Add Patient
              </button>
            )}

            <div className={styles.liveChip}>
              <span className="live-dot" />
              <span className="font-mono" style={{ fontSize: '0.65rem', letterSpacing: '0.08em' }}>LIVE</span>
            </div>

            <button className={styles.themeBtn} onClick={toggleTheme} aria-label="Toggle theme">
              <motion.div
                key={theme}
                initial={{ rotate: -30, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
              </motion.div>
            </button>

            {isAuthenticated && (
              <button
                id="navbar-logout"
                className={styles.themeBtn}
                onClick={handleLogout}
                title="Logout"
                style={{ color: 'var(--text-muted)' }}
              >
                <LogOut size={16} />
              </button>
            )}
          </div>
        </div>
      </motion.nav>

      <AddPatientModal open={addOpen} onClose={() => setAddOpen(false)} />
    </>
  )
}
