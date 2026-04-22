/* ============================================================
   HOSPITAL + PATIENT SYNTHETIC DATA SEED
   5 hospitals · 25-40 patients each · 6-20h history per patient
   ============================================================ */

export interface VitalSnapshot {
  hour: number
  hr: number
  sbp: number
  map: number
  temp: number
  spo2: number
  rr: number
  prob: number
}

export interface Patient {
  id: string
  hospitalId: string
  name: string
  age: number
  gender: 'M' | 'F'
  unit: string
  admissionHour: number
  icuHour: number
  diagnosis: string
  vitals: {
    hr: number; sbp: number; dbp: number; map: number
    temp: number; spo2: number; rr: number; glucose: number
  }
  sepsisProb: number
  priorityScore: number
  risk: 'High' | 'Medium' | 'Low'
  alerts: string[]
  history: VitalSnapshot[]
  isActive: boolean
}

export interface Hospital {
  id: string
  name: string
  city: string
  address: string
  adminEmail: string
  passwordHash: string   // plain text for demo — "SepsisAI2024"
  accentColor: string
  units: string[]
  bedsTotal: number
  established: string
}

// ─── Deterministic pseudo-random from seed ────────────────
function seededRandom(seed: number) {
  let s = seed
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff
    return s / 0x7fffffff
  }
}

function rndRange(rng: () => number, min: number, max: number, dec = 0) {
  const v = rng() * (max - min) + min
  return +v.toFixed(dec)
}

function pickRandom<T>(rng: () => number, arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)]
}

// ─── Diagnoses pool ───────────────────────────────────────
const DIAGNOSES = [
  'Pneumonia', 'Acute Respiratory Failure', 'Septic Shock', 'UTI',
  'Abdominal Sepsis', 'Meningitis', 'Post-operative Complications',
  'Cellulitis', 'Community-Acquired Pneumonia', 'Bacteremia',
  'Endocarditis', 'Peritonitis', 'Necrotizing Fasciitis',
  'Cholangitis', 'Diabetic Ketoacidosis', 'Pancreatitis',
]

// ─── Name pools ───────────────────────────────────────────
const FIRST_M = ['James','Michael','David','Robert','William','John','Thomas','Daniel','Christopher','Andrew','George','Henry','Edward','Charles','Benjamin','Samuel','Joseph','Richard','Mark','Steven']
const FIRST_F = ['Sarah','Emma','Olivia','Sophia','Isabella','Amelia','Charlotte','Emily','Jessica','Lauren','Rachel','Katherine','Michelle','Patricia','Sandra','Dorothy','Helen','Ruth','Marie','Anne']
const LAST    = ['Chen','Patel','Williams','Johnson','Kim','García','Martinez','Anderson','Thompson','White','Davis','Miller','Wilson','Moore','Taylor','Jackson','Harris','Martin','Lee','Walker','Hall','Allen','Young','King','Scott','Green','Baker','Adams','Nelson','Carter']

// ─── Build synthetic history ──────────────────────────────
function buildHistory(rng: () => number, baseProb: number, hours: number): VitalSnapshot[] {
  const hist: VitalSnapshot[] = []
  let prob = Math.max(0, baseProb - rng() * 0.18)
  let hr   = rndRange(rng, 65, 130)
  let sbp  = rndRange(rng, 85, 155)
  let map_ = rndRange(rng, 58, 110)
  let temp = rndRange(rng, 36.2, 40.0, 1)
  let spo2 = rndRange(rng, 89, 100, 1)
  let rr   = rndRange(rng, 11, 34)

  for (let h = 1; h <= hours; h++) {
    // Drift each vital slightly each hour
    hr   = Math.min(160, Math.max(45,  hr   + (rng() - 0.48) * 6))
    sbp  = Math.min(200, Math.max(70,  sbp  + (rng() - 0.47) * 8))
    map_ = Math.min(140, Math.max(50,  map_ + (rng() - 0.47) * 6))
    temp = Math.min(41,  Math.max(35.5,temp + (rng() - 0.48) * 0.25))
    spo2 = Math.min(100, Math.max(85,  spo2 + (rng() - 0.4)  * 1.2))
    rr   = Math.min(40,  Math.max(8,   rr   + (rng() - 0.47) * 2))
    prob = Math.min(1,   Math.max(0,   prob + (rng() - 0.42) * 0.07))

    hist.push({
      hour: h,
      hr:   +hr.toFixed(0),
      sbp:  +sbp.toFixed(0),
      map:  +map_.toFixed(0),
      temp: +temp.toFixed(1),
      spo2: +spo2.toFixed(1),
      rr:   +rr.toFixed(0),
      prob: +prob.toFixed(3),
    })
  }
  return hist
}

