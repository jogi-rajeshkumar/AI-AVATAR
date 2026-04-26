import { useCallback, useEffect, useRef, useState } from 'react'
import Avatar from './components/Avatar.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import MicButton from './components/MicButton.jsx'

const BACKEND = import.meta.env.VITE_BACKEND_URL || ''

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [statusType, setStatusType] = useState('') // '' | 'error' | 'info'
  const [emotion, setEmotion] = useState('neutral')
  const [emotionConf, setEmotionConf] = useState(0.5)
  const [speaking, setSpeaking] = useState(false)
  const [convId, setConvId] = useState(null)
  const [ttsAvailable, setTtsAvailable] = useState(true)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const showStatus = (msg, type = '') => {
    setStatus(msg)
    setStatusType(type)
  }

  const clearStatus = () => { setStatus(''); setStatusType('') }

  // ── Send message to backend ─────────────────────────────────────────────
  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setMessages(prev => [...prev, { role: 'user', content: trimmed }])
    setInput('')
    setLoading(true)
    showStatus('Thinking…')

    try {
      const res = await fetch(`${BACKEND}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: trimmed, conversation_id: convId }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || res.statusText)
      }

      const data = await res.json()
      setConvId(data.conversation_id)
      setEmotion(data.emotion || 'neutral')
      setEmotionConf(data.emotion_confidence ?? 0.5)
      setTtsAvailable(data.tts_available)

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        emotion: data.emotion,
        emotionConf: data.emotion_confidence,
        sources: data.sources || [],
      }])

      clearStatus()

      // TTS playback
      if (data.tts_available) {
        await playBackendTTS(data.response)
      } else {
        playBrowserTTS(data.response)
      }
    } catch (err) {
      showStatus(`Error: ${err.message}`, 'error')
      setLoading(false)
    } finally {
      setLoading(false)
    }
  }, [loading, convId])

  // ── Backend TTS ─────────────────────────────────────────────────────────
  const playBackendTTS = async (text) => {
    try {
      const res = await fetch(`${BACKEND}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (res.status === 204 || !res.ok) {
        playBrowserTTS(text)
        return
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      setSpeaking(true)
      audio.onended = () => { setSpeaking(false); URL.revokeObjectURL(url) }
      audio.onerror = () => { setSpeaking(false); playBrowserTTS(text) }
      await audio.play()
    } catch {
      playBrowserTTS(text)
    }
  }

  // ── Browser SpeechSynthesis fallback ────────────────────────────────────
  const playBrowserTTS = (text) => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(text)
    utt.onstart = () => setSpeaking(true)
    utt.onend = () => setSpeaking(false)
    utt.onerror = () => setSpeaking(false)
    window.speechSynthesis.speak(utt)
  }

  // ── STT callback from MicButton ─────────────────────────────────────────
  const handleTranscript = (transcript, sttAvailable) => {
    if (!transcript) {
      showStatus('Could not transcribe audio. Please type your message.', 'error')
      return
    }
    setInput(transcript)
    showStatus(`Transcribed: "${transcript}"`, 'info')
    // Auto-send after a short delay so user can see the transcript
    setTimeout(() => sendMessage(transcript), 400)
  }

  // ── Key handler in textarea ─────────────────────────────────────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="app">
      <header>
        <span style={{ fontSize: '1.8rem' }}>🤖</span>
        <h1>AI Avatar</h1>
        <span className="badge">prototype</span>
      </header>

      {/* Avatar side panel */}
      <aside className="avatar-panel">
        <Avatar emotion={emotion} confidence={emotionConf} speaking={speaking} />

        <div style={{
          width: '100%',
          borderTop: '1px solid #1e293b',
          paddingTop: 16,
          fontSize: '.8rem',
          color: '#475569',
          lineHeight: 1.7,
        }}>
          <div>🔍 <b>Search:</b> DuckDuckGo / SerpAPI</div>
          <div>🧠 <b>LLM:</b> OpenAI / Mock</div>
          <div>🎙 <b>STT:</b> Whisper / Text</div>
          <div>🔊 <b>TTS:</b> {ttsAvailable ? 'Backend' : 'Browser'}</div>
        </div>
      </aside>

      {/* Chat area */}
      <div className="chat-panel">
        <ChatPanel messages={messages} loading={loading} />
        <div ref={messagesEndRef} />

        {/* Status bar */}
        {status && (
          <div style={{ padding: '0 20px' }}>
            <div className={`status ${statusType}`}>{status}</div>
          </div>
        )}

        {/* Input bar */}
        <div className="input-bar">
          <MicButton
            onTranscript={handleTranscript}
            onError={msg => showStatus(msg, 'error')}
            disabled={loading}
          />

          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message or use the mic… (Enter to send)"
            rows={1}
            disabled={loading}
          />

          <button
            className="btn-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
