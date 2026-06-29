import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Package, FileText, DollarSign, BarChart3, Calculator,
  MessageSquare, Bell, Settings, LogOut, Sun, Moon, Mic,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'

const navKeys = [
  { to: '/', icon: LayoutDashboard, key: 'dashboard' },
  { to: '/inventory', icon: Package, key: 'inventory' },
  { to: '/documents', icon: FileText, key: 'documents' },
  { to: '/finance', icon: DollarSign, key: 'finance' },
  { to: '/reports', icon: BarChart3, key: 'reports' },
  { to: '/calculator', icon: Calculator, key: 'calculator' },
  { to: '/assistant', icon: MessageSquare, key: 'assistant' },
  { to: '/notifications', icon: Bell, key: 'notifications' },
  { to: '/settings', icon: Settings, key: 'settings' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()

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
        <Outlet />
      </main>
    </div>
  )
}