// ─── Build one patient ────────────────────────────────────
function buildPatient(rng: () => number, hospitalId: string, idx: number,units: string[]): Patient {
  const isMale    = rng() > 0.44
  const firstName = pickRandom(rng, isMale ? FIRST_M : FIRST_F)
  const lastName  = pickRandom(rng, LAST)
  const age       = Math.floor(rng() * 55) + 28          // 28-82
  const severity  = rng()                                  // 0-1 drives everything
  const hoursOfHistory = Math.floor(rng() * 15) + 6       // 6-20

  // Vital generation driven by severity
  const hr    = rndRange(rng, 58 + severity * 50,  85 + severity * 60)
  const sbp   = rndRange(rng, 160 - severity * 80, 175 - severity * 60)
  const dbp   = rndRange(rng, 90  - severity * 40, 105 - severity * 30)
  const map_  = rndRange(rng, 110 - severity * 55, 120 - severity * 40)
  const temp  = rndRange(rng, 36.5 + severity * 2.5, 37.0 + severity * 3.2, 1)
  const spo2  = rndRange(rng, 100 - severity * 14, 100 - severity * 4, 1)
  const rr    = rndRange(rng, 12 + severity * 14,  16 + severity * 22)
  const glucose = rndRange(rng, 80 + severity * 100, 110 + severity * 200)

  // Clinical formula for sepsis probability
  const prob_ = Math.min(1, Math.max(0,
    0.25 * Math.min(1, Math.max(0, (hr - 60) / 80)) +
    0.20 * Math.min(1, Math.max(0, (100 - sbp) / 50)) +
    0.20 * Math.min(1, Math.max(0, (100 - spo2) / 20)) +
    0.15 * Math.min(1, Math.max(0, (rr - 12) / 28)) +
    0.10 * Math.min(1, Math.max(0, (temp - 36) / 5)) +
    0.10 * Math.min(1, Math.max(0, (70 - map_) / 30))
  ))
  const sepsisProb = +(prob_ + (rng() - 0.5) * 0.06).toFixed(3)
  const hrR    = hr > 100 ? 1 : 0
  const bpR    = Math.min(1, (map_ < 65 ? 1 : 0) + (sbp < 90 ? 0.5 : 0))
  const priorityScore = +(Math.min(1, 0.6 * sepsisProb + 0.2 * hrR + 0.2 * bpR)).toFixed(3)
  const risk: Patient['risk'] = priorityScore > 0.78 ? 'High' : priorityScore > 0.48 ? 'Medium' : 'Low'

  const alerts: string[] = []
  if (sepsisProb > 0.85)  alerts.push('Sepsis probability > 85%')
  if (sbp < 90)           alerts.push(`Low SBP: ${sbp} mmHg`)
  if (map_ < 65)          alerts.push(`Low MAP: ${map_} mmHg`)
  if (spo2 < 92)          alerts.push(`Critical SpO₂: ${spo2}%`)
  if (hr > 130)           alerts.push(`Tachycardia: ${hr} bpm`)
  if (temp > 39.5)        alerts.push(`Fever: ${temp}°C`)
  if (rr > 30)            alerts.push(`Tachypnea: RR ${rr}`)

  const paddedIdx = String(idx + 100).padStart(3, '0')

  return {
    id: `${hospitalId.toUpperCase().slice(0, 3)}-${paddedIdx}`,
    hospitalId,
    name: `${firstName} ${lastName}`,
    age,
    gender: isMale ? 'M' : 'F',
    unit: pickRandom(rng, units),
    admissionHour: rndRange(rng, 2, 48),
    icuHour: rndRange(rng, 1, hoursOfHistory),
    diagnosis: pickRandom(rng, DIAGNOSES),
    vitals: { hr, sbp, dbp, map: map_, temp, spo2, rr, glucose },
    sepsisProb,
    priorityScore,
    risk,
    alerts,
    history: buildHistory(rng, sepsisProb, hoursOfHistory),
    isActive: true,
  }
}

