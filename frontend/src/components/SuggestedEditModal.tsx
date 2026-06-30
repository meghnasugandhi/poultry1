import { useEffect, useState } from 'react'
import { useToast } from '../contexts/ToastContext'
import api from '../lib/api'

export default function SuggestedEditModal({ suggestion, onClose, onSave }: any) {
  const [form, setForm] = useState<any>(suggestion)
  const { push } = useToast()

  useEffect(() => setForm(suggestion), [suggestion])

  if (!suggestion) return null

  const save = async () => {
    try {
      const { data } = await api.put(`/suggested-transactions/${suggestion.id}`, form)
      push('Suggestion updated', 'success')
      onSave(data)
    } catch (e) {
      push('Failed to update suggestion', 'error')
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <h3>Edit Suggested Transaction</h3>
        <div className="form-group">
          <label>Amount</label>
          <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} />
        </div>
        <div className="form-group">
          <label>Description</label>
          <input value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="modal-actions">
          <button className="btn-primary" onClick={save}>Save</button>
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}
