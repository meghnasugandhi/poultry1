import { useEffect, useState } from 'react'
import { Mic, Volume2, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useLanguage } from '../contexts/LanguageContext'
import { useSpeech } from '../hooks/useSpeech'

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'Kannada' },
  { code: 'hi', label: 'Hindi' },
  { code: 'te', label: 'Telugu' },
  { code: 'ta', label: 'Tamil' },
  { code: 'ml', label: 'Malayalam' },
  { code: 'mr', label: 'Marathi' },
]

interface VoiceResponse {
  action: string
  response: string
  followUp?: string[]
}

export default function VoicePage() {
  const { user } = useAuth()
  const { t, language } = useLanguage()
  const { listening, transcript, startListening, speak } = useSpeech(language)
  const navigate = useNavigate()
  const [lastResponse, setLastResponse] = useState<VoiceResponse | null>(null)

  useEffect(() => {
    if (!transcript) return
    handleCommand(transcript)
  }, [transcript])

  const handleCommand = async (text: string) => {
    const { data } = await api.post('/voice/command', {
      text,
      language: user?.preferred_language || language,
    })
    setLastResponse(data)
    if (user?.voice_enabled) speak(data.response)
  }

  const handleFollowUp = (suggestion: string) => {
    handleCommand(suggestion)
  }

  return (
    <div className="page">
      <header className="page-header"><h2>{t('voice')}</h2></header>
      <div className="voice-container chart-card">
        <div className={`voice-icon ${listening ? 'listening' : ''}`}><Mic size={48} /></div>
        <h3>Hands-Free Farm Management</h3>
        <p>Tap the microphone and speak in your preferred language.</p>
        <button className={`btn-primary voice-btn ${listening ? 'pulse' : ''}`} onClick={startListening} disabled={listening}>
          <Mic size={24} /> {listening ? 'Listening...' : 'Start Listening'}
        </button>
        {transcript && <p className="transcript">You said: "{transcript}"</p>}
        {lastResponse && (
          <div className="voice-response">
            <Volume2 size={16} /> {lastResponse.response}
          </div>
        )}
        {lastResponse?.followUp && lastResponse.followUp.length > 0 && (
          <div className="follow-up-suggestions" style={{marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
            <p style={{fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem'}}>Suggested next actions:</p>
            {lastResponse.followUp.map((suggestion, i) => (
              <button key={i} className="btn-secondary follow-up-btn" onClick={() => handleFollowUp(suggestion)} style={{justifyContent: 'space-between'}}>
                {suggestion} <ChevronRight size={16} />
              </button>
            ))}
          </div>
        )}
        <div className="language-tags">
          {LANGUAGES.map((l) => <span key={l.code} className={`badge ${language === l.code ? 'active' : ''}`}>{l.label}</span>)}
        </div>
        <p className="voice-note">Responses use your language from Settings. Try: "How much feed stock remains?"</p>
        <button className="btn-secondary" onClick={() => navigate('/assistant')}>Open Text Chat</button>
      </div>
    </div>
  )
}