// ─── Hospital definitions ─────────────────────────────────
export const HOSPITALS: Hospital[] = [
  {
    id: 'CGH',
    name: 'City General Hospital',
    city: 'New York, NY',
    address: '550 First Avenue, Manhattan, NY 10016',
    adminEmail: 'admin@citygeneral.com',
    passwordHash: 'SepsisAI2024',
    accentColor: '#06b6d4',
    units: ['MICU', 'SICU', 'CCU', 'NICU', 'TICU'],
    bedsTotal: 450,
    established: '1902',
  },
  {
    id: 'SMM',
    name: "St. Mary's Medical Center",
    city: 'Chicago, IL',
    address: '2233 West Division Street, Chicago, IL 60622',
    adminEmail: 'admin@stmarys.com',
    passwordHash: 'SepsisAI2024',
    accentColor: '#8b5cf6',
    units: ['MICU', 'CSICU', 'Neuro-ICU', 'PICU'],
    bedsTotal: 320,
    established: '1918',
  },
  {
    id: 'PCH',
    name: 'Pacific Coast Hospital',
    city: 'Los Angeles, CA',
    address: '1300 N Vermont Ave, Los Angeles, CA 90027',
    adminEmail: 'admin@pacificcoast.com',
    passwordHash: 'SepsisAI2024',
    accentColor: '#10b981',
    units: ['MICU', 'SICU', 'BICU', 'CCU'],
    bedsTotal: 275,
    established: '1955',
  },
  {
    id: 'NHS',
    name: 'Northside Health System',
    city: 'Atlanta, GA',
    address: '1000 Johnson Ferry Rd NE, Atlanta, GA 30342',
    adminEmail: 'admin@northside.com',
    passwordHash: 'SepsisAI2024',
    accentColor: '#f59e0b',
    units: ['MICU', 'CICU', 'SICU', 'PICU', 'NICU'],
    bedsTotal: 390,
    established: '1971',
  },
  {
    id: 'MVH',
    name: 'Mountain View Hospital',
    city: 'Denver, CO',
    address: '4700 E Hale Pkwy, Denver, CO 80220',
    adminEmail: 'admin@mountainview.com',
    passwordHash: 'SepsisAI2024',
    accentColor: '#ef4444',
    units: ['MICU', 'SICU', 'CCU', 'Trauma-ICU'],
    bedsTotal: 210,
    established: '1988',
  },
]

// ─── Generate all patients per hospital ──────────────────
function generateHospitalPatients(hospital: Hospital, seed: number, count: number): Patient[] {
  const rng = seededRandom(seed)
  const patients: Patient[] = []
  for (let i = 0; i < count; i++) {
    patients.push(buildPatient(rng, hospital.id, i, hospital.units))
  }
  return patients.sort((a, b) => b.priorityScore - a.priorityScore)
}

// ─── Pre-seeded patient counts per hospital ───────────────
const PATIENT_COUNTS: Record<string, number> = {
  CGH: 38, SMM: 30, PCH: 25, NHS: 35, MVH: 28,
}

// ─── MASTER EXPORT ─────────────────────────────────────────
export const HOSPITAL_PATIENTS: Record<string, Patient[]> = Object.fromEntries(
  HOSPITALS.map((h, i) => [
    h.id,
    generateHospitalPatients(h, (i + 1) * 7919, PATIENT_COUNTS[h.id]),
  ])
)

export function getHospitalById(id: string): Hospital | undefined {
  return HOSPITALS.find(h => h.id === id)
}

export function getHospitalPatients(hospitalId: string): Patient[] {
  return (HOSPITAL_PATIENTS[hospitalId] ?? []).filter(p => p.isActive)
}
