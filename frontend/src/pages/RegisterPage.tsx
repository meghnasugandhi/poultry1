import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const { t } = useLanguage()
  const [form, setForm] = useState({
    email: '', password: '', owner_name: '', farm_name: '',
    mobile_number: '', state: '', district: '', address: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const update = (field: string, value: string) => setForm((f) => ({ ...f, [field]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form)
    } catch {
      setError(t('registration_failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <motion.div className="auth-card auth-card-wide" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <h1>{t('register_farm_title')}</h1>
        <form onSubmit={handleSubmit} className="register-form">
          <div className="form-row">
            <div className="form-group">
              <label>{t('owner_name')}</label>
              <input value={form.owner_name} onChange={(e) => update('owner_name', e.target.value)} required />
            </div>
            <div className="form-group">
              <label>{t('farm_name')}</label>
              <input value={form.farm_name} onChange={(e) => update('farm_name', e.target.value)} required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>{t('email')}</label>
              <input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} required />
            </div>
            <div className="form-group">
              <label>{t('password')}</label>
              <input type="password" value={form.password} onChange={(e) => update('password', e.target.value)} required minLength={8} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>{t('mobile_number')}</label>
              <input value={form.mobile_number} onChange={(e) => update('mobile_number', e.target.value)} required />
            </div>
            <div className="form-group">
              <label>{t('state')}</label>
              <input value={form.state} onChange={(e) => update('state', e.target.value)} required />
            </div>
          </div>
          <div className="form-group">
            <label>{t('district')}</label>
            <input value={form.district} onChange={(e) => update('district', e.target.value)} required />
          </div>
          <div className="form-group">
            <label>{t('address')}</label>
            <textarea value={form.address} onChange={(e) => update('address', e.target.value)} required rows={2} />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? t('creating_account') : t('register')}
          </button>
        </form>
        <p className="auth-link">{t('already_registered')} <Link to="/login">{t('login')}</Link></p>
      </motion.div>
    </div>
  )
}
