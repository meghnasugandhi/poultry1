import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import api from '../lib/api'
import { useAuth } from './AuthContext'
import { TRANSLATIONS, type Dict, type LangCode } from '../i18n'

interface LanguageContextType {
  language: LangCode
  t: (key: string) => string
  setLanguage: (lang: LangCode) => void
  reload: () => Promise<void>
}

const LanguageContext = createContext<LanguageContextType | null>(null)

const STORAGE_KEY = 'lang'

function readStoredLang(): LangCode | null {
  const v = localStorage.getItem(STORAGE_KEY)
  return v && v in TRANSLATIONS ? (v as LangCode) : null
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [language, setLanguageState] = useState<LangCode>(readStoredLang() || 'en')

  // When the logged-in user's stored preference is known and no local override
  // exists yet, adopt the server-side preferred language.
  useEffect(() => {
    if (!user) return
    if (!readStoredLang() && user.preferred_language in TRANSLATIONS) {
      setLanguageState(user.preferred_language as LangCode)
    }
  }, [user?.preferred_language])

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const setLanguage = (lang: LangCode) => {
    setLanguageState(lang)
    localStorage.setItem(STORAGE_KEY, lang)
    if (localStorage.getItem('token')) {
      api.put('/auth/settings', { preferred_language: lang }).catch(() => {})
    }
  }

  const reload = async () => {
    if (!user) return
    if (user.preferred_language in TRANSLATIONS) {
      setLanguageState(user.preferred_language as LangCode)
      localStorage.setItem(STORAGE_KEY, user.preferred_language)
    }
  }

  const t = (key: string): string => {
    const dict: Dict = TRANSLATIONS[language] || TRANSLATIONS.en
    return dict[key] ?? TRANSLATIONS.en[key] ?? key
  }

  return (
    <LanguageContext.Provider value={{ language, t, setLanguage, reload }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider')
  return ctx
}
