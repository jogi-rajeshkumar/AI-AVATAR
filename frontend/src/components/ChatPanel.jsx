/**
 * Renders the scrollable conversation with user + assistant messages,
 * sources/citations, and a typing indicator.
 */
export default function ChatPanel({ messages, loading }) {
  return (
    <div className="messages">
      {messages.length === 0 && (
        <div style={{
          textAlign: 'center',
          color: '#475569',
          marginTop: '20vh',
          lineHeight: 1.8,
        }}>
          <div style={{ fontSize: '3rem', marginBottom: 12 }}>🤖</div>
          <div style={{ fontWeight: 600, fontSize: '1.1rem', color: '#64748b' }}>
            Start a conversation
          </div>
          <div style={{ fontSize: '.85rem', color: '#334155', marginTop: 4 }}>
            Press the mic button to speak, or type your message below.
          </div>
        </div>
      )}

      {messages.map((msg, i) => (
        <div key={i} className={`msg ${msg.role}`}>
          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

          {msg.emotion && (
            <div className="meta">
              {emotionEmoji(msg.emotion)} {capitalize(msg.emotion)} ·{' '}
              {Math.round((msg.emotionConf ?? 0.5) * 100)}% confidence
            </div>
          )}

          {msg.sources?.length > 0 && (
            <div className="sources">
              <div style={{ fontSize: '.72rem', color: '#64748b', marginBottom: 3 }}>Sources</div>
              {msg.sources.map((s, j) => (
                <a key={j} href={s.url} target="_blank" rel="noopener noreferrer" title={s.snippet}>
                  🔗 {s.title || s.url}
                </a>
              ))}
            </div>
          )}
        </div>
      ))}

      {loading && (
        <div className="msg assistant" style={{ maxWidth: 80 }}>
          <div className="typing">
            <span /><span /><span />
          </div>
        </div>
      )}
    </div>
  )
}

function emotionEmoji(emotion) {
  const map = {
    neutral: '😐', happy: '😊', sad: '😢',
    angry: '😠', fearful: '😨', surprised: '😲',
  }
  return map[emotion] ?? '🤔'
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''
}
