import React, { useState, useEffect, useRef } from 'react'
import { User, Bot, Database, Search, AlertCircle, MessageCircle, Volume2, VolumeX, Pause, Play, PenLine, BarChart2, List, Zap } from 'lucide-react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'

const TYPE = {
  greeting:        { label: 'Chat',      icon: MessageCircle, color: 'var(--green)',   bg: 'var(--green-bg)'   },
  rag:             { label: 'RAG',       icon: Search,        color: 'var(--accent)',  bg: 'var(--accent-bg)'  },
  sql_natural:     { label: 'SQL',       icon: Database,      color: 'var(--yellow)',  bg: 'var(--yellow-bg)'  },
  sql_raw:         { label: 'SQL Raw',   icon: Database,      color: 'var(--yellow)',  bg: 'var(--yellow-bg)'  },
  sql_aggregate:   { label: 'SQL',       icon: Database,      color: 'var(--yellow)',  bg: 'var(--yellow-bg)'  },
  agent_generate:  { label: '✍️ Write',  icon: PenLine,       color: '#a855f7',        bg: 'rgba(168,85,247,0.1)' },
  agent_analyze:   { label: '📊 Analyze',icon: BarChart2,     color: '#06b6d4',        bg: 'rgba(6,182,212,0.1)'  },
  agent_transform: { label: '🔄 Extract',icon: List,          color: '#f59e0b',        bg: 'rgba(245,158,11,0.1)' },
  agent_action:    { label: '⚡ Action', icon: Zap,           color: '#10b981',        bg: 'rgba(16,185,129,0.1)' },
  visualization:   { label: '📊 Charts', icon: BarChart2,     color: '#6366f1',        bg: 'rgba(99,102,241,0.1)'  },
  error:           { label: 'Error',     icon: AlertCircle,   color: 'var(--red)',     bg: 'var(--red-bg)'     },
}

