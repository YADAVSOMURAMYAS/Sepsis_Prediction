import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { PatientProvider } from './context/PatientContext'
import ProtectedRoute from './components/ProtectedRoute'
import Navbar from './components/Navbar'
import ParticleBackground from './components/ParticleBackground'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import PatientsPage from './pages/PatientsPage'
import LoginPage from './pages/auth/LoginPage'

export default function App() {
  const location = useLocation()
  const isAuth = location.pathname === '/login'

  return (
    <ThemeProvider>
      <AuthProvider>
        <PatientProvider>
          <ParticleBackground />
          {!isAuth && <Navbar />}
          <AnimatePresence mode="wait">
            <Routes location={location} key={location.pathname}>
              <Route path="/"       element={<LandingPage />} />
              <Route path="/login"  element={<LoginPage />} />
              <Route path="/dashboard" element={
                <ProtectedRoute><Dashboard /></ProtectedRoute>
              } />
              <Route path="/patients" element={
                <ProtectedRoute><PatientsPage /></ProtectedRoute>
              } />
            </Routes>
          </AnimatePresence>
        </PatientProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
