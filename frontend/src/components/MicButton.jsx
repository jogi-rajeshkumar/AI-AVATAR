import { useRef, useState } from 'react'

const BACKEND = import.meta.env.VITE_BACKEND_URL || ''

/**
 * Microphone record button.
 * Sends audio blob to /api/stt and calls onTranscript with the result.
 * If sttAvailable is false it simply opens the text input (handled by parent).
 */
export default function MicButton({ onTranscript, onError, disabled }) {
  const [recording, setRecording] = useState(false)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunksRef.current = []
      const mr = new MediaRecorder(stream)
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || 'audio/webm' })
        await sendAudio(blob, mr.mimeType || 'audio/webm')
      }
      mr.start()
      mediaRef.current = mr
      setRecording(true)
    } catch (err) {
      onError?.(`Microphone error: ${err.message}`)
    }
  }

  const stop = () => {
    mediaRef.current?.stop()
    setRecording(false)
  }

  const sendAudio = async (blob, mimeType) => {
    try {
      const fd = new FormData()
      fd.append('audio', blob, `recording.${mimeType.split('/')[1]?.split(';')[0] || 'webm'}`)
      const res = await fetch(`${BACKEND}/api/stt`, { method: 'POST', body: fd })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        onError?.(`STT failed: ${err.detail || res.statusText}`)
        return
      }
      const data = await res.json()
      onTranscript?.(data.transcript, data.stt_available)
    } catch (err) {
      onError?.(`STT request failed: ${err.message}`)
    }
  }

  return (
    <button
      className={`btn-icon${recording ? ' recording' : ''}`}
      onClick={recording ? stop : start}
      disabled={disabled}
      title={recording ? 'Stop recording' : 'Start recording'}
      aria-label={recording ? 'Stop recording' : 'Record audio'}
    >
      {recording ? '⏹' : '🎙'}
    </button>
  )
}
