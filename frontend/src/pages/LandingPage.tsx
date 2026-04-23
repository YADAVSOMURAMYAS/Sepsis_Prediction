import { useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, Shield, Zap, BarChart3, Activity, Brain, Clock, Stethoscope } from 'lucide-react'
import styles from './LandingPage.module.css'

/* ── Hero Symbol ─────────────────────────────────── */
function HeroSymbol() {
  return (
    <div style={{ position: 'relative', width: '100%', maxWidth: 500, aspectRatio: '1/1', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {/* Outer Pulse */}
      <motion.div
        animate={{ scale: [1, 1.25, 1], opacity: [0.2, 0.5, 0.2] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute',
          width: '80%', height: '80%',
          background: 'radial-gradient(circle, rgba(6,182,212,0.3) 0%, rgba(6,182,212,0) 70%)',
          borderRadius: '50%',
        }}
      />
      {/* Inner Pulse */}
      <motion.div
        animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.8, 0.4] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute',
          width: '55%', height: '55%',
          background: 'radial-gradient(circle, rgba(14,165,233,0.4) 0%, rgba(14,165,233,0) 70%)',
          borderRadius: '50%',
        }}
      />
      
      {/* Stethoscope Icon */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1, y: [-5, 5, -5] }}
        transition={{ 
          y: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
          default: { duration: 1, ease: 'easeOut' }
        }}
        style={{ position: 'relative', zIndex: 10, color: '#06b6d4', filter: 'drop-shadow(0 0 25px rgba(6, 182, 212, 0.7))' }}
      >
        <Stethoscope size={180} strokeWidth={1.5} />
      </motion.div>
    </div>
  )
}

/* ── Floating Vital Card ──────────────────────────────── */
function FloatingCard({ label, value, unit, status, delay, x, y, rotate }:
  { label: string; value: string; unit: string; status: 'critical' | 'warning' | 'normal'; delay: number; x: string; y: string; rotate: number }) {
  const statusColor = status === 'critical' ? 'var(--color-red)' : status === 'warning' ? 'var(--color-amber)' : 'var(--color-green)'
  return (
    <motion.div
      className={styles.floatCard}
      style={{ position: 'absolute', left: x, top: y, rotate: `${rotate}deg` }}
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1, y: [0, -8, 0] }}
      transition={{
        opacity: { delay, duration: 0.5 },
        scale:   { delay, duration: 0.5 },
        y:       { delay: delay + 0.5, duration: 3 + delay * 0.5, repeat: Infinity, ease: 'easeInOut' },
      }}
    >
      <div className={styles.floatLabel}>{label}</div>
      <div className={styles.floatValue} style={{ color: statusColor }}>
        {value}
        <span className={styles.floatUnit}>{unit}</span>
      </div>
      <div className={styles.floatBar} style={{ '--fc': statusColor } as React.CSSProperties} />
    </motion.div>
  )
}

/* ── Feature Card ─────────────────────────────────────── */
function FeatureCard({ icon: Icon, title, desc, delay }: {
  icon: React.ElementType; title: string; desc: string; delay: number
}) {
  return (
    <motion.div
      className={styles.featureCard}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -6, transition: { duration: 0.2 } }}
    >
      <div className={styles.featureIcon}>
        <Icon size={24} />
      </div>
      <h3 className={`font-display ${styles.featureTitle}`}>{title}</h3>
      <p className={styles.featureDesc}>{desc}</p>
    </motion.div>
  )
}

