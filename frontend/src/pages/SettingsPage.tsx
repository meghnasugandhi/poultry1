import { useEffect, useState } from 'react'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'Kannada' },
  { code: 'hi', label: 'Hindi' },
  { code: 'te', label: 'Telugu' },
  { code: 'ta', label: 'Tamil' },
  { code: 'ml', label: 'Malayalam' },
  { code: 'mr', label: 'Marathi' },
]

interface LoginEntry {
  id: number
  ip_address: string | null
  device: string | null
  logged_in_at: string
}

export default function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { t, reload } = useLanguage()
  const [language, setLanguage] = useState(user?.preferred_language || 'en')
  const [voiceEnabled, setVoiceEnabled] = useState(user?.voice_enabled || false)
  const [notificationsEnabled, setNotificationsEnabled] = useState(user?.notifications_enabled ?? true)
  const [profileForm, setProfileForm] = useState({
    owner_name: '', farm_name: '', mobile_number: '', state: '', district: '', address: '',
    farm_type: 'broiler', total_capacity: 0, current_bird_count: 0,
  })
  const [passwordForm, setPasswordForm] = useState({ current: '', new: '' })
  const [loginHistory, setLoginHistory] = useState<LoginEntry[]>([])
  const [ocrStatus, setOcrStatus] = useState<any>(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (user) {
      setLanguage(user.preferred_language)
      setVoiceEnabled(user.voice_enabled)
      setNotificationsEnabled(user.notifications_enabled)
      setProfileForm({
        owner_name: user.owner_name,
        farm_name: user.farm_name,
        mobile_number: user.mobile_number,
        state: user.state,
        district: user.district,
        address: user.address,
        farm_type: user.farm_type,
        total_capacity: user.total_capacity,
        current_bird_count: user.current_bird_count,
      })
    }
  }, [user])

  useEffect(() => {
    api.get('/auth/login-history').then(({ data }) => setLoginHistory(data))
    api.get('/ocr/health').then(({ data }) => setOcrStatus(data)).catch(() => setOcrStatus({ error: 'Unable to fetch OCR status' }))
  }, [])

  const saveProfile = async () => {
    await api.put('/auth/me', profileForm)
    await refreshUser()
    setMessage('Profile updated')
  }

  const saveSettings = async () => {
    await api.put('/auth/settings', {
      preferred_language: language,
      preferred_theme: theme,
      voice_enabled: voiceEnabled,
      notifications_enabled: notificationsEnabled,
    })
    await refreshUser()
    await reload()
    setMessage('Settings saved')
  }

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/auth/change-password', {
      current_password: passwordForm.current,
      new_password: passwordForm.new,
    })
    setPasswordForm({ current: '', new: '' })
    setMessage('Password updated')
  }

  const uploadPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    await api.post('/auth/profile-photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    await refreshUser()
    setMessage('Profile photo updated')
  }

  return (
    <div className="page">
      <header className="page-header"><h2>{t('settings')}</h2></header>

      <div className="settings-grid">
        <div className="chart-card">
          <h3>Profile</h3>
          <div className="profile-photo-section">
            <div className="avatar">{user?.owner_name?.[0]?.toUpperCase() || 'F'}</div>
            <label className="btn-secondary upload-btn">
              Upload Photo
              <input type="file" hidden accept="image/*" onChange={uploadPhoto} />
            </label>
          </div>
          <div className="form-group"><label>Owner Name</label><input value={profileForm.owner_name} onChange={(e) => setProfileForm({ ...profileForm, owner_name: e.target.value })} /></div>
          <div className="form-group"><label>Farm Name</label><input value={profileForm.farm_name} onChange={(e) => setProfileForm({ ...profileForm, farm_name: e.target.value })} /></div>
          <div className="form-group"><label>Mobile</label><input value={profileForm.mobile_number} onChange={(e) => setProfileForm({ ...profileForm, mobile_number: e.target.value })} /></div>
          <div className="form-row">
            <div className="form-group"><label>State</label><input value={profileForm.state} onChange={(e) => setProfileForm({ ...profileForm, state: e.target.value })} /></div>
            <div className="form-group"><label>District</label><input value={profileForm.district} onChange={(e) => setProfileForm({ ...profileForm, district: e.target.value })} /></div>
          </div>
          <div className="form-group"><label>Address</label><textarea value={profileForm.address} onChange={(e) => setProfileForm({ ...profileForm, address: e.target.value })} rows={2} /></div>
          <div className="form-row">
            <div className="form-group"><label>Farm Type</label>
              <select value={profileForm.farm_type} onChange={(e) => setProfileForm({ ...profileForm, farm_type: e.target.value })}>
                <option value="broiler">Broiler</option><option value="layer">Layer</option><option value="both">Both</option>
              </select>
            </div>
            <div className="form-group"><label>Total Capacity</label><input type="number" value={profileForm.total_capacity} onChange={(e) => setProfileForm({ ...profileForm, total_capacity: parseInt(e.target.value) || 0 })} /></div>
          </div>
          <div className="form-group"><label>Current Bird Count</label><input type="number" value={profileForm.current_bird_count} onChange={(e) => setProfileForm({ ...profileForm, current_bird_count: parseInt(e.target.value) || 0 })} /></div>
          <button className="btn-primary" onClick={saveProfile}>{t('save')} Profile</button>
        </div>

        <div className="chart-card">
          <h3>Preferences</h3>
          <div className="form-group"><label>Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </div>
          <div className="form-group toggle-row"><label>Dark Mode</label>
            <button type="button" className={`toggle ${theme === 'dark' ? 'on' : ''}`} onClick={toggleTheme} aria-label="Toggle dark mode" />
          </div>
          <div className="form-group toggle-row"><label>Voice Responses</label>
            <button type="button" className={`toggle ${voiceEnabled ? 'on' : ''}`} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setVoiceEnabled(!voiceEnabled) }} aria-label="Toggle voice" />
          </div>
          <div className="form-group toggle-row"><label>Notifications</label>
            <button type="button" className={`toggle ${notificationsEnabled ? 'on' : ''}`} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setNotificationsEnabled(!notificationsEnabled) }} aria-label="Toggle notifications" />
          </div>
          <button className="btn-primary" onClick={saveSettings}>{t('save')} Settings</button>
        </div>

        <div className="chart-card">
          <h3>Change Password</h3>
          <form onSubmit={changePassword}>
            <div className="form-group"><label>Current Password</label><input type="password" value={passwordForm.current} onChange={(e) => setPasswordForm({ ...passwordForm, current: e.target.value })} required /></div>
            <div className="form-group"><label>New Password</label><input type="password" value={passwordForm.new} onChange={(e) => setPasswordForm({ ...passwordForm, new: e.target.value })} required minLength={8} /></div>
            <button type="submit" className="btn-primary">Update Password</button>
          </form>
        </div>

        <div className="chart-card">
          <h3>OCR Health</h3>
          {!ocrStatus && <p>Loading OCR status…</p>}
          {ocrStatus?.error && <p className="text-muted">{ocrStatus.error}</p>}
          {ocrStatus && !ocrStatus.error && (
            <div>
              <div className="form-group"><label>OCR.Space</label><input readOnly value={ocrStatus.ocr_space?.configured ? `Configured, reachable=${ocrStatus.ocr_space?.reachable}` : 'Not configured'} /></div>
              <div className="form-group"><label>Tesseract</label><input readOnly value={ocrStatus.tesseract?.installed ? `Installed (${ocrStatus.tesseract.path})` : 'Not installed'} /></div>
            </div>
          )}
        </div>

        <div className="chart-card">
          <h3>Login History</h3>
          <div className="login-history-list">
            {loginHistory.map((h) => (
              <div key={h.id} className="login-entry">
                <span>{new Date(h.logged_in_at).toLocaleString()}</span>
                <span className="text-muted">{h.ip_address || 'Unknown IP'}</span>
              </div>
            ))}
            {loginHistory.length === 0 && <p className="empty-state">No login history yet.</p>}
          </div>
        </div>
      </div>
      {message && <p className="success-msg">{message}</p>}
    </div>
  )
}