// ─────────────────────────────────────────────
// Markdown renderer — styled for both themes
// ─────────────────────────────────────────────
function MarkdownContent({ content }) {
  return (
    <ReactMarkdown
      components={{
        // Headings
        h1: ({ children }) => (
          <h1 style={{ color: 'var(--text-1)', fontSize: '17px', fontWeight: 700, marginBottom: '8px', marginTop: '12px' }}>
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 style={{ color: 'var(--text-1)', fontSize: '15px', fontWeight: 700, marginBottom: '6px', marginTop: '10px' }}>
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 style={{ color: 'var(--text-1)', fontSize: '14px', fontWeight: 600, marginBottom: '6px', marginTop: '10px' }}>
            {children}
          </h3>
        ),
        // Paragraph
        p: ({ children }) => (
          <p style={{ color: 'var(--text-1)', fontSize: '14px', lineHeight: '1.65', marginBottom: '8px' }}>
            {children}
          </p>
        ),
        // Bold
        strong: ({ children }) => (
          <strong style={{ color: 'var(--text-1)', fontWeight: 700 }}>{children}</strong>
        ),
        // Italic
        em: ({ children }) => (
          <em style={{ color: 'var(--text-2)', fontStyle: 'italic' }}>{children}</em>
        ),
        // Unordered list
        ul: ({ children }) => (
          <ul style={{ paddingLeft: '18px', marginBottom: '8px', marginTop: '4px' }}>{children}</ul>
        ),
        // Ordered list
        ol: ({ children }) => (
          <ol style={{ paddingLeft: '18px', marginBottom: '8px', marginTop: '4px' }}>{children}</ol>
        ),
        // List item
        li: ({ children }) => (
          <li style={{ color: 'var(--text-1)', fontSize: '14px', lineHeight: '1.65', marginBottom: '3px' }}>
            {children}
          </li>
        ),
        // Inline code
        code: ({ inline, children }) =>
          inline ? (
            <code style={{
              background: 'var(--hover-bg)',
              color: 'var(--accent)',
              padding: '1px 6px',
              borderRadius: '5px',
              fontSize: '12.5px',
              fontFamily: 'monospace',
            }}>
              {children}
            </code>
          ) : (
            <pre style={{
              background: 'var(--input-bg)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '12px',
              overflowX: 'auto',
              marginBottom: '8px',
              marginTop: '4px',
            }}>
              <code style={{ color: 'var(--accent)', fontSize: '12.5px', fontFamily: 'monospace' }}>
                {children}
              </code>
            </pre>
          ),
        // Blockquote
        blockquote: ({ children }) => (
          <blockquote style={{
            borderLeft: '3px solid var(--accent)',
            paddingLeft: '12px',
            marginLeft: '0',
            marginBottom: '8px',
            color: 'var(--text-2)',
            fontStyle: 'italic',
          }}>
            {children}
          </blockquote>
        ),
        // Horizontal rule
        hr: () => <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '10px 0' }} />,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

// ─────────────────────────────────────────────
// Speaker Button — per message TTS
// ─────────────────────────────────────────────
function SpeakerButton({ text }) {
  const [status, setStatus] = useState('idle')
  const uttRef = useRef(null)

  // Strip markdown symbols for cleaner speech
  const cleanText = text
    .replace(/#{1,6}\s/g, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/`(.*?)`/g, '$1')
    .replace(/>\s/g, '')
    .replace(/[-*+]\s/g, '')
    .trim()

  useEffect(() => {
    return () => { if (uttRef.current) window.speechSynthesis.cancel() }
  }, [])

  const handleClick = () => {
    if (status === 'playing') { window.speechSynthesis.pause(); setStatus('paused'); return }
    if (status === 'paused')  { window.speechSynthesis.resume(); setStatus('playing'); return }

    window.speechSynthesis.cancel()
    setStatus('loading')

    const utt = new SpeechSynthesisUtterance(cleanText)
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(v =>
      v.name.includes('Google') || v.name.includes('Natural') ||
      v.name.includes('Premium') || v.lang === 'en-US'
    )
    if (preferred) utt.voice = preferred
    utt.rate = 0.95

    utt.onstart  = () => setStatus('playing')
    utt.onend    = () => { setStatus('idle'); uttRef.current = null }
    utt.onerror  = () => { setStatus('idle'); uttRef.current = null }

    uttRef.current = utt
    window.speechSynthesis.speak(utt)
  }

  const handleStop = (e) => {
    e.stopPropagation()
    window.speechSynthesis.cancel()
    setStatus('idle')
    uttRef.current = null
  }

  const iconMap = {
    idle:    { Icon: Volume2, title: 'Listen' },
    loading: { Icon: Volume2, title: 'Starting...' },
    playing: { Icon: Pause,   title: 'Pause' },
    paused:  { Icon: Play,    title: 'Resume' },
  }
  const { Icon, title } = iconMap[status]
  const isActive = status === 'playing' || status === 'paused'

  return (
    <div className="flex items-center gap-1">
      <motion.button whileTap={{ scale: 0.88 }} whileHover={{ scale: 1.08 }}
        onClick={handleClick} title={title}
        className="flex items-center justify-center w-7 h-7 rounded-lg transition-all"
        style={{
          background: isActive ? 'var(--accent-bg)' : 'transparent',
          border: `1px solid ${isActive ? 'var(--accent-border)' : 'transparent'}`,
          color: isActive ? 'var(--accent)' : 'var(--text-3)',
          cursor: status === 'loading' ? 'wait' : 'pointer',
        }}
        onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = 'var(--card-alt)'; e.currentTarget.style.border = '1px solid var(--border)'; e.currentTarget.style.color = 'var(--text-1)' }}}
        onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.border = '1px solid transparent'; e.currentTarget.style.color = 'var(--text-3)' }}}>
        {status === 'loading' ? (
          <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
            className="w-3.5 h-3.5 border-2 rounded-full"
            style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
        ) : (
          <Icon size={13} />
        )}
      </motion.button>

      {isActive && (
        <motion.button initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }}
          whileTap={{ scale: 0.88 }} onClick={handleStop} title="Stop"
          className="flex items-center justify-center w-7 h-7 rounded-lg"
          style={{ background: 'var(--red-bg)', border: '1px solid var(--red)', color: 'var(--red)' }}>
          <VolumeX size={12} />
        </motion.button>
      )}

      {status === 'playing' && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-0.5 ml-1">
          {[0, 1, 2].map(i => (
            <motion.div key={i}
              animate={{ height: ['4px', '10px', '4px'] }}
              transition={{ repeat: Infinity, duration: 0.7, delay: i * 0.15, ease: 'easeInOut' }}
              className="w-0.5 rounded-full"
              style={{ background: 'var(--accent)' }} />
          ))}
        </motion.div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// Main MessageBubble
// ─────────────────────────────────────────────
// ── Email Sent Card ───────────────────────────────────────────────────────────
function EmailSentCard({ message }) {
  const isBulk   = message.startsWith('EMAIL_SENT_BULK::')
  const isSingle = message.startsWith('EMAIL_SENT_SINGLE::')

  if (isSingle) {
    const [, to, subject] = message.split('::')
    return (
      <div className="rounded-2xl overflow-hidden"
        style={{ border: '1px solid var(--border)', background: 'var(--card-alt)', minWidth: '260px', maxWidth: '400px' }}>
        {/* Green header */}
        <div className="flex items-center gap-2.5 px-4 py-3"
          style={{ background: 'linear-gradient(135deg, #064e3b, #065f46)' }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(255,255,255,0.15)' }}>
            <span style={{ fontSize: '16px' }}>✉️</span>
          </div>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '13px' }}>Email Sent</div>
            <div style={{ color: '#6ee7b7', fontSize: '11px' }}>Delivered successfully</div>
          </div>
        </div>
        {/* Details */}
        <div className="px-4 py-3 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span style={{ fontSize: '11px', color: 'var(--text-3)', fontWeight: 600, minWidth: 52 }}>TO</span>
            <span style={{ fontSize: '13px', color: 'var(--text-1)', fontFamily: 'monospace' }}>{to}</span>
          </div>
          <div style={{ height: '1px', background: 'var(--border)' }} />
          <div className="flex items-start gap-2">
            <span style={{ fontSize: '11px', color: 'var(--text-3)', fontWeight: 600, minWidth: 52, paddingTop: 2 }}>SUBJECT</span>
            <span style={{ fontSize: '13px', color: 'var(--text-1)', lineHeight: '1.4' }}>{subject}</span>
          </div>
        </div>
      </div>
    )
  }

  if (isBulk) {
    const [, sent, failed, ...errParts] = message.split('::')
    const errors = errParts.join('::')
    return (
      <div className="rounded-2xl overflow-hidden"
        style={{ border: '1px solid var(--border)', background: 'var(--card-alt)', minWidth: '260px', maxWidth: '400px' }}>
        {/* Header */}
        <div className="flex items-center gap-2.5 px-4 py-3"
          style={{ background: 'linear-gradient(135deg, #1e3a5f, #1e40af)' }}>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(255,255,255,0.15)' }}>
            <span style={{ fontSize: '16px' }}>📬</span>
          </div>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '13px' }}>Bulk Email Complete</div>
            <div style={{ color: '#93c5fd', fontSize: '11px' }}>Campaign finished</div>
          </div>
        </div>
        {/* Stats */}
        <div className="px-4 py-3 flex gap-4">
          <div className="flex flex-col items-center px-4 py-2 rounded-xl flex-1"
            style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
            <span style={{ fontSize: '22px', fontWeight: 800, color: '#10b981' }}>{sent}</span>
            <span style={{ fontSize: '11px', color: 'var(--text-3)', marginTop: '2px' }}>Sent</span>
          </div>
          <div className="flex flex-col items-center px-4 py-2 rounded-xl flex-1"
            style={{ background: failed > 0 ? 'rgba(239,68,68,0.08)' : 'rgba(100,116,139,0.08)',
                     border: `1px solid ${failed > 0 ? 'rgba(239,68,68,0.2)' : 'rgba(100,116,139,0.15)'}` }}>
            <span style={{ fontSize: '22px', fontWeight: 800, color: failed > 0 ? '#ef4444' : 'var(--text-3)' }}>{failed}</span>
            <span style={{ fontSize: '11px', color: 'var(--text-3)', marginTop: '2px' }}>Failed</span>
          </div>
        </div>
        {errors && (
          <div className="px-4 pb-3">
            <div style={{ fontSize: '11px', color: '#ef4444', background: 'rgba(239,68,68,0.06)',
                          border: '1px solid rgba(239,68,68,0.15)', borderRadius: '8px', padding: '8px 10px' }}>
              {errors}
            </div>
          </div>
        )}
      </div>
    )
  }

  return null
}

