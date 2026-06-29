import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Mic, Search, Paperclip, X } from 'lucide-react'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useSpeech } from '../hooks/useSpeech'
import type { ChatMessage } from '../types'

const SUGGESTION_KEYS = [
  'sugg_feed_stock',
  'sugg_feed_expense',
  'sugg_profit',
  'sugg_add_feed',
  'sugg_sold_birds',
  'sugg_low_stock',
]

const DOC_TYPES = [
  'feed_bill', 'medicine_bill', 'vaccine_bill', 'sales_invoice',
  'purchase_receipt', 'vaccination_report', 'lab_report',
]

interface Session {
  id: number
  title: string
}

export default function AssistantPage() {
  const { user } = useAuth()
  const { t, language } = useLanguage()
  const { startListening, transcript, speak } = useSpeech(language)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [docType, setDocType] = useState('feed_bill')
  const bottomRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { api.get('/assistant/sessions').then(({ data }) => setSessions(data)) }, [])
  useEffect(() => { if (transcript) send(transcript) }, [transcript])

  const refreshSessions = () => api.get('/assistant/sessions').then(({ data }) => setSessions(data))

  const send = async (text: string) => {
    if (file) return uploadFile(text)
    if (!text.trim() || loading) return
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      const { data } = await api.post('/assistant/chat', {
        message: text,
        session_id: sessionId,
        language: user?.preferred_language || language,
      })
      setSessionId(data.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: data.message }])
      if (user?.voice_enabled) speak(data.message)
      refreshSessions()
    } finally {
      setLoading(false)
    }
  }

  const uploadFile = async (text: string) => {
    if (!file || loading) return
    const label = text.trim() || `${t('attached_file')}: ${file.name}`
    setMessages((m) => [...m, { role: 'user', content: label }])
    setInput('')
    setLoading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('message', text)
      form.append('document_type', docType)
      form.append('language', user?.preferred_language || language)
      if (sessionId) form.append('session_id', String(sessionId))
      const { data } = await api.post('/assistant/upload', form)
      setSessionId(data.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: data.message }])
      if (user?.voice_enabled) speak(data.message)
      refreshSessions()
    } finally {
      setFile(null)
      setLoading(false)
    }
  }

  const loadSession = async (id: number) => {
    setSessionId(id)
    const { data } = await api.get(`/assistant/sessions/${id}/messages`)
    setMessages(data.map((m: ChatMessage) => ({ role: m.role, content: m.content })))
  }

  const filteredSessions = sessions.filter((s) =>
    !search || s.title.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="page chat-page">
      <header className="page-header"><h2>{t('assistant')}</h2></header>
      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="search-box">
            <Search size={16} />
            <input placeholder={t('search_conversations')} value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button className="btn-secondary full-width" onClick={() => { setSessionId(null); setMessages([]) }}>{t('new_chat')}</button>
          <div className="session-list">
            {filteredSessions.map((s) => (
              <button key={s.id} className={`session-item ${sessionId === s.id ? 'active' : ''}`} onClick={() => loadSession(s.id)}>
                {s.title}
              </button>
            ))}
          </div>
        </aside>

        <div className="chat-container">
          <div className="chat-messages">
            {messages.length === 0 && (
              <div className="chat-welcome">
                <h3>{t('how_can_i_help')}</h3>
                <div className="suggestions">
                  {SUGGESTION_KEYS.map((key) => (
                    <button key={key} className="suggestion-btn" onClick={() => send(t(key))}>{t(key)}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <motion.div key={i} className={`chat-bubble ${msg.role}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                {msg.content}
              </motion.div>
            ))}
            {loading && <div className="chat-bubble assistant typing">{t('thinking')}</div>}
            <div ref={bottomRef} />
          </div>

          {file && (
            <div className="chat-attachment">
              <Paperclip size={15} />
              <span className="attachment-name">{file.name}</span>
              <select value={docType} onChange={(e) => setDocType(e.target.value)}>
                {DOC_TYPES.map((d) => (
                  <option key={d} value={d}>{d.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
              <button className="icon-btn" onClick={() => setFile(null)} title={t('close')}><X size={16} /></button>
            </div>
          )}

          <div className="chat-input-bar">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.csv,image/*"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <button className="icon-btn" onClick={() => fileInputRef.current?.click()} title={t('attach_file')}><Paperclip size={20} /></button>
            <button className="icon-btn" onClick={startListening} title={t('voice_input')}><Mic size={20} /></button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send(input)}
              placeholder={t('ask_placeholder')}
            />
            <button className="btn-primary" onClick={() => send(input)} disabled={loading}>
              {loading ? t('uploading') : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
