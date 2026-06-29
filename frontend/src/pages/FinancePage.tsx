import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'

interface Summary {
  monthly_revenue: number
  monthly_expenses: number
  profit_loss: number
  revenue_breakdown: Record<string, number>
  expense_breakdown: Record<string, number>
}

interface Transaction {
  id: number
  transaction_type: string
  revenue_category: string | null
  expense_category: string | null
  amount: number
  description: string | null
  transaction_date: string
}

export default function FinancePage() {
  const { t } = useLanguage()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    transaction_type: 'expense',
    revenue_category: 'bird_sales',
    expense_category: 'feed',
    amount: '',
    description: '',
    transaction_date: new Date().toISOString().split('T')[0],
  })

  const load = () => {
    api.get('/finance/summary').then(({ data }) => setSummary(data))
    api.get('/finance/transactions').then(({ data }) => setTransactions(data))
  }

  useEffect(() => { load() }, [])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/finance/transactions', {
      transaction_type: form.transaction_type,
      revenue_category: form.transaction_type === 'revenue' ? form.revenue_category : null,
      expense_category: form.transaction_type === 'expense' ? form.expense_category : null,
      amount: parseFloat(form.amount),
      description: form.description || null,
      transaction_date: form.transaction_date,
    })
    setShowForm(false)
    setForm({ ...form, amount: '', description: '' })
    load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm(t('delete_transaction_confirm'))) return
    await api.delete(`/finance/transactions/${id}`)
    load()
  }

  if (!summary) return <div className="page"><p>{t('loading')}</p></div>

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t('finance')}</h2>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}><Plus size={18} /> {t('add_transaction')}</button>
      </header>

      <div className="cards-grid finance-summary">
        <div className="stat-card"><p className="stat-label">{t('monthly_revenue')}</p><p className="stat-value positive">₹{summary.monthly_revenue.toLocaleString()}</p></div>
        <div className="stat-card"><p className="stat-label">{t('monthly_expenses')}</p><p className="stat-value negative">₹{summary.monthly_expenses.toLocaleString()}</p></div>
        <div className="stat-card"><p className="stat-label">{t('profit_loss')}</p><p className={`stat-value ${summary.profit_loss >= 0 ? 'positive' : 'negative'}`}>₹{Math.abs(summary.profit_loss).toLocaleString()}</p></div>
      </div>

      {showForm && (
        <form className="chart-card inline-form expanded" onSubmit={handleAdd}>
          <select value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value })}>
            <option value="expense">{t('expense')}</option>
            <option value="revenue">{t('revenue')}</option>
          </select>
          {form.transaction_type === 'expense' ? (
            <select value={form.expense_category} onChange={(e) => setForm({ ...form, expense_category: e.target.value })}>
              {['feed', 'medicines', 'vaccines', 'labor', 'electricity', 'transport', 'miscellaneous'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          ) : (
            <select value={form.revenue_category} onChange={(e) => setForm({ ...form, revenue_category: e.target.value })}>
              {['bird_sales', 'egg_sales', 'other_income'].map((c) => (
                <option key={c} value={c}>{c.replace('_', ' ')}</option>
              ))}
            </select>
          )}
          <input type="number" placeholder={`${t('amount')} (₹)`} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
          <input type="date" value={form.transaction_date} onChange={(e) => setForm({ ...form, transaction_date: e.target.value })} />
          <input placeholder={t('description')} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <button type="submit" className="btn-primary">{t('save')}</button>
        </form>
      )}

      <div className="breakdown-grid">
        <div className="chart-card">
          <h3>{t('revenue_breakdown')}</h3>
          {Object.entries(summary.revenue_breakdown).filter(([, v]) => v > 0).map(([k, v]) => (
            <div key={k} className="breakdown-row"><span>{k.replace(/_/g, ' ')}</span><span>₹{v.toLocaleString()}</span></div>
          ))}
          {Object.values(summary.revenue_breakdown).every((v) => v === 0) && <p className="empty-state">{t('no_revenue')}</p>}
        </div>
        <div className="chart-card">
          <h3>{t('expense_breakdown')}</h3>
          {Object.entries(summary.expense_breakdown).filter(([, v]) => v > 0).map(([k, v]) => (
            <div key={k} className="breakdown-row"><span>{k.replace(/_/g, ' ')}</span><span>₹{v.toLocaleString()}</span></div>
          ))}
          {Object.values(summary.expense_breakdown).every((v) => v === 0) && <p className="empty-state">{t('no_expenses')}</p>}
        </div>
      </div>

      <div className="chart-card" style={{ marginTop: '1.5rem' }}>
        <h3>{t('recent_transactions')}</h3>
        <div className="table-container">
          <table>
            <thead><tr><th>{t('date')}</th><th>{t('type')}</th><th>{t('category')}</th><th>{t('amount')}</th><th>{t('description')}</th><th></th></tr></thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id}>
                  <td>{tx.transaction_date}</td>
                  <td><span className="badge">{tx.transaction_type}</span></td>
                  <td>{(tx.expense_category || tx.revenue_category || '').replace(/_/g, ' ')}</td>
                  <td className={tx.transaction_type === 'revenue' ? 'positive' : 'negative'}>₹{tx.amount.toLocaleString()}</td>
                  <td>{tx.description || '—'}</td>
                  <td><button className="icon-btn-sm danger" onClick={() => handleDelete(tx.id)}><Trash2 size={14} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
