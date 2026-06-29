import { useState } from 'react'
import { motion } from 'framer-motion'
import { Download, FileText, X, Plus, Trash2 } from 'lucide-react'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'

const REPORT_TYPES = [
  'feed_expense', 'medicine_expense', 'inventory', 'profit_loss',
  'vaccination', 'sales', 'batch',
]

interface Preview {
  title: string
  farm_name: string
  owner_name: string
  generated: string
  columns: string[]
  rows: string[][]
}

export default function ReportsPage() {
  const { t } = useLanguage()
  const [reportType, setReportType] = useState('inventory')
  const [format, setFormat] = useState('pdf')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [rows, setRows] = useState<string[][]>([])

  const generate = async () => {
    setLoading(true)
    try {
      const { data } = await api.post<Preview>('/reports/preview', { report_type: reportType })
      setPreview(data)
      setRows(data.rows.map((r) => [...r]))
    } finally {
      setLoading(false)
    }
  }

  const editCell = (ri: number, ci: number, value: string) => {
    setRows((prev) => prev.map((r, i) => (i === ri ? r.map((c, j) => (j === ci ? value : c)) : r)))
  }

  const addRow = () => {
    if (!preview) return
    setRows((prev) => [...prev, preview.columns.map(() => '')])
  }

  const removeRow = (ri: number) => setRows((prev) => prev.filter((_, i) => i !== ri))

  const download = async (fmt: 'pdf' | 'excel') => {
    if (!preview) return
    const { data } = await api.post('/reports/generate', {
      report_type: reportType,
      export_format: fmt,
      columns: preview.columns,
      rows,
    }, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `${reportType}_report.${fmt === 'pdf' ? 'pdf' : 'xlsx'}`
    link.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="page">
      <header className="page-header"><h2>{t('report_generation')}</h2></header>
      <div className="report-form chart-card">
        <div className="form-group">
          <label>{t('report_type')}</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
            {REPORT_TYPES.map((rt) => (
              <option key={rt} value={rt}>{rt.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>{t('export_format')}</label>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="pdf">{t('pdf')}</option>
            <option value="excel">{t('excel')}</option>
          </select>
        </div>
        <button className="btn-primary" onClick={generate} disabled={loading}>
          <FileText size={18} /> {loading ? t('generating') : t('generate_report')}
        </button>
      </div>

      {preview && (
        <div className="modal-overlay" onClick={() => setPreview(null)}>
          <motion.div
            className="modal report-preview-modal"
            onClick={(e) => e.stopPropagation()}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <div className="modal-header">
              <h3>{t('report_preview')}</h3>
              <button className="icon-btn" onClick={() => setPreview(null)}><X size={20} /></button>
            </div>

            <div className="report-sheet">
              <h2 className="report-sheet-title">{preview.title}</h2>
              <p className="report-sheet-meta">
                {t('farm')}: {preview.farm_name} &nbsp;|&nbsp; {t('owner')}: {preview.owner_name}
              </p>
              <p className="report-sheet-meta">{t('generated')}: {preview.generated}</p>

              <p className="preview-hint">{t('preview_hint')}</p>

              {rows.length === 0 ? (
                <p className="empty-state">{t('no_report_data')}</p>
              ) : (
                <div className="report-table-wrap">
                  <table className="report-table">
                    <thead>
                      <tr>
                        {preview.columns.map((col, i) => <th key={i}>{col}</th>)}
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, ri) => (
                        <tr key={ri}>
                          {preview.columns.map((_, ci) => (
                            <td key={ci}>
                              <input
                                value={row[ci] ?? ''}
                                onChange={(e) => editCell(ri, ci, e.target.value)}
                              />
                            </td>
                          ))}
                          <td>
                            <button className="icon-btn danger" onClick={() => removeRow(ri)} title={t('remove')}>
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <button className="btn-secondary add-row-btn" onClick={addRow}>
                <Plus size={15} /> {t('add_row')}
              </button>
            </div>

            <div className="modal-footer report-preview-actions">
              <button className="btn-secondary" onClick={() => download('pdf')}>
                <Download size={16} /> {t('download_pdf')}
              </button>
              <button className="btn-primary" onClick={() => download('excel')}>
                <Download size={16} /> {t('download_excel')}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
