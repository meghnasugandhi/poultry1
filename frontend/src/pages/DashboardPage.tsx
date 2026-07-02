import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Bird, Package, Pill, Syringe, TrendingUp, TrendingDown, Scale, Sparkles, AlertTriangle, ClipboardList, Activity } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from 'recharts'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'

interface DashboardData {
  total_birds: number
  feed_stock: number
  medicine_stock: number
  vaccine_stock: number
  monthly_revenue: number
  monthly_expenses: number
  profit_loss: number
  farm_name: string
  owner_name: string
  revenue_trend: { month: string; revenue: number; expenses: number }[]
  feed_consumption_trend: { month: string; feed: number }[]
  inventory_trend: { month: string; feed: number; medicine: number; vaccine: number }[]
  pending_bills: number
  recent_expenses: number
  low_stock_items: string[]
  vaccination_alerts: string[]
  mortality_alerts: string[]
  ai_summary: { insights: string[]; suggested_actions: string[]; summary: string }
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08 } }),
}

const sanitizeText = (value: string) =>
  value
    .replace(/Gemini_Generated_Image_[A-Za-z0-9_-]+\.(png|jpg|jpeg|webp)/gi, 'Generated image')
    .replace(/\.(png|jpg|jpeg|webp)/gi, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

export default function DashboardPage() {
  const { t, language } = useLanguage()
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    api.get('/dashboard/', { params: { language } }).then(({ data: d }) => setData(d))
  }, [language])

  const cards = data ? [
    { label: t('total_birds'), value: data.total_birds.toLocaleString(), icon: Bird, color: '#4f46e5' },
    { label: t('feed_stock'), value: `${data.feed_stock} kg`, icon: Package, color: '#059669' },
    { label: t('medicine_stock'), value: `${data.medicine_stock} units`, icon: Pill, color: '#d97706' },
    { label: t('vaccine_stock'), value: `${data.vaccine_stock} doses`, icon: Syringe, color: '#7c3aed' },
    { label: t('monthly_revenue'), value: `₹${data.monthly_revenue.toLocaleString()}`, icon: TrendingUp, color: '#10b981' },
    { label: t('monthly_expenses'), value: `₹${data.monthly_expenses.toLocaleString()}`, icon: TrendingDown, color: '#ef4444' },
    { label: t('profit_loss'), value: `₹${Math.abs(data.profit_loss).toLocaleString()}`, icon: Scale, color: data.profit_loss >= 0 ? '#10b981' : '#ef4444' },
  ] : []

  return (
    <div className="page dashboard-page">
      <header className="page-header dashboard-header">
        <div>
          <h2>{t('dashboard')}</h2>
          <p>{t('welcome')}, {data?.owner_name || 'Farmer'}</p>
        </div>
      </header>

      <div className="cards-grid dashboard-stat-grid">
        {cards.map((card, i) => (
          <motion.div key={card.label} className="stat-card" custom={i} variants={cardVariants} initial="hidden" animate="visible">
            <div className="stat-icon" style={{ background: `${card.color}20`, color: card.color }}>
              <card.icon size={24} />
            </div>
            <div>
              <p className="stat-label">{card.label}</p>
              <p className="stat-value">{card.value}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {data && (
        <div className="dashboard-feature-grid">
          <motion.div className="chart-card dashboard-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="dashboard-panel-title">
              <Sparkles size={18} color="#4f46e5" />
              <h3>{t('ai_summary_card')}</h3>
            </div>
            <p className="dashboard-muted-copy">{sanitizeText(data.ai_summary.summary)}</p>
            <ul className="dashboard-list">
              {data.ai_summary.insights.map((insight, index) => (
                <li key={index}>{sanitizeText(insight)}</li>
              ))}
            </ul>
            <div className="dashboard-action-stack">
              {data.ai_summary.suggested_actions.map((action, index) => (
                <div key={index} className="dashboard-action-note">{sanitizeText(action)}</div>
              ))}
            </div>
          </motion.div>

          <motion.div className="chart-card dashboard-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.08 }}>
            <div className="dashboard-panel-title">
              <Activity size={18} color="#059669" />
              <h3>{t('todays_activity')}</h3>
            </div>
            <div className="activity-list">
              <div><span>{t('pending_bills')}</span><strong>{data.pending_bills}</strong></div>
              <div><span>{t('recent_expenses')}</span><strong>₹{data.recent_expenses.toLocaleString()}</strong></div>
              <div><span>{t('low_stock_alerts')}</span><strong>{data.low_stock_items.length}</strong></div>
              <div><span>{t('vaccination_alerts')}</span><strong>{data.vaccination_alerts.length}</strong></div>
            </div>
          </motion.div>
        </div>
      )}

      {data && (
        <div className="dashboard-info-grid">
          <motion.div className="chart-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.12 }}>
            <div className="dashboard-panel-title">
              <AlertTriangle size={18} color="#ef4444" />
              <h3>{t('alerts')}</h3>
            </div>
            <div className="dashboard-text-list">
              {data.low_stock_items.length > 0 ? data.low_stock_items.map((item) => <div key={item}>• {item}</div>) : <div>{t('no_low_stock_alerts')}</div>}
              {data.vaccination_alerts.map((item) => <div key={item}>• {item}</div>)}
              {data.mortality_alerts.map((item) => <div key={item}>• {item}</div>)}
            </div>
          </motion.div>

          <motion.div className="chart-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.16 }}>
            <div className="dashboard-panel-title">
              <ClipboardList size={18} color="#d97706" />
              <h3>{t('suggested_actions')}</h3>
            </div>
            <div className="dashboard-text-list">
              {data.ai_summary.suggested_actions.map((action, index) => <div key={index}>• {sanitizeText(action)}</div>)}
            </div>
          </motion.div>
        </div>
      )}

      {data && (
        <div className="dashboard-chart-grid">
          <motion.div className="chart-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h3>{t('revenue_expense_trend')}</h3>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={data.revenue_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip />
                <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="#10b98130" name={t('revenue')} />
                <Area type="monotone" dataKey="expenses" stroke="#ef4444" fill="#ef444430" name={t('expenses')} />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>

          <motion.div className="chart-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
            <h3>{t('feed_consumption_trend')}</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.feed_consumption_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip />
                <Line type="monotone" dataKey="feed" stroke="#059669" strokeWidth={2} name={`${t('feed')} (kg)`} />
              </LineChart>
            </ResponsiveContainer>
          </motion.div>

          <motion.div className="chart-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
            <h3>{t('inventory_trend')}</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.inventory_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="feed" stroke="#059669" name={t('feed')} />
                <Line type="monotone" dataKey="medicine" stroke="#d97706" name={t('medicine')} />
                <Line type="monotone" dataKey="vaccine" stroke="#7c3aed" name={t('vaccine')} />
              </LineChart>
            </ResponsiveContainer>
          </motion.div>
        </div>
      )}
    </div>
  )
}
