import { useState } from 'react'
import { Download } from 'lucide-react'
import api from '../lib/api'

const REPORT_TYPES = [
  'feed_expense', 'medicine_expense', 'inventory', 'profit_loss',
  'vaccination', 'sales', 'batch',
]

export default function ReportsPage() {
  const [reportType, setReportType] = useState('inventory')
  const [format, setFormat] = useState('pdf')
  const [loading, setLoading] = useState(false)

  const generate = async () => {
    setLoading(true)
    try {
      const { data } = await api.post('/reports/generate', {
        report_type: reportType,
        export_format: format,
      }, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `${reportType}_report.${format === 'pdf' ? 'pdf' : 'xlsx'}`
      link.click()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="page-header"><h2>Report Generation</h2></header>
      <div className="report-form chart-card">
        <div className="form-group">
          <label>Report Type</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
            {REPORT_TYPES.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Export Format</label>
          <select value={format} onChange={(e) => setFormat(e.target.value)}>
            <option value="pdf">PDF</option>
            <option value="excel">Excel</option>
          </select>
        </div>
        <button className="btn-primary" onClick={generate} disabled={loading}>
          <Download size={18} /> {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>
    </div>
  )
}
