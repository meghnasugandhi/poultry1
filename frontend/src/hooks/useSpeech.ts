import { useCallback, useEffect, useRef, useState } from 'react'

const SPEECH_CODES: Record<string, string> = {
  en: 'en-US', kn: 'kn-IN', hi: 'hi-IN', te: 'te-IN', ta: 'ta-IN', ml: 'ml-IN', mr: 'mr-IN',
}

export function useSpeech(language = 'en') {
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [supported, setSupported] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    setSupported(true)
    const rec = new SR()
    rec.continuous = false
    rec.interimResults = false
    rec.lang = SPEECH_CODES[language] || 'en-US'
    rec.onresult = (e: SpeechRecognitionEvent) => {
      setTranscript(e.results[0][0].transcript)
      setListening(false)
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    recognitionRef.current = rec
  }, [language])

  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Use Chrome or Edge.')
      return
    }
    setTranscript('')
    setListening(true)
    recognitionRef.current.start()
  }, [])

  const speak = useCallback((text: string) => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = SPEECH_CODES[language] || 'en-US'
    window.speechSynthesis.speak(utter)
  }, [language])

  return { listening, transcript, startListening, speak, supported }
}
