import { useEffect, useState } from 'react'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'

interface Notification {
  id: number
  type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export default function NotificationsPage() {
  const { t } = useLanguage()
  const [notifications, setNotifications] = useState<Notification[]>([])

  const load = () => api.get('/notifications/').then(({ data }) => setNotifications(data))
  useEffect(() => { load() }, [])

  const markAllRead = async () => {
    await api.put('/notifications/read-all')
    load()
  }

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t('notifications_alerts')}</h2>
        <button className="btn-secondary" onClick={markAllRead}>{t('mark_all_read')}</button>
      </header>
      <div className="notifications-list">
        {notifications.map((n) => (
          <div key={n.id} className={`notification-item ${n.is_read ? 'read' : 'unread'}`}>
            <div>
              <strong>{n.title}</strong>
              <p>{n.message}</p>
              <span className="timestamp">{new Date(n.created_at).toLocaleString()}</span>
            </div>
            <span className="badge">{n.type.replace(/_/g, ' ')}</span>
          </div>
        ))}
        {notifications.length === 0 && <p className="empty-state">{t('no_notifications')}</p>}
      </div>
    </div>
  )
}
