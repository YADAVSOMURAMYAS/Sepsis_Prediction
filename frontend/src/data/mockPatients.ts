export interface Patient {
  id: string
  name: string
  age: number
  gender: 'M' | 'F'
  unit: string
  admissionHour: number
  icuHour: number
  vitals: {
    hr: number
    sbp: number
    dbp: number
    map: number
    temp: number
    spo2: number
    rr: number
    glucose: number
  }
  sepsisProb: number
  priorityScore: number
  risk: 'High' | 'Medium' | 'Low'
  alerts: string[]
  history: Array<{
    hour: number
    hr: number; sbp: number; map: number; temp: number; spo2: number; rr: number
    prob: number
  }>
}

function rnd(min: number, max: number, decimals = 0) {
  const v = Math.random() * (max - min) + min
  return +v.toFixed(decimals)
}

function buildHistory(baseProb: number, hours = 24) {
  const hist = []
  let prob = Math.max(0, Math.min(1, baseProb - 0.15))
  for (let h = 1; h <= hours; h++) {
    prob = Math.min(1, Math.max(0, prob + (Math.random() - 0.4) * 0.06))
    hist.push({
      hour: h,
      hr:   rnd(65, 145),
      sbp:  rnd(80, 160),
      map:  rnd(55, 115),
      temp: rnd(35.8, 40.2, 1),
      spo2: rnd(88, 100, 1),
      rr:   rnd(10, 36),
      prob: +prob.toFixed(3),
    })
  }
  return hist
}

function makePatient(idx: number): Patient {
  const severity = Math.random()
  const sepsisProb = Math.min(0.97, Math.max(0.03, severity * 0.9 + (Math.random() - 0.5) * 0.1))
  const priorityScore = Math.min(1, 0.6 * sepsisProb + 0.2 * (sepsisProb > 0.6 ? 1 : 0) + 0.2 * (Math.random() > 0.5 ? 0.5 : 0))
  const risk: Patient['risk'] = priorityScore > 0.8 ? 'High' : priorityScore > 0.5 ? 'Medium' : 'Low'

  const hr   = rnd(60, 145)
  const sbp  = rnd(80, 170)
  const dbp  = rnd(45, 110)
  const map  = rnd(55, 120)
  const temp = rnd(35.8, 40.5, 1)
  const spo2 = rnd(88, 100, 1)
  const rr   = rnd(10, 38)
  const glucose = rnd(65, 380)

  const alerts: string[] = []
  if (sepsisProb > 0.85) alerts.push('Sepsis probability > 85%')
  if (sbp < 90)          alerts.push(`Low SBP: ${sbp} mmHg`)
  if (map < 65)          alerts.push(`Low MAP: ${map} mmHg`)
  if (spo2 < 92)         alerts.push(`Critical SpO₂: ${spo2}%`)
  if (hr > 130)          alerts.push(`Tachycardia: ${hr} bpm`)
  if (temp > 39.5)       alerts.push(`Fever: ${temp}°C`)
  if (rr > 30)           alerts.push(`Tachypnea: RR ${rr}`)

  const firstNames = ['James','Sarah','Michael','Emma','David','Olivia','Daniel','Sophia','Robert','Amelia']
  const lastNames  = ['Chen','Patel','Williams','Johnson','Kim','García','Martinez','Anderson','Thompson','White']
  const units      = ['MICU','SICU','CCU','NICU','PICU']

  return {
    id:           `ICU-${100 + idx}`,
    name:         `${firstNames[idx % 10]} ${lastNames[(idx + 3) % 10]}`,
    age:          rnd(32, 88),
    gender:       Math.random() > 0.5 ? 'M' : 'F',
    unit:         units[idx % 5],
    admissionHour: rnd(2, 48),
    icuHour:      rnd(1, 72),
    vitals:       { hr, sbp, dbp, map, temp, spo2, rr, glucose },
    sepsisProb:   +sepsisProb.toFixed(3),
    priorityScore: +priorityScore.toFixed(3),
    risk,
    alerts,
    history:      buildHistory(sepsisProb),
  }
}

function seededPatients(n: number): Patient[] {
  const result: Patient[] = []
  // We just produce n patients; in real app these come from API
  for (let i = 0; i < n; i++) result.push(makePatient(i))
  return result.sort((a, b) => b.priorityScore - a.priorityScore)
}

export const MOCK_PATIENTS: Patient[] = seededPatients(20)

export const ICU_STATS = {
  totalPatients: 20,
  highRisk: MOCK_PATIENTS.filter(p => p.risk === 'High').length,
  mediumRisk: MOCK_PATIENTS.filter(p => p.risk === 'Medium').length,
  lowRisk: MOCK_PATIENTS.filter(p => p.risk === 'Low').length,
  totalAlerts: MOCK_PATIENTS.reduce((acc, p) => acc + p.alerts.length, 0),
  avgSepsisProb: +(MOCK_PATIENTS.reduce((a, p) => a + p.sepsisProb, 0) / MOCK_PATIENTS.length).toFixed(2),
}
