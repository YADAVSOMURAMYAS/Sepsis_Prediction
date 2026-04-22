import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import { authApi } from '../api/auth'
import type { HospitalInfo } from '../api/auth'

interface AuthState {
  isAuthenticated: boolean
  hospital: HospitalInfo | null
  token: string | null
}

interface AuthContextType extends AuthState {
  login:    (email: string, password: string) => Promise<void>
  logout:   () => void
  register: (payload: Parameters<typeof authApi.register>[0]) => Promise<void>
  loading:  boolean
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false, hospital: null, token: null,
  login: async () => {}, logout: () => {}, register: async () => {},
  loading: true,
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    hospital: null,
    token: localStorage.getItem('sepsisai_token'),
  })
  const [loading, setLoading] = useState(true)

  // On mount — restore session from stored token
  useEffect(() => {
    const token = localStorage.getItem('sepsisai_token')
    if (!token) { setLoading(false); return }

    authApi.me()
      .then(hospital => setState({ isAuthenticated: true, hospital, token }))
      .catch(() => {
        localStorage.removeItem('sepsisai_token')
        setState({ isAuthenticated: false, hospital: null, token: null })
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    localStorage.setItem('sepsisai_token', res.access_token)
    const hospital = await authApi.me()
    setState({ isAuthenticated: true, hospital, token: res.access_token })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('sepsisai_token')
    setState({ isAuthenticated: false, hospital: null, token: null })
  }, [])

  const register = useCallback(async (payload: Parameters<typeof authApi.register>[0]) => {
    const res = await authApi.register(payload)
    localStorage.setItem('sepsisai_token', res.access_token)
    const hospital = await authApi.me()
    setState({ isAuthenticated: true, hospital, token: res.access_token })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout, register, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
