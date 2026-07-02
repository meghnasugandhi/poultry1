import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Mic, Search, Trash2, AlertCircle } from 'lucide-react'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useSpeech } from '../hooks/useSpeech'
import type { ChatMessage } from '../types'


const SUGGESTIONS = [
  'suggestion_feed_stock',
  'suggestion_feed_expense',
  'suggestion_profit',
  'suggestion_fcr',
  'suggestion_medicine_inventory',
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
  const [streamingMessage, setStreamingMessage] = useState('')
  const [suggested, setSuggested] = useState<any | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const requestSeqRef = useRef(0)


  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, streamingMessage])
  useEffect(() => { api.get('/assistant/sessions').then(({ data }) => setSessions(data)) }, [])
  useEffect(() => { if (transcript) send(transcript) }, [transcript])

  const refreshSessions = async () => {
    const { data } = await api.get('/assistant/sessions')
    setSessions(data)
  }

  const startNewChat = () => {
    requestSeqRef.current += 1
    setSessionId(null)
    setMessages([])
    setInput('')
    setStreamingMessage('')
    setSuggested(null)
    setLoading(false)
  }

  const send = async (text: string) => {
    const message = text.trim()
    if (!message || loading) return

    const currentSessionId = sessionId
    const payload: Record<string, unknown> = {
      message,
      session_id: currentSessionId,
      language,
    }
    if (selectedFile) {
      payload.attachment = {
        filename: selectedFile.name,
        type: selectedFile.type,
        size: selectedFile.size,
      }
    }

    const seq = ++requestSeqRef.current

    const needsConfirmation = /\b(add|remove|delete|update|approve|reject|create|buy|purchase|consume|deduct)\b/i.test(message)
    setMessages((m) => [...m, { role: 'user', content: message }])

    setInput('')
    setLoading(true)
    setStreamingMessage('')

    try {
      if (needsConfirmation) {
        const confirmed = window.confirm(t('mutating_action_confirm'))
        if (!confirmed) {
          setMessages((m) => [...m, { role: 'assistant', content: t('action_cancelled') }])
          return
        }
      }

      const { data } = await api.post('/assistant/chat', payload)
      if (seq !== requestSeqRef.current) return
      setSessionId(data.session_id)
      setMessages((m) => [...m, { role: 'assistant', content: data.message || t('no_assistant_response') }])
      if (user?.voice_enabled && data.message) speak(data.message)
      await refreshSessions()
    } catch (e) {
      console.error(e)
      setMessages((m) => [...m, { role: 'assistant', content: t('no_assistant_response') }])
    } finally {
      setLoading(false)
      setStreamingMessage('')
    }
  }

  const handleSubmit = (event?: React.FormEvent) => {
    event?.preventDefault()
    if (selectedFile) {
      void processSelectedFile()
      return
    }
    void send(input)
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
      setMessages((m) => [...m, { role: 'assistant', content: summary }])
      if (data.needs_clarification || data.is_confused) {
        setPendingUploadData(payload)
        setShowUploadConfirm(true)
        return
      }

      await processUploadedDocument(payload, true, true)
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
      language,
    })

    setSessionId(resp.data.session_id)
    setMessages((m) => [...m, { role: 'assistant', content: summary }, { role: 'assistant', content: resp.data.message }])
    if (user?.voice_enabled) speak(resp.data.message)
    api.get('/assistant/sessions').then(({ data: s }) => setSessions(s))
  }

  const processUploadedDocument = async (payload: any, addInventory: boolean, addFinance: boolean) => {
    const docId = payload.data?.id
    if (!docId) {
      setMessages((m) => [...m, { role: 'assistant', content: t('failed_process_document') }])
      return
    }

    const { data } = await api.post(`/documents/${docId}/process`, {
      add_inventory: addInventory,
      add_finance: addFinance,
    })

    const updates: string[] = []
    if (data.inventory) {
      const label = data.inventory.product_name || `${t('item')} ${data.inventory.item_id}`
      const unit = data.inventory.unit ? ` ${data.inventory.unit}` : ''
      updates.push(`${t('inventory_updated')}: ${label} - ${data.inventory.quantity}${unit}`)
    }
    if (data.finance) {
      updates.push(`${t('finance_transaction_created')}: ₹${data.finance.amount}`)
    }
    if (data.document) {
      updates.push(`${t('document_saved')}: ${data.document.filename}`)
    }
    if (updates.length === 0) updates.push(t('no_actions_taken'))

    const message = `${t('bill_processing_complete')}\n${updates.join('\n')}`
    setMessages((m) => [...m, { role: 'assistant', content: message }])
    if (user?.voice_enabled) speak(message)
    api.get('/assistant/sessions').then(({ data: s }) => setSessions(s))
  }

  const handleUploadConfirm = async () => {
    if (!pendingUploadData) return
    setShowUploadConfirm(false)
    setProcessingUpload(true)
    try {
      await processUploadedDocument(pendingUploadData, confirmInventory, confirmFinance)
      return
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
      setMessages((m) => [...m, { role: 'assistant', content: t('failed_process_document') }])
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
      setMessages((m) => [...m, { role: 'assistant', content: `${t('suggested_transaction_approved')}: ₹${data.amount}` }])
    } catch (e) {
      console.error(e)
    }
  }

  const rejectSuggested = async (id: number) => {
    try {
      await api.post(`/suggested-transactions/${id}/reject`)
      setSuggested(null)
      setMessages((m) => [...m, { role: 'assistant', content: t('suggested_transaction_rejected') }])
    } catch (e) {
      console.error(e)
    }
  }

  const deleteSession = async (id: number) => {
    if (!confirm(t('delete_conversation_confirm'))) return
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
            <input placeholder={t('search_conversations')} value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <button className="btn-secondary full-width" onClick={startNewChat}>{t('new_chat')}</button>
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
                  title={t('delete_conversation')}
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
                <h3>{t('farm_help_prompt')}</h3>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="suggestion-btn" onClick={() => send(t(s))}>{t(s)}</button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <motion.div key={i} className={`chat-bubble ${msg.role}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                {msg.content}
              </motion.div>
            ))}
            {loading && streamingMessage && (
              <motion.div className="chat-bubble assistant typing" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                {streamingMessage}
              </motion.div>
            )}
            {loading && !streamingMessage && <div className="chat-bubble assistant typing">{t('thinking')}</div>}
            <div ref={bottomRef} />
          </div>
          <form className="chat-input-bar" onSubmit={handleSubmit}>
            <button type="button" className="icon-btn" onClick={startListening} title={t('voice_input')} disabled={loading || processingUpload}><Mic size={20} /></button>
            <label className="btn-secondary upload-btn">
              {selectedFile ? selectedFile.name : t('select_bill')}
              <input type="file" accept="image/*,application/pdf" hidden onChange={(e) => selectFile(e.target.files?.[0] || null)} />
            </label>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={t('ask_assistant_placeholder')} disabled={loading || processingUpload} />
            <button type="submit" className="btn-primary" disabled={loading || processingUpload}>
              <Send size={18} />
            </button>
          </form>
          {suggested && (
            <div className="suggested-transaction-banner">
              <div>
                <strong>{t('suggested_transaction')}:</strong> {suggested.transaction_type} ₹{suggested.amount} - {suggested.description}
              </div>
              <div className="suggested-actions">
                <button className="btn-primary" onClick={() => approveSuggested(suggested.id)}>{t('approve')}</button>
                <button className="btn-secondary" onClick={() => rejectSuggested(suggested.id)}>{t('reject')}</button>
              </div>
            </div>
          )}
          {showUploadConfirm && pendingUploadData && (
            <div className="modal-overlay">
              <div className="modal">
                <h3><AlertCircle size={20} /> {t('clarification_needed')}</h3>
                <p>{t('bill_review_prompt')}</p>
                <div className="history-list">
                  {pendingUploadData.parts.length > 0 ? (
                    pendingUploadData.parts.map((part: string, index: number) => (
                      <div key={index} className="history-entry">{part}</div>
                    ))
                  ) : (
                    <div className="history-entry">{t('no_structured_fields')}</div>
                  )}
                </div>
                <div style={{display: 'flex', gap: 12, alignItems: 'center', marginTop: 8}}>
                  <label style={{display: 'flex', alignItems: 'center', gap: 8}}>
                    <input type="checkbox" checked={confirmInventory} onChange={(e) => setConfirmInventory(e.target.checked)} /> {t('add_to_inventory')}
                  </label>
                  <label style={{display: 'flex', alignItems: 'center', gap: 8}}>
                    <input type="checkbox" checked={confirmFinance} onChange={(e) => setConfirmFinance(e.target.checked)} /> {t('add_to_finance')}
                  </label>
                </div>
                <div className="modal-actions">
                  <button className="btn-primary" onClick={handleUploadConfirm}>{t('proceed')}</button>
                  <button className="btn-secondary" onClick={handleUploadCancel}>{t('cancel')}</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
