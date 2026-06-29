import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Bird, Package, Pill, Syringe, TrendingUp, TrendingDown, Scale } from 'lucide-react'
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
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08 } }),
}

export default function DashboardPage() {
  const { t } = useLanguage()
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    api.get('/dashboard/').then(({ data: d }) => setData(d))
  }, [])

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
    <div className="page">
      <header className="page-header">
        <div>
          <h2>{t('dashboard')}</h2>
          <p>{t('welcome')}, {data?.owner_name || t('farmer')}</p>
        </div>
      </header>

      <div className="cards-grid">
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
        <div className="charts-grid multi">
          <motion.div className="chart-card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h3>{t('revenue_expense_trend')}</h3>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={data.revenue_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="month" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip />
                <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="#10b98130" name="Revenue" />
                <Area type="monotone" dataKey="expenses" stroke="#ef4444" fill="#ef444430" name="Expenses" />
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
                <Line type="monotone" dataKey="feed" stroke="#059669" strokeWidth={2} name="Feed (kg)" />
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
                <Line type="monotone" dataKey="feed" stroke="#059669" name="Feed" />
                <Line type="monotone" dataKey="medicine" stroke="#d97706" name="Medicine" />
                <Line type="monotone" dataKey="vaccine" stroke="#7c3aed" name="Vaccine" />
              </LineChart>
            </ResponsiveContainer>
          </motion.div>
        </div>
      )}
    </div>
  )
}
