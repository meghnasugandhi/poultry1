import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Package, FileText, DollarSign, BarChart3, Calculator,
  MessageSquare, Bell, Settings, LogOut, Sun, Moon, Mic,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'
import api from '../lib/api'
import { useState, useEffect } from 'react'

const navKeys = [
  { to: '/', icon: LayoutDashboard, key: 'dashboard' },
  { to: '/inventory', icon: Package, key: 'inventory' },
  { to: '/documents', icon: FileText, key: 'documents' },
  { to: '/finance', icon: DollarSign, key: 'finance' },
  { to: '/reports', icon: BarChart3, key: 'reports' },
  { to: '/calculator', icon: Calculator, key: 'calculator' },
  { to: '/assistant', icon: MessageSquare, key: 'assistant' },
  { to: '/suggested-transactions', icon: FileText, key: 'suggested_transactions' },
  { to: '/notifications', icon: Bell, key: 'notifications' },
  { to: '/settings', icon: Settings, key: 'settings' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()
  const { refreshUser } = useAuth()
  const { reload, language } = useLanguage()
  const [langLoading, setLangLoading] = useState(false)
  const [suggestedCount, setSuggestedCount] = useState(0)

  const loadSuggestedCount = async () => {
    try {
      const { data } = await api.get('/suggested-transactions')
      const count = data.filter((s: any) => s.status === 'suggested').length
      setSuggestedCount(count)
    } catch {
      setSuggestedCount(0)
    }
  }

  useEffect(() => { loadSuggestedCount() }, [])

  const LANGUAGES = [
    { code: 'en', label: 'English' },
    { code: 'kn', label: 'Kannada' },
    { code: 'hi', label: 'Hindi' },
    { code: 'te', label: 'Telugu' },
    { code: 'ta', label: 'Tamil' },
    { code: 'ml', label: 'Malayalam' },
    { code: 'mr', label: 'Marathi' },
  ]

  const changeLanguage = async (v: string) => {
    if (!user) return
    try {
      setLangLoading(true)
      await api.put('/auth/settings', { preferred_language: v })
      await refreshUser()
      await reload()
    } finally {
      setLangLoading(false)
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Poultry ERP</h1>
          <p>{user?.farm_name}</p>
        </div>
        <nav className="sidebar-nav">
          {navKeys.map(({ to, icon: Icon, key }) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Icon size={20} />
              <span>{t(key)}</span>
              {key === 'suggested_transactions' && suggestedCount > 0 && (
                <span className="badge">{suggestedCount}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button onClick={toggleTheme} className="icon-btn" title="Toggle theme">
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
          <NavLink to="/voice" className="icon-btn" title={t('voice')}>
            <Mic size={20} />
          </NavLink>
          <button onClick={logout} className="icon-btn" title={t('logout')}>
            <LogOut size={20} />
          </button>
        </div>
      </aside>
      <main className="main-content">
        <div className="topbar">
          <div className="topbar-left">{/* place for local data / breadcrumbs */}</div>
          <div className="topbar-right">
            <div className="language-select-wrapper">
              <select value={user?.preferred_language || language} onChange={(e) => changeLanguage(e.target.value)} disabled={langLoading}>
                {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
              <span className="language-dropdown-icon">▾</span>
            </div>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
