import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import api from '../lib/api'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: Record<string, string>) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    try {
      const { data } = await api.get('/auth/me')
      setUser(data)
    } catch {
      setUser(null)
    }
  }

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      refreshUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login/json', { email, password })
    localStorage.setItem('token', data.access_token)
    await refreshUser()
  }

  const register = async (formData: Record<string, string>) => {
    await api.post('/auth/register', formData)
    await login(formData.email, formData.password)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
