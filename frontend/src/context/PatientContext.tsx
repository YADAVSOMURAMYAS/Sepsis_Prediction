import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import { patientsApi } from '../api/patients'
import type { Patient } from '../api/patients'
import { useAuth } from './AuthContext'

interface PatientContextType {
  patients:        Patient[]
  loading:         boolean
  error:           string | null
  refresh:         () => Promise<void>
  addPatient:      (payload: Parameters<typeof patientsApi.create>[0]) => Promise<Patient>
  dischargePatient:(id: string) => Promise<void>
}

const PatientContext = createContext<PatientContextType>({
  patients: [], loading: false, error: null,
  refresh: async () => {},
  addPatient: async () => { throw new Error('not ready') },
  dischargePatient: async () => {},
})

export function PatientProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!isAuthenticated) return
    setLoading(true)
    setError(null)
    try {
      const data = await patientsApi.list()
      setPatients(data.sort((a, b) => b.priority_score - a.priority_score))
    } catch (e: any) {
      setError(e.message || 'Failed to load patients')
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated])

  useEffect(() => { refresh() }, [refresh])

  const addPatient = useCallback(async (payload: Parameters<typeof patientsApi.create>[0]) => {
    const newPat = await patientsApi.create(payload)
    setPatients(prev =>
      [...prev, newPat].sort((a, b) => b.priority_score - a.priority_score)
    )
    return newPat
  }, [])

  const dischargePatient = useCallback(async (id: string) => {
    await patientsApi.discharge(id)
    setPatients(prev => prev.filter(p => p.id !== id))
  }, [])

  return (
    <PatientContext.Provider value={{ patients, loading, error, refresh, addPatient, dischargePatient }}>
      {children}
    </PatientContext.Provider>
  )
}

export const usePatients = () => useContext(PatientContext)
