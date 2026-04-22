import { motion } from 'framer-motion'
import styles from './KpiCard.module.css'

interface KpiCardProps {
  label: string
  value: string | number
  sub?: string
  color?: 'default' | 'red' | 'amber' | 'green' | 'cyan'
  icon?: React.ReactNode
  delay?: number
}

const colorMap = {
  default: 'var(--text-primary)',
  red:     'var(--color-red)',
  amber:   'var(--color-amber)',
  green:   'var(--color-green)',
  cyan:    'var(--color-cyan)',
}

export default function KpiCard({ label, value, sub, color = 'default', icon, delay = 0 }: KpiCardProps) {
  return (
    <motion.div
      className={styles.card}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
    >
      <div className={styles.top}>
        <span className={`section-label ${styles.label}`}>{label}</span>
        {icon && <div className={styles.icon}>{icon}</div>}
      </div>
      <div className={styles.value} style={{ color: colorMap[color] }}>
        {value}
      </div>
      {sub && <div className={styles.sub}>{sub}</div>}
    </motion.div>
  )
}
