import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import api from '../lib/api'
import { useAuth } from './AuthContext'
import en from '../locales/en.json'
import hi from '../locales/hi.json'

type Labels = Record<string, string>

interface LanguageContextType {
  labels: Labels
  language: string
  t: (key: string) => string
  reload: (languageOverride?: string) => Promise<void>
}

const LanguageContext = createContext<LanguageContextType | null>(null)

const FALLBACK: Labels = en as Labels

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [labels, setLabels] = useState<Labels>(FALLBACK)
  const [language, setLanguage] = useState('en')

  const reload = async (languageOverride?: string) => {
    const targetLanguage = languageOverride || user?.preferred_language || 'en'
    if (targetLanguage === 'hi') {
      setLabels({ ...FALLBACK, ...(hi as Labels) })
      setLanguage(targetLanguage)
      return
    }
    if (targetLanguage === 'en') {
      setLabels(FALLBACK)
      setLanguage(targetLanguage)
      return
    }
    if (!user) return
    try {
      const { data } = await api.get('/translations/ui')
      const nextLabels = { ...FALLBACK, ...data.labels }
      setLabels(nextLabels)
      setLanguage(data.language || targetLanguage)
    } catch {
      setLabels(FALLBACK)
      setLanguage('en')
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
