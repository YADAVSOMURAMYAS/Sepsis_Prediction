import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import styles from './AlertBanner.module.css'

interface AlertBannerProps {
  alerts: Array<{ patientId: string; message: string }>
}

export default function AlertBanner({ alerts }: AlertBannerProps) {
  if (!alerts.length) return null

  return (
    <motion.div
      className={styles.banner}
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className={styles.inner}>
        <div className={styles.iconWrap}>
          <motion.div
            animate={{ scale: [1, 1.15, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <AlertTriangle size={16} />
          </motion.div>
          <span className={styles.title}>CRITICAL ALERTS</span>
        </div>
        <div className={styles.messages}>
          {alerts.slice(0, 5).map((a, i) => (
            <span key={i} className={styles.item}>
              <strong>{a.patientId}</strong>: {a.message}
            </span>
          ))}
          {alerts.length > 5 && (
            <span className={styles.more}>+{alerts.length - 5} more</span>
          )}
        </div>
      </div>
    </motion.div>
  )
}
