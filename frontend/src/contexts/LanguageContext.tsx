import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import api from '../lib/api'
import { useAuth } from './AuthContext'

type Labels = Record<string, string>

interface LanguageContextType {
  labels: Labels
  language: string
  t: (key: string) => string
  reload: () => Promise<void>
}

const LanguageContext = createContext<LanguageContextType | null>(null)

const FALLBACK: Labels = {
  dashboard: 'Dashboard',
  inventory: 'Inventory',
  documents: 'Documents',
  finance: 'Finance',
  reports: 'Reports',
  calculator: 'Calculator',
  assistant: 'AI Assistant',
  notifications: 'Notifications',
  settings: 'Settings',
  voice: 'Voice Assistant',
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [labels, setLabels] = useState<Labels>(FALLBACK)
  const [language, setLanguage] = useState('en')

  const reload = async () => {
    if (!user) return
    try {
      const { data } = await api.get('/translations/ui')
      setLabels({ ...FALLBACK, ...data.labels })
      setLanguage(data.language)
    } catch {
      setLabels(FALLBACK)
    }
  }

  useEffect(() => {
    reload()
  }, [user?.preferred_language])

  const t = (key: string) => labels[key] || FALLBACK[key] || key

  return (
    <LanguageContext.Provider value={{ labels, language, t, reload }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}
