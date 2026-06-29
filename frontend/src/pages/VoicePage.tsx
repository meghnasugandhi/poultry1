import { useEffect, useState } from 'react'
import { Mic, Volume2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useSpeech } from '../hooks/useSpeech'
import { LANGUAGES } from '../i18n'

export default function VoicePage() {
  const { user } = useAuth()
  const { t, language } = useLanguage()
  const { listening, transcript, startListening, speak } = useSpeech(language)
  const navigate = useNavigate()
  const [lastResponse, setLastResponse] = useState('')

  useEffect(() => {
    if (!transcript) return
    handleCommand(transcript)
  }, [transcript])

  const handleCommand = async (text: string) => {
    const { data } = await api.post('/assistant/chat', {
      message: text,
      language: user?.preferred_language || language,
    })
    setLastResponse(data.message)
    if (user?.voice_enabled) speak(data.message)
  }

  return (
    <div className="page">
      <header className="page-header"><h2>{t('voice')}</h2></header>
      <div className="voice-container chart-card">
        <div className={`voice-icon ${listening ? 'listening' : ''}`}><Mic size={48} /></div>
        <h3>{t('hands_free')}</h3>
        <p>{t('tap_mic')}</p>
        <button className={`btn-primary voice-btn ${listening ? 'pulse' : ''}`} onClick={startListening} disabled={listening}>
          <Mic size={24} /> {listening ? t('listening') : t('start_listening')}
        </button>
        {transcript && <p className="transcript">{t('you_said')}: "{transcript}"</p>}
        {lastResponse && <div className="voice-response"><Volume2 size={16} /> {lastResponse}</div>}
        <div className="language-tags">
          {LANGUAGES.map((l) => <span key={l.code} className={`badge ${language === l.code ? 'active' : ''}`}>{l.native}</span>)}
        </div>
        <p className="voice-note">{t('responses_use_language')}</p>
        <button className="btn-secondary" onClick={() => navigate('/assistant')}>{t('open_text_chat')}</button>
      </div>
    </div>
  )
}
