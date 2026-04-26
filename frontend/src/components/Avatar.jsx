import { useEffect, useRef } from 'react'

/**
 * Simple CSS/SVG avatar whose expression changes based on `emotion`.
 * Supports: neutral | happy | sad | angry | fearful | surprised
 */
const EXPRESSIONS = {
  neutral:   { face: '😐', color: '#6366f1', label: 'Neutral',   bg: '#1e1b4b' },
  happy:     { face: '😊', color: '#22c55e', label: 'Happy',     bg: '#14532d' },
  sad:       { face: '😢', color: '#60a5fa', label: 'Sad',       bg: '#1e3a5f' },
  angry:     { face: '😠', color: '#ef4444', label: 'Angry',     bg: '#450a0a' },
  fearful:   { face: '😨', color: '#f59e0b', label: 'Fearful',   bg: '#451a03' },
  surprised: { face: '😲', color: '#a855f7', label: 'Surprised', bg: '#3b0764' },
}

export default function Avatar({ emotion = 'neutral', confidence = 0.5, speaking = false }) {
  const expr = EXPRESSIONS[emotion] ?? EXPRESSIONS.neutral
  const ringRef = useRef(null)

  // Animate ring while speaking
  useEffect(() => {
    const el = ringRef.current
    if (!el) return
    if (speaking) {
      el.style.animation = 'avatarPulse 0.8s ease-in-out infinite'
    } else {
      el.style.animation = 'none'
    }
  }, [speaking])

  return (
    <>
      <style>{`
        @keyframes avatarPulse {
          0%,100% { box-shadow: 0 0 0 0 ${expr.color}55; }
          50%      { box-shadow: 0 0 0 18px ${expr.color}00; }
        }
        .avatar-face {
          transition: all 0.5s cubic-bezier(.34,1.56,.64,1);
        }
      `}</style>

      <div
        ref={ringRef}
        style={{
          width: 160,
          height: 160,
          borderRadius: '50%',
          background: `radial-gradient(circle at 35% 35%, ${expr.color}88, ${expr.bg})`,
          border: `4px solid ${expr.color}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'border-color 0.5s, background 0.5s',
          position: 'relative',
        }}
      >
        <span className="avatar-face" style={{ fontSize: 80, lineHeight: 1, userSelect: 'none' }}>
          {expr.face}
        </span>
        {speaking && (
          <span style={{
            position: 'absolute',
            bottom: 6,
            right: 6,
            width: 18,
            height: 18,
            borderRadius: '50%',
            background: '#22c55e',
            border: '2px solid #0f0f1a',
            animation: 'avatarPulse 0.8s ease-in-out infinite',
          }} />
        )}
      </div>

      <div style={{ textAlign: 'center' }}>
        <div style={{
          fontSize: '1.05rem',
          fontWeight: 600,
          color: expr.color,
          letterSpacing: '.05em',
        }}>
          {expr.label}
        </div>
        <div style={{ fontSize: '.75rem', color: '#94a3b8', marginTop: 2 }}>
          {Math.round(confidence * 100)}% confidence
        </div>
      </div>

      <div style={{
        width: '100%',
        padding: '0 8px',
      }}>
        <div style={{ fontSize: '.75rem', color: '#94a3b8', marginBottom: 4 }}>Emotion state</div>
        <div style={{
          height: 6,
          borderRadius: 99,
          background: '#1e293b',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${Math.round(confidence * 100)}%`,
            background: `linear-gradient(90deg, ${expr.color}, #a855f7)`,
            borderRadius: 99,
            transition: 'width 0.5s ease, background 0.5s ease',
          }} />
        </div>
      </div>
    </>
  )
}
