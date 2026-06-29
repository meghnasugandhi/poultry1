import { useEffect, useState } from 'react'
import { Upload, Download, AlertCircle } from 'lucide-react'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'

interface Document {
  id: number
  document_type: string
  original_filename: string
  company_name: string | null
  product_name: string | null
  quantity: number | null
  cost: number | null
  invoice_number: string | null
  supplier_name: string | null
  ocr_confidence: number | null
  needs_clarification: boolean
  created_at: string
}

const DOC_TYPES = [
  'feed_bill', 'medicine_bill', 'vaccine_bill', 'sales_invoice',
  'purchase_receipt', 'vaccination_report', 'lab_report',
]

export default function DocumentsPage() {
  const { t } = useLanguage()
  const [docs, setDocs] = useState<Document[]>([])
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('')
  const [uploadType, setUploadType] = useState('feed_bill')
  const [clarifyDoc, setClarifyDoc] = useState<Document | null>(null)
  const [clarifyForm, setClarifyForm] = useState({ company_name: '', product_name: '', cost: '', invoice_number: '', supplier_name: '' })

  const load = () => {
    api.get('/documents/', {
      params: { search: search || undefined, document_type: filterType || undefined },
    }).then(({ data }) => setDocs(data))
  }

  useEffect(() => { load() }, [search, filterType])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', uploadType)
    const { data } = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (data.needs_clarification) {
      setClarifyDoc(data)
      setClarifyForm({
        company_name: data.company_name || '',
        product_name: data.product_name || '',
        cost: data.cost ? String(data.cost) : '',
        invoice_number: data.invoice_number || '',
        supplier_name: data.supplier_name || '',
      })
    }
    load()
    e.target.value = ''
  }

  const handleDownload = async (id: number, filename: string) => {
    const { data } = await api.get(`/documents/${id}/download`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
  }

  const submitClarification = async () => {
    if (!clarifyDoc) return
    await api.put(`/documents/${clarifyDoc.id}/clarify`, {
      company_name: clarifyForm.company_name || null,
      product_name: clarifyForm.product_name || null,
      cost: clarifyForm.cost ? parseFloat(clarifyForm.cost) : null,
      invoice_number: clarifyForm.invoice_number || null,
      supplier_name: clarifyForm.supplier_name || null,
    })
    setClarifyDoc(null)
    load()
  }

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t('documents')}</h2>
        <div className="header-actions">
          <select value={uploadType} onChange={(e) => setUploadType(e.target.value)}>
            {DOC_TYPES.map((dt) => <option key={dt} value={dt}>{dt.replace(/_/g, ' ')}</option>)}
          </select>
          <label className="btn-primary upload-btn">
            <Upload size={18} /> {t('upload_document')}
            <input type="file" hidden onChange={handleUpload} accept="image/*,.pdf,.txt" />
          </label>
        </div>
      </header>

      <div className="filter-bar">
        <input className="search-input" placeholder="Search documents..." value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
          <option value="">All types</option>
          {DOC_TYPES.map((dt) => <option key={dt} value={dt}>{dt.replace(/_/g, ' ')}</option>)}
        </select>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr><th>File</th><th>Type</th><th>Company</th><th>Product</th><th>Cost</th><th>Confidence</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.original_filename}</td>
                <td><span className="badge">{doc.document_type.replace(/_/g, ' ')}</span></td>
                <td>{doc.company_name || '—'}</td>
                <td>{doc.product_name || '—'}</td>
                <td>{doc.cost ? `₹${doc.cost}` : '—'}</td>
                <td>{doc.ocr_confidence != null ? `${(doc.ocr_confidence * 100).toFixed(0)}%` : '—'}</td>
                <td>
                  {doc.needs_clarification ? (
                    <button className="alert-badge warn btn-link" onClick={() => { setClarifyDoc(doc); setClarifyForm({ company_name: doc.company_name || '', product_name: doc.product_name || '', cost: doc.cost ? String(doc.cost) : '', invoice_number: doc.invoice_number || '', supplier_name: doc.supplier_name || '' }) }}>
                      <AlertCircle size={14} /> Review
                    </button>
                  ) : 'Verified'}
                </td>
                <td>
                  <button className="icon-btn-sm" onClick={() => handleDownload(doc.id, doc.original_filename)}><Download size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {clarifyDoc && (
        <div className="modal-overlay">
          <div className="modal">
            <h3><AlertCircle size={20} /> Clarification Required</h3>
            <p>OCR confidence was below 90%. Please verify or correct the extracted fields.</p>
            <div className="form-group"><label>Company</label><input value={clarifyForm.company_name} onChange={(e) => setClarifyForm({ ...clarifyForm, company_name: e.target.value })} /></div>
            <div className="form-group"><label>Product</label><input value={clarifyForm.product_name} onChange={(e) => setClarifyForm({ ...clarifyForm, product_name: e.target.value })} /></div>
            <div className="form-group"><label>Cost (₹)</label><input type="number" value={clarifyForm.cost} onChange={(e) => setClarifyForm({ ...clarifyForm, cost: e.target.value })} /></div>
            <div className="form-group"><label>Invoice #</label><input value={clarifyForm.invoice_number} onChange={(e) => setClarifyForm({ ...clarifyForm, invoice_number: e.target.value })} /></div>
            <div className="form-group"><label>Supplier</label><input value={clarifyForm.supplier_name} onChange={(e) => setClarifyForm({ ...clarifyForm, supplier_name: e.target.value })} /></div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={submitClarification}>{t('save')}</button>
              <button className="btn-secondary" onClick={() => setClarifyDoc(null)}>{t('cancel')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