export default function MessageBubble({ message: rawMessage, isUser, queryType, confidence, index, intentLabel, pdfToken }) {
  // Coerce message to string — prevents [object Object]
  const message = typeof rawMessage === 'string' ? rawMessage : JSON.stringify(rawMessage) || '...'

  const handleReDownload = () => {
    if (!pdfToken) return
    const jwt = localStorage.getItem('rag_token') || ''
    const a = document.createElement('a')
    a.href = `/api/workspaces/pdf/${pdfToken}?auth=${jwt}`
    a.download = 'Analytics_Report.pdf'
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
  }

  const isEmailSent = message.startsWith('EMAIL_SENT_SINGLE::') || message.startsWith('EMAIL_SENT_BULK::')

  const type = TYPE[queryType]

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 16 : -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.02 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

      {/* Avatar */}
      <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-1"
        style={{ background: isUser ? 'var(--accent)' : 'var(--card-alt)', border: '1px solid var(--border)' }}>
        {isUser
          ? <User size={13} color="white" />
          : <Bot size={13} style={{ color: 'var(--text-3)' }} />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[76%] flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'}`}>
        <div className="px-4 py-3 text-sm"
          style={isUser
            ? { background: 'var(--accent)', color: '#fff', borderRadius: '18px 4px 18px 18px' }
            : { background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '4px 18px 18px 18px' }}>
          {isUser
            ? <p style={{ color: '#fff', fontSize: '14px', lineHeight: '1.6' }}>{message}</p>
            : isEmailSent
              ? <EmailSentCard message={message} />
              : <MarkdownContent content={message} />}
        </div>

        {/* Bottom row — badge + confidence + speaker */}
        {!isUser && (
          <div className="flex items-center gap-2 flex-wrap">
            {type && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-medium"
                style={{ background: type.bg, color: type.color }}>
                <type.icon size={10} /> {type.label}
              </span>
            )}

            <SpeakerButton text={message} />
            {queryType === 'pdf_report' && pdfToken && (
              <button
                onClick={handleReDownload}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl ml-1 transition-all hover:opacity-80"
                style={{
                  background: 'var(--accent-bg)',
                  border: '1px solid var(--accent-border)',
                  color: 'var(--accent)',
                }}>
                ⬇ Download PDF
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}