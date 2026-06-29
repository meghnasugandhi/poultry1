import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Mic, Search } from 'lucide-react'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useSpeech } from '../hooks/useSpeech'
import type { ChatMessage } from '../types'

const SUGGESTIONS = [
  'How much feed stock remains?',
  'What was my feed expense last month?',
  'Show overall profit.',
  'Calculate FCR.',
  'Show medicine inventory.',
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
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { api.get('/assistant/sessions').then(({ data }) => setSessions(data)) }, [])
  useEffect(() => { if (transcript) send(transcript) }, [transcript])

  const send = async (text: string) => {
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
      api.get('/assistant/sessions').then(({ data: s }) => setSessions(s))
    } finally {
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
            <input placeholder="Search conversations..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button className="btn-secondary full-width" onClick={() => { setSessionId(null); setMessages([]) }}>New Chat</button>
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
                <h3>How can I help your farm today?</h3>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="suggestion-btn" onClick={() => send(s)}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <motion.div key={i} className={`chat-bubble ${msg.role}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                {msg.content}
              </motion.div>
            ))}
            {loading && <div className="chat-bubble assistant typing">Thinking...</div>}
            <div ref={bottomRef} />
          </div>
          <div className="chat-input-bar">
            <button className="icon-btn" onClick={startListening} title="Voice input"><Mic size={20} /></button>
            <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send(input)} placeholder="Ask about inventory, finances, reports..." />
            <button className="btn-primary" onClick={() => send(input)} disabled={loading}><Send size={18} /></button>
          </div>
        </div>
      </div>
    </div>
  )
}
