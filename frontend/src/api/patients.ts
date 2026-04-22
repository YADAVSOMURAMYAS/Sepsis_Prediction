import { apiFetch } from './client'

export interface VitalHistory {
  hour: number; hr: number; sbp: number; map: number
  temp: number; spo2: number; rr: number; prob: number
}

export interface Patient {
  id:             string
  hospital_id:    string
  name:           string
  age:            number
  gender:         'M' | 'F'
  unit:           string
  diagnosis:      string
  admission_hour: number
  icu_hour:       number
  hr: number; sbp: number; dbp: number; map: number
  temp: number; spo2: number; rr: number; glucose: number
  sepsis_prob:    number
  priority_score: number
  risk:           'High' | 'Medium' | 'Low'
  alerts:         string[]
  is_active:      boolean
  history:        VitalHistory[]
}

export interface PatientCreatePayload {
  name: string; age: number; gender: string; unit: string; diagnosis: string
  hr: number; sbp: number; dbp: number; map: number
  temp: number; spo2: number; rr: number; glucose: number
}

export const patientsApi = {
  list: () => apiFetch<Patient[]>('/patients'),

  create: (payload: PatientCreatePayload) =>
    apiFetch<Patient>('/patients', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  discharge: (patientId: string) =>
    apiFetch<Patient>(`/patients/${patientId}/discharge`, { method: 'POST' }),

  history: (patientId: string) =>
    apiFetch<VitalHistory[]>(`/patients/${patientId}/history`),
}
