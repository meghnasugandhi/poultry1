import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Mic, Search, Trash2, AlertCircle } from 'lucide-react'
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
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadPrompt, setUploadPrompt] = useState('')
  const [processingUpload, setProcessingUpload] = useState(false)
  const [showUploadConfirm, setShowUploadConfirm] = useState(false)
  const [pendingUploadData, setPendingUploadData] = useState<any | null>(null)
  const [confirmInventory, setConfirmInventory] = useState(true)
  const [confirmFinance, setConfirmFinance] = useState(true)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggested, setSuggested] = useState<any | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { api.get('/assistant/sessions').then(({ data }) => setSessions(data)) }, [])
  useEffect(() => { if (transcript) send(transcript) }, [transcript])

  const send = async (text: string) => {
    if (!text.trim() || loading) return
    const needsConfirmation = /\b(add|remove|delete|update|approve|reject|create|buy|purchase|consume|deduct)\b/i.test(text)
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      if (needsConfirmation) {
        const confirmed = window.confirm('This action changes records. Do you want to continue?')
        if (!confirmed) {
          setMessages((m) => [...m, { role: 'assistant', content: 'Action cancelled.' }])
          return
        }
      }
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

  const selectFile = (file: File | null) => {
    if (!file) return
    setSelectedFile(file)
    setUploadPrompt('')
  }

  const processSelectedFile = async () => {
    if (!selectedFile) return
    setProcessingUpload(true)
    try {
      const fd = new FormData()
      fd.append('file', selectedFile)
      fd.append('prompt', uploadPrompt)
      const { data } = await api.post('/documents/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })

      setSelectedFile(null)

      const parts: string[] = []
      if (data.company_name) parts.push(`Company: ${data.company_name}`)
      if (data.product_name) parts.push(`Product: ${data.product_name}`)
      if (data.quantity) parts.push(`Quantity: ${data.quantity}`)
      if (data.cost) parts.push(`Cost: ₹${data.cost}`)
      if (data.invoice_number) parts.push(`Invoice: ${data.invoice_number}`)

      const summary = `Uploaded document — ${parts.join(' | ')}\n(Raw OCR: ${data.raw_ocr_text?.slice(0, 200) || ''})`
      setMessages((m) => [...m, { role: 'user', content: `Uploaded document: ${data.original_filename}` }])

      const payload = { data, parts, summary, prompt: uploadPrompt.trim() }
      if (data.is_confused) {
        setPendingUploadData(payload)
        setShowUploadConfirm(true)
        return
      }

      await completeUploadProcessing(payload)
    } finally {
      setProcessingUpload(false)
      setUploadPrompt('')
    }
  }

  const completeUploadProcessing = async (payload: any) => {
    const { parts, summary, prompt } = payload
    const systemPrompt = prompt || 'Please extract any bill data and add it to inventory/finance as needed.'
    const resp = await api.post('/assistant/chat', {
      message: `${systemPrompt} Document data: ${parts.join('; ')}`,
      session_id: sessionId,
      language: user?.preferred_language || language,
    })

    setSessionId(resp.data.session_id)
    setMessages((m) => [...m, { role: 'assistant', content: summary }, { role: 'assistant', content: resp.data.message }])
    if (user?.voice_enabled) speak(resp.data.message)
    api.get('/assistant/sessions').then(({ data: s }) => setSessions(s))
  }

  const handleUploadConfirm = async () => {
    if (!pendingUploadData) return
    setShowUploadConfirm(false)
    setProcessingUpload(true)
    try {
      const docId = pendingUploadData.data?.id
      if (docId) {
        const { data } = await api.post(`/documents/${docId}/process`, {
          add_inventory: confirmInventory,
          add_finance: confirmFinance,
        })
        const parts: string[] = []
        if (data.inventory) parts.push(`Inventory updated (item ${data.inventory.item_id}): ${data.inventory.quantity}`)
        if (data.finance) parts.push(`Finance transaction created: ₹${data.finance.amount}`)
        if (parts.length === 0) parts.push('No actions taken')
        setMessages((m) => [...m, { role: 'assistant', content: parts.join(' | ') }])
      } else {
        // fallback to usual processing
        await completeUploadProcessing(pendingUploadData)
      }
    } catch (e) {
      console.error(e)
      setMessages((m) => [...m, { role: 'assistant', content: 'Failed to process document.' }])
    } finally {
      setProcessingUpload(false)
      setPendingUploadData(null)
      setUploadPrompt('')
      setConfirmInventory(true)
      setConfirmFinance(true)
    }
  }

  const handleUploadCancel = () => {
    setShowUploadConfirm(false)
    setPendingUploadData(null)
    setUploadPrompt('')
  }

  const approveSuggested = async (id: number) => {
    try {
      const { data } = await api.post(`/suggested-transactions/${id}/approve`)
      setSuggested(null)
      setMessages((m) => [...m, { role: 'assistant', content: `Suggested transaction approved: ₹${data.amount}` }])
    } catch (e) {
      console.error(e)
    }
  }

  const rejectSuggested = async (id: number) => {
    try {
      await api.post(`/suggested-transactions/${id}/reject`)
      setSuggested(null)
      setMessages((m) => [...m, { role: 'assistant', content: `Suggested transaction rejected` }])
    } catch (e) {
      console.error(e)
    }
  }

  const deleteSession = async (id: number) => {
    if (!confirm('Delete this conversation and its message history?')) return
    try {
      await api.delete(`/assistant/sessions/${id}`)
      setSessionId(null)
      setMessages([])
      const { data: refreshed } = await api.get('/assistant/sessions')
      setSessions(refreshed)
    } catch (e) {
      console.error(e)
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
              <div key={s.id} className={`session-item ${sessionId === s.id ? 'active' : ''}`}>
                <button type="button" className="session-link" onClick={() => loadSession(s.id)}>
                  {s.title}
                </button>
                <button
                  type="button"
                  className="icon-btn-sm danger"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteSession(s.id)
                  }}
                  title="Delete conversation"
                >
                  <Trash2 size={14} />
                </button>
              </div>
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
            <label className="btn-secondary upload-btn">
              {selectedFile ? selectedFile.name : 'Select Bill'}
              <input type="file" accept="image/*,application/pdf" hidden onChange={(e) => selectFile(e.target.files?.[0] || null)} />
            </label>
            <input value={uploadPrompt} onChange={(e) => setUploadPrompt(e.target.value)} placeholder="Optional bill context or notes" />
            <button
              className="btn-primary"
              onClick={() => selectedFile ? processSelectedFile() : send(input)}
              disabled={loading || processingUpload}
            >
              <Send size={18} />
            </button>
          </div>
          {suggested && (
            <div className="suggested-transaction-banner">
              <div>
                <strong>Suggested transaction:</strong> {suggested.transaction_type} ₹{suggested.amount} — {suggested.description}
              </div>
              <div className="suggested-actions">
                <button className="btn-primary" onClick={() => approveSuggested(suggested.id)}>Approve</button>
                <button className="btn-secondary" onClick={() => rejectSuggested(suggested.id)}>Reject</button>
              </div>
            </div>
          )}
          {showUploadConfirm && pendingUploadData && (
            <div className="modal-overlay">
              <div className="modal">
                <h3><AlertCircle size={20} /> Clarification needed</h3>
                <p>The bill may be handwritten or low confidence. Review the extracted details carefully and confirm before processing.</p>
                <div className="history-list">
                  {pendingUploadData.parts.length > 0 ? (
                    pendingUploadData.parts.map((part: string, index: number) => (
                      <div key={index} className="history-entry">{part}</div>
                    ))
                  ) : (
                    <div className="history-entry">No structured fields were extracted.</div>
                  )}
                </div>
                <div style={{display: 'flex', gap: 12, alignItems: 'center', marginTop: 8}}>
                  <label style={{display: 'flex', alignItems: 'center', gap: 8}}>
                    <input type="checkbox" checked={confirmInventory} onChange={(e) => setConfirmInventory(e.target.checked)} /> Add to inventory
                  </label>
                  <label style={{display: 'flex', alignItems: 'center', gap: 8}}>
                    <input type="checkbox" checked={confirmFinance} onChange={(e) => setConfirmFinance(e.target.checked)} /> Add to finance
                  </label>
                </div>
                <div className="modal-actions">
                  <button className="btn-primary" onClick={handleUploadConfirm}>Proceed</button>
                  <button className="btn-secondary" onClick={handleUploadCancel}>Cancel</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
