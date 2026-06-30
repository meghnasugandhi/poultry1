import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Plus, Mic, Pencil, Trash2, History } from 'lucide-react'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'
import { useSpeech } from '../hooks/useSpeech'
import type { InventoryItem } from '../types'

export default function InventoryPage() {
  const { t, language } = useLanguage()
  const { startListening, transcript, listening } = useSpeech(language)
  const [items, setItems] = useState<InventoryItem[]>([])
  const [categories, setCategories] = useState<string[]>(['feed', 'medicine', 'vaccine'])
  const [category, setCategory] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showCategoryInput, setShowCategoryInput] = useState(false)
  const [newCategory, setNewCategory] = useState('')
  const [editId, setEditId] = useState<number | null>(null)
  const [historyId, setHistoryId] = useState<number | null>(null)
  const [history, setHistory] = useState<{ change_amount: number; reason: string; created_at: string }[]>([])
  const [voiceText, setVoiceText] = useState('')
  const [form, setForm] = useState({
    category: 'feed', product_name: '', quantity: '', unit: 'kg',
    reorder_level: '10', expiry_date: '', supplier_name: '',
  })

  const load = () => {
    api.get('/inventory/', { params: category ? { category } : {} }).then(({ data }) => setItems(data))
  }

  useEffect(() => {
    const stored = window.localStorage.getItem('inventoryCategories')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          setCategories(parsed)
        }
      } catch {
        // ignore malformed storage
      }
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem('inventoryCategories', JSON.stringify(categories))
  }, [categories])

  useEffect(() => { load() }, [category])

  useEffect(() => {
    if (transcript) setVoiceText(transcript)
  }, [transcript])

  const resetForm = () => {
    setForm({ category: categories[0] || 'feed', product_name: '', quantity: '', unit: 'kg', reorder_level: '10', expiry_date: '', supplier_name: '' })
    setEditId(null)
    setShowForm(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      category: form.category,
      product_name: form.product_name,
      quantity: parseFloat(form.quantity),
      unit: form.unit,
      reorder_level: parseFloat(form.reorder_level),
      expiry_date: form.expiry_date || null,
      supplier_name: form.supplier_name || null,
    }
    if (editId) {
      await api.put(`/inventory/${editId}`, payload)
    } else {
      await api.post('/inventory/', payload)
    }
    resetForm()
    load()
  }

  const handleEdit = (item: InventoryItem) => {
    setEditId(item.id)
    setForm({
      category: item.category,
      product_name: item.product_name,
      quantity: String(item.quantity),
      unit: item.unit,
      reorder_level: '10',
      expiry_date: '',
      supplier_name: '',
    })
    setShowForm(true)
  }

  const createCategory = () => {
    const candidate = newCategory.trim().toLowerCase()
    if (!candidate) return
    if (!categories.includes(candidate)) {
      setCategories([...categories, candidate])
      setCategory(candidate)
    }
    setNewCategory('')
    setShowCategoryInput(false)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this item?')) return
    await api.delete(`/inventory/${id}`)
    load()
  }

  const showHistory = async (id: number) => {
    setHistoryId(id)
    const { data } = await api.get(`/inventory/${id}/history`)
    setHistory(data)
  }

  const handleVoiceEntry = async () => {
    const text = voiceText.trim()
    if (!text) return
    try {
      await api.post('/inventory/voice-entry', { text })
      setVoiceText('')
      load()
      alert('Stock added via voice command!')
    } catch {
      alert('Could not parse command. Try: "Add 50 kg broiler feed"')
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t('inventory')}</h2>
        <button className="btn-primary" onClick={() => { resetForm(); setShowForm(true) }}>
          <Plus size={18} /> {t('add_stock')}
        </button>
      </header>

      <div className="voice-entry-bar">
        <input
          placeholder='Voice/text entry: "Add 50 kg broiler feed"'
          value={voiceText}
          onChange={(e) => setVoiceText(e.target.value)}
        />
        <button className="btn-secondary" onClick={startListening} disabled={listening}>
          <Mic size={16} /> {listening ? 'Listening...' : 'Voice'}
        </button>
        <button className="btn-primary" onClick={handleVoiceEntry}>Apply</button>
      </div>

      <div className="filter-bar">
        {['', ...categories].map((c) => (
          <button key={c} className={`filter-btn ${category === c ? 'active' : ''}`} onClick={() => setCategory(c)}>
            {c ? c.replace(/\b\w/g, (ch) => ch.toUpperCase()) : 'All'}
          </button>
        ))}
        <button type="button" className="btn-secondary category-add-btn" onClick={() => setShowCategoryInput((prev) => !prev)}>
          + Add Category
        </button>
      </div>
      {showCategoryInput && (
        <div className="category-input-row">
          <input
            placeholder="New category name"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
          />
          <button type="button" className="btn-primary" onClick={createCategory}>Save Category</button>
        </div>
      )}

      {showForm && (
        <motion.form className="inline-form expanded" onSubmit={handleSubmit} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat.replace(/\b\w/g, (ch) => ch.toUpperCase())}</option>
            ))}
          </select>
          <input placeholder="Product name" value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} required />
          <input placeholder="Quantity" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required />
          <input placeholder="Unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
          <input placeholder="Reorder level" type="number" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: e.target.value })} />
          <input placeholder="Expiry date" type="date" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} />
          <input placeholder="Supplier" value={form.supplier_name} onChange={(e) => setForm({ ...form, supplier_name: e.target.value })} />
          <button type="submit" className="btn-primary">{editId ? 'Update' : t('save')}</button>
          <button type="button" className="btn-secondary" onClick={resetForm}>{t('cancel')}</button>
        </motion.form>
      )}

      <div className="table-container">
        <table>
          <thead>
            <tr><th>Product</th><th>Category</th><th>Quantity</th><th>Status</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.product_name}</td>
                <td><span className="badge">{item.category}</span></td>
                <td>{item.quantity} {item.unit}</td>
                <td>
                  {item.is_low_stock && <span className="alert-badge"><AlertTriangle size={14} /> Low</span>}
                  {item.is_expiring_soon && <span className="alert-badge warn">Expiring</span>}
                </td>
                <td className="actions-cell">
                  <button className="icon-btn-sm" onClick={() => handleEdit(item)} title="Edit"><Pencil size={14} /></button>
                  <button className="icon-btn-sm" onClick={() => showHistory(item.id)} title="History"><History size={14} /></button>
                  <button className="icon-btn-sm danger" onClick={() => handleDelete(item.id)} title="Delete"><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {historyId && (
        <div className="modal-overlay" onClick={() => setHistoryId(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Stock History</h3>
            {history.length === 0 ? <p>No movements recorded.</p> : (
              <ul className="history-list">
                {history.map((h) => (
                  <li key={h.created_at}>{h.change_amount > 0 ? '+' : ''}{h.change_amount} — {h.reason} ({new Date(h.created_at).toLocaleString()})</li>
                ))}
              </ul>
            )}
            <button className="btn-secondary" onClick={() => setHistoryId(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