/* ── Stat Block ───────────────────────────────────────── */
function StatBlock({ value, label, color }: { value: string; label: string; color?: string }) {
  return (
    <motion.div
      className={styles.statBlock}
      initial={{ opacity: 0, scale: 0.8 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
    >
      <div className={styles.statValue} style={{ color: color || 'var(--color-red)' }}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </motion.div>
  )
}

/* ── Main Component ───────────────────────────────────── */
export default function LandingPage() {
  const navigate = useNavigate()
  const heroRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const heroY = useTransform(scrollYProgress, [0, 1], ['0%', '30%'])

  return (
    <div className={styles.page}>
      {/* ── HERO ───────────────────────────────────── */}
      <section ref={heroRef} className={styles.hero}>
        <motion.div className={styles.heroGlow} style={{ y: heroY }} />
        <div className={`container ${styles.heroInner}`}>
          {/* Left */}
          <div className={styles.heroLeft}>
            <motion.div
              className={styles.heroBadge}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className="live-dot" />
              <span className="font-mono" style={{ fontSize: '0.7rem', letterSpacing: '0.1em' }}>
                PhysioNet Challenge 2019 · 80% ROC-AUC
              </span>
            </motion.div>

            <motion.h1
              className={`font-display ${styles.heroTitle}`}
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
            >
              Predict Sepsis{' '}
              <span className={styles.heroAccent}>6 Hours</span>
              {' '}Before It Strikes
            </motion.h1>

            <motion.p
              className={styles.heroSub}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.25 }}
            >
              AI-powered ICU intelligence that ranks your most critical patients —
              before the numbers scream. Trained on 40,336 patients.
            </motion.p>

            <motion.div
              className={styles.heroCta}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <button className="btn btn-primary" onClick={() => navigate('/dashboard')} id="cta-dashboard">
                Open Dashboard <ArrowRight size={16} />
              </button>
              <button className="btn btn-ghost" onClick={() => navigate('/patients')} id="cta-analytics">
                View Analytics
              </button>
            </motion.div>

            <motion.div
              className={styles.heroMetrics}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              {[
                { v: '0.800', l: 'Patient ROC-AUC' },
                { v: '69.5%', l: 'Patient Recall' },
                { v: '4.1x', l: 'False Alarm Rate' },
              ].map(({ v, l }) => (
                <div key={l} className={styles.heroMetricItem}>
                  <div className={`font-mono ${styles.heroMetricVal}`}>{v}</div>
                  <div className={styles.heroMetricLab}>{l}</div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right – 3D Hospital Symbol + Floating Cards */}
          <div className={styles.heroRight}>
            <motion.div
              className={styles.heartWrap}
              initial={{ opacity: 0, scale: 0.7, rotateY: -20 }}
              animate={{ opacity: 1, scale: 1, rotateY: 0 }}
              transition={{ duration: 1, delay: 0.2, ease: 'easeOut' }}
            >
              <HeroSymbol />
              <FloatingCard label="HR"   value="112" unit="bpm"  status="critical" delay={0.8} x="75%"  y="12%" rotate={3}  />
              <FloatingCard label="MAP"  value="58"  unit="mmHg" status="critical" delay={1.0} x="-8%"  y="60%" rotate={-4} />
              <FloatingCard label="SpO₂" value="94.2" unit="%" status="warning"  delay={1.2} x="70%"  y="65%" rotate={2}  />
              <FloatingCard label="Sepsis Risk" value="87" unit="%" status="critical" delay={1.4} x="-5%"  y="15%" rotate={-3} />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── STATS STRIP ───────────────────────────── */}
      <section className={styles.statsStrip}>
        <div className="container">
          <div className={styles.statsGrid}>
            <StatBlock value="1 in 3"  label="hospital deaths involve sepsis" color="var(--color-red)" />
            <StatBlock value="7.6%"    label="higher mortality per hour of treatment delay" color="var(--color-red)" />
            <StatBlock value="+40K"    label="ICU patients in training dataset" color="var(--color-cyan)" />
            <StatBlock value="6 hours" label="advance warning window" color="var(--color-green)" />
          </div>
        </div>
      </section>

      {/* ── FEATURES ──────────────────────────────── */}
      <section className={styles.features}>
        <div className="container">
          <motion.div
            className={styles.sectionHead}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <span className="section-label">Platform Capabilities</span>
            <h2 className={`font-display ${styles.sectionTitle}`}>
              Clinical AI That Clinicians Trust
            </h2>
          </motion.div>

          <div className={styles.featuresGrid}>
            <FeatureCard icon={Brain} delay={0}    title="XGBoost Prediction Engine" desc="68 engineered features from rolling vitals, labs, and admission data. Trained with early-label shift to fire 6 hours before onset." />
            <FeatureCard icon={Zap}   delay={0.1}  title="Real-Time Patient Ranking" desc="Priority score integrates sepsis probability, hemodynamic instability flags, and shock index into a single actionable rank." />
            <FeatureCard icon={BarChart3} delay={0.2} title="ICU Analytics Dashboard" desc="Visualize vitals history, risk trends, and population-level distributions across your entire ICU at a glance." />
            <FeatureCard icon={Clock} delay={0.3}  title="6-Hour Early Warning" desc="SepsisLabel shifted backward by 6 hours during training means alerts fire well before clinical deterioration becomes obvious." />
            <FeatureCard icon={Activity} delay={0.4} title="Live Simulation Mode" desc="Step-by-step patient deterioration simulation with realistic physiology so you can train and validate workflows." />
            <FeatureCard icon={Shield} delay={0.5} title="HIPAA-Ready Architecture" desc="Designed for hospital deployment with identifiable data kept local, model inference running on-premise." />
          </div>
        </div>
      </section>

      {/* ── MODEL DETAILS ─────────────────────────── */}
      <section className={styles.modelSection}>
        <div className="container">
          <div className={styles.modelGrid}>
            <motion.div
              className={styles.modelLeft}
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <span className="section-label">Under The Hood</span>
              <h2 className={`font-display ${styles.sectionTitle}`} style={{ marginTop: '0.75rem' }}>
                4-Phase ML Pipeline
              </h2>
              <div className={styles.phaseList}>
                {[
                  { n: '01', title: 'Streaming Preprocessing', desc: 'Line-by-line CSV parsing of 40K .psv files. Imputation, scaling, early-label shift.' },
                  { n: '02', title: 'Feature Engineering',     desc: '68 features: rolling stats (3h/6h), vitals delta, clinical flags, shock index.' },
                  { n: '03', title: 'XGBoost Training',        desc: 'Stratified patient-level split, threshold auto-selected for recall ≥ 70%.' },
                  { n: '04', title: 'Severity Scoring',        desc: 'Priority = 0.6 × prob + 0.2 × HR_risk + 0.2 × BP_risk. Ranked output.' },
                ].map(({ n, title, desc }) => (
                  <motion.div
                    key={n}
                    className={styles.phaseItem}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.4, delay: +n * 0.05 }}
                  >
                    <div className={styles.phaseNum}>{n}</div>
                    <div>
                      <div className={styles.phaseTitle}>{title}</div>
                      <div className={styles.phaseDesc}>{desc}</div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            <motion.div
              className={styles.modelRight}
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <div className={styles.metricsPanel}>
                <div className={styles.metricsPanelHead}>
                  <span className="font-mono" style={{ fontSize: '0.65rem', letterSpacing: '0.12em', color: 'var(--text-muted)' }}>MODEL PERFORMANCE</span>
                </div>
                {[
                  { label: 'Row-level ROC-AUC',    val: '0.755', pct: 75.5 },
                  { label: 'Patient-level ROC-AUC', val: '0.800', pct: 80 },
                  { label: 'Patient Recall',         val: '69.5%', pct: 69.5 },
                  { label: 'Patient Precision',      val: '19.6%', pct: 19.6 },
                ].map(({ label, val, pct }) => (
                  <div key={label} className={styles.metricRow}>
                    <div className={styles.metricRowTop}>
                      <span className={styles.metricRowLabel}>{label}</span>
                      <span className={`font-mono ${styles.metricRowVal}`}>{val}</span>
                    </div>
                    <div className="stat-bar-track">
                      <motion.div
                        className="stat-bar-fill"
                        style={{ background: 'var(--gradient-cyan)' }}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${pct}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.8, delay: 0.2 }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── CTA FOOTER ────────────────────────────── */}
      <section className={styles.ctaSection}>
        <div className="container">
          <motion.div
            className={styles.ctaBox}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className={`font-display ${styles.ctaTitle}`}>Ready to Monitor Your ICU?</h2>
            <p className={styles.ctaSub}>Open the live dashboard and explore sepsis prediction in real-time.</p>
            <button className="btn btn-primary" style={{ fontSize: '1rem', padding: '0.85rem 2rem' }}
              onClick={() => navigate('/dashboard')} id="cta-footer-dashboard">
              Launch Dashboard <ArrowRight size={18} />
            </button>
          </motion.div>
        </div>
      </section>

      {/* ── FOOTER ────────────────────────────────── */}
      <footer className={styles.footer}>
        <div className="container">
          <div className={styles.footerInner}>
            <div>
              <div className={`font-display font-bold ${styles.footerLogo}`}>SepsisAI</div>
              <p className={styles.footerSub}>© 2024 SepsisAI. AI-Driven Clinical Excellence.</p>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                <span className="badge badge-info">HIPAA Ready</span>
                <span className="badge badge-info">SOC 2 Type II</span>
              </div>
            </div>
            <div className={styles.footerLinks}>
              <span className="section-label">Citation</span>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', maxWidth: 360, marginTop: '0.5rem' }}>
                Reyna M, et al. Early Prediction of Sepsis from Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine 48(2):210-217, 2020.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
