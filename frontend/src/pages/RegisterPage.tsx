import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth()
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
      setError('Registration failed. Email may already be in use.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <motion.div className="auth-card auth-card-wide" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <h1>Register Your Farm</h1>
        <form onSubmit={handleSubmit} className="register-form">
          <div className="form-row">
            <div className="form-group">
              <label>Owner Name</label>
              <input value={form.owner_name} onChange={(e) => update('owner_name', e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Farm Name</label>
              <input value={form.farm_name} onChange={(e) => update('farm_name', e.target.value)} required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={form.email} onChange={(e) => update('email', e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" value={form.password} onChange={(e) => update('password', e.target.value)} required minLength={8} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Mobile Number</label>
              <input value={form.mobile_number} onChange={(e) => update('mobile_number', e.target.value)} required />
            </div>
            <div className="form-group">
              <label>State</label>
              <input value={form.state} onChange={(e) => update('state', e.target.value)} required />
            </div>
          </div>
          <div className="form-group">
            <label>District</label>
            <input value={form.district} onChange={(e) => update('district', e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Address</label>
            <textarea value={form.address} onChange={(e) => update('address', e.target.value)} required rows={2} />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>
        <p className="auth-link">Already registered? <Link to="/login">Login</Link></p>
      </motion.div>
    </div>
  )
}
