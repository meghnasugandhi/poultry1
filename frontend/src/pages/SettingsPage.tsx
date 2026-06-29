import { useEffect, useState } from 'react'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useLanguage } from '../contexts/LanguageContext'
import { LANGUAGES, type LangCode } from '../i18n'

interface LoginEntry {
  id: number
  ip_address: string | null
  device: string | null
  logged_in_at: string
}

export default function SettingsPage() {
  const { user, refreshUser } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { t, language, setLanguage } = useLanguage()
  const [voiceEnabled, setVoiceEnabled] = useState(user?.voice_enabled || false)
  const [notificationsEnabled, setNotificationsEnabled] = useState(user?.notifications_enabled ?? true)
  const [profileForm, setProfileForm] = useState({
    owner_name: '', farm_name: '', mobile_number: '', state: '', district: '', address: '',
    farm_type: 'broiler', total_capacity: 0, current_bird_count: 0,
  })
  const [passwordForm, setPasswordForm] = useState({ current: '', new: '' })
  const [loginHistory, setLoginHistory] = useState<LoginEntry[]>([])
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (user) {
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
  }, [])

  const saveProfile = async () => {
    await api.put('/auth/me', profileForm)
    await refreshUser()
    setMessage(t('profile_updated'))
  }

  const saveSettings = async () => {
    await api.put('/auth/settings', {
      preferred_language: language,
      preferred_theme: theme,
      voice_enabled: voiceEnabled,
      notifications_enabled: notificationsEnabled,
    })
    await refreshUser()
    setMessage(t('settings_saved'))
  }

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/auth/change-password', {
      current_password: passwordForm.current,
      new_password: passwordForm.new,
    })
    setPasswordForm({ current: '', new: '' })
    setMessage(t('password_updated'))
  }

  const uploadPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    await api.post('/auth/profile-photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    await refreshUser()
    setMessage(t('photo_updated'))
  }

  return (
    <div className="page">
      <header className="page-header"><h2>{t('settings')}</h2></header>

      <div className="settings-grid">
        <div className="chart-card">
          <h3>{t('profile')}</h3>
          <div className="profile-photo-section">
            <div className="avatar">{user?.owner_name?.[0]?.toUpperCase() || 'F'}</div>
            <label className="btn-secondary upload-btn">
              {t('upload_photo')}
              <input type="file" hidden accept="image/*" onChange={uploadPhoto} />
            </label>
          </div>
          <div className="form-group"><label>{t('owner_name')}</label><input value={profileForm.owner_name} onChange={(e) => setProfileForm({ ...profileForm, owner_name: e.target.value })} /></div>
          <div className="form-group"><label>{t('farm_name')}</label><input value={profileForm.farm_name} onChange={(e) => setProfileForm({ ...profileForm, farm_name: e.target.value })} /></div>
          <div className="form-group"><label>{t('mobile')}</label><input value={profileForm.mobile_number} onChange={(e) => setProfileForm({ ...profileForm, mobile_number: e.target.value })} /></div>
          <div className="form-row">
            <div className="form-group"><label>{t('state')}</label><input value={profileForm.state} onChange={(e) => setProfileForm({ ...profileForm, state: e.target.value })} /></div>
            <div className="form-group"><label>{t('district')}</label><input value={profileForm.district} onChange={(e) => setProfileForm({ ...profileForm, district: e.target.value })} /></div>
          </div>
          <div className="form-group"><label>{t('address')}</label><textarea value={profileForm.address} onChange={(e) => setProfileForm({ ...profileForm, address: e.target.value })} rows={2} /></div>
          <div className="form-row">
            <div className="form-group"><label>{t('farm_type')}</label>
              <select value={profileForm.farm_type} onChange={(e) => setProfileForm({ ...profileForm, farm_type: e.target.value })}>
                <option value="broiler">{t('broiler')}</option><option value="layer">{t('layer')}</option><option value="both">{t('both')}</option>
              </select>
            </div>
            <div className="form-group"><label>{t('total_capacity')}</label><input type="number" value={profileForm.total_capacity} onChange={(e) => setProfileForm({ ...profileForm, total_capacity: parseInt(e.target.value) || 0 })} /></div>
          </div>
          <div className="form-group"><label>{t('current_bird_count')}</label><input type="number" value={profileForm.current_bird_count} onChange={(e) => setProfileForm({ ...profileForm, current_bird_count: parseInt(e.target.value) || 0 })} /></div>
          <button className="btn-primary" onClick={saveProfile}>{t('save_profile')}</button>
        </div>

        <div className="chart-card">
          <h3>{t('preferences')}</h3>
          <div className="form-group"><label>{t('language')}</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value as LangCode)}>
              {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native}</option>)}
            </select>
          </div>
          <div className="form-group toggle-row"><label>{t('dark_mode')}</label>
            <button type="button" className={`toggle ${theme === 'dark' ? 'on' : ''}`} onClick={toggleTheme} aria-label="Toggle dark mode" />
          </div>
          <div className="form-group toggle-row"><label>{t('voice_responses')}</label>
            <button type="button" className={`toggle ${voiceEnabled ? 'on' : ''}`} onClick={() => setVoiceEnabled(!voiceEnabled)} aria-label="Toggle voice" />
          </div>
          <div className="form-group toggle-row"><label>{t('notifications')}</label>
            <button type="button" className={`toggle ${notificationsEnabled ? 'on' : ''}`} onClick={() => setNotificationsEnabled(!notificationsEnabled)} aria-label="Toggle notifications" />
          </div>
          <button className="btn-primary" onClick={saveSettings}>{t('save_settings')}</button>
        </div>

        <div className="chart-card">
          <h3>{t('change_password')}</h3>
          <form onSubmit={changePassword}>
            <div className="form-group"><label>{t('current_password')}</label><input type="password" value={passwordForm.current} onChange={(e) => setPasswordForm({ ...passwordForm, current: e.target.value })} required /></div>
            <div className="form-group"><label>{t('new_password')}</label><input type="password" value={passwordForm.new} onChange={(e) => setPasswordForm({ ...passwordForm, new: e.target.value })} required minLength={8} /></div>
            <button type="submit" className="btn-primary">{t('update_password')}</button>
          </form>
        </div>

        <div className="chart-card">
          <h3>{t('login_history')}</h3>
          <div className="login-history-list">
            {loginHistory.map((h) => (
              <div key={h.id} className="login-entry">
                <span>{new Date(h.logged_in_at).toLocaleString()}</span>
                <span className="text-muted">{h.ip_address || t('unknown_ip')}</span>
              </div>
            ))}
            {loginHistory.length === 0 && <p className="empty-state">{t('no_login_history')}</p>}
          </div>
        </div>
      </div>
      {message && <p className="success-msg">{message}</p>}
    </div>
  )
}
