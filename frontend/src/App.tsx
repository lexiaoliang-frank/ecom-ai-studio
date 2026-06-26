import { useState, createContext, useContext, useCallback, type ReactNode } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'

// Simple auth context
interface AuthState {
  token: string | null
  user: { id: string; email: string; name: string; tenant_id: string } | null
}

const AuthContext = createContext<{
  auth: AuthState
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}>({
  auth: { token: null, user: null },
  login: async () => {},
  logout: () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}

export default function App() {
  const [auth, setAuth] = useState<AuthState>(() => {
    const token = localStorage.getItem('token')
    const user = localStorage.getItem('user')
    if (token && user) {
      return { token, user: JSON.parse(user) }
    }
    return { token: null, user: null }
  })

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify({
      id: data.user_id,
      email: data.email,
      name: data.name,
      tenant_id: data.tenant_id,
    }))
    setAuth({ token: data.access_token, user: {
      id: data.user_id,
      email: data.email,
      name: data.name,
      tenant_id: data.tenant_id,
    }})
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setAuth({ token: null, user: null })
  }, [])

  return (
    <AuthContext.Provider value={{ auth, login, logout }}>
      <Routes>
        <Route path="/login" element={auth.token ? <Navigate to="/" /> : <LoginPage />} />
        <Route path="/*" element={auth.token ? <DashboardPage /> : <Navigate to="/login" />} />
      </Routes>
    </AuthContext.Provider>
  )
}
