import { useEffect, useState } from 'react'
import api from '../lib/api'
import { useToast } from '../contexts/ToastContext'
import SuggestedEditModal from '../components/SuggestedEditModal'

export default function SuggestedTransactionsPage() {
  const [list, setList] = useState<any[]>([])
  const [selected, setSelected] = useState<any | null>(null)
  const { push } = useToast()

  const load = async () => {
    const { data } = await api.get('/suggested-transactions')
    setList(data)
  }

  useEffect(() => { load() }, [])

  const approve = async (id: number) => {
    try {
      await api.post(`/suggested-transactions/${id}/approve`)
      push('Approved', 'success')
      load()
    } catch {
      push('Failed to approve', 'error')
    }
  }

  const reject = async (id: number) => {
    try {
      await api.post(`/suggested-transactions/${id}/reject`)
      push('Rejected', 'info')
      load()
    } catch {
      push('Failed to reject', 'error')
    }
  }

  const bulkApprove = async () => {
    const ids = list.filter((s) => s.selected).map((s) => s.id)
    if (!ids.length) return push('No items selected', 'info')
    try {
      await api.post('/suggested-transactions/bulk-approve', ids)
      push('Bulk approved', 'success')
      load()
    } catch {
      push('Bulk approve failed', 'error')
    }
  }

  const bulkReject = async () => {
    const ids = list.filter((s) => s.selected).map((s) => s.id)
    if (!ids.length) return push('No items selected', 'info')
    try {
      await api.post('/suggested-transactions/bulk-reject', ids)
      push('Bulk rejected', 'info')
      load()
    } catch {
      push('Bulk reject failed', 'error')
    }
  }

  const toggleSelect = (id: number) => {
    setList((l) => l.map((s) => s.id === id ? { ...s, selected: !s.selected } : s))
  }

  return (
    <div className="page">
      <header className="page-header"><h2>Suggested Transactions</h2></header>
      <div className="actions-row">
        <button className="btn-primary" onClick={bulkApprove}>Bulk Approve</button>
        <button className="btn-secondary" onClick={bulkReject}>Bulk Reject</button>
      </div>
      <div className="suggestion-list">
        {list.map((s) => (
          <div key={s.id} className={`suggestion-card ${s.status}`}>
            <input type="checkbox" checked={!!s.selected} onChange={() => toggleSelect(s.id)} />
            <div className="suggestion-main">
              <div><strong>{s.transaction_type}</strong> ₹{s.amount}</div>
              <div className="muted">{s.description}</div>
            </div>
            <div className="suggestion-actions">
              <button className="btn-primary" onClick={() => approve(s.id)}>Approve</button>
              <button className="btn-secondary" onClick={() => reject(s.id)}>Reject</button>
              <button className="btn-secondary" onClick={() => setSelected(s)}>Edit</button>
            </div>
          </div>
        ))}
      </div>
      <SuggestedEditModal suggestion={selected} onClose={() => setSelected(null)} onSave={() => { setSelected(null); load() }} />
    </div>
  )
}
