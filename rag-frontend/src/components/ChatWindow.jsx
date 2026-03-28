import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Trash2, MessageSquare, Square, PenLine, BarChart2, List, Search } from 'lucide-react'
import ChartMessage from './ChartMessage'
import { motion, AnimatePresence } from 'framer-motion'
import MessageBubble from './MessageBubble'
import toast from 'react-hot-toast'
import { streamQuery, clearHistory, getHistory, getVizData } from '../api/workspace.service'
import { FileDown } from 'lucide-react'

const SUGGESTIONS_WITH_FILE = [
  'Give me a summary of this document',
  'What are the key points?',
  'List all important information from this document',
  'Write a brief report based on this document',
]

// Action chips shown after AI responses — context-aware quick follow-ups
const ACTION_CHIPS = {
  visualization:   ['Download PDF', 'Analyze top performers', 'Show department breakdown'],
  agent_generate:  ['Write another version', 'Make it more formal', 'Make it shorter'],
  agent_analyze:   ['Show me the full list', 'Write a report on this', 'Compare with others'],
  agent_transform: ['Export as a table', 'Summarize this further', 'Find more details'],
  sql_natural:     ['Write an email about this', 'Give me more details', 'Show top 5'],
  sql_aggregate:   ['Write a report on this', 'Show me details', 'Compare with average'],
  rag:             ['Tell me more', 'Summarize this', 'Write a report on this topic'],
}

const SUGGESTIONS_NO_FILE = [
  'Hi! What can you help me with?',
  'What types of files can I upload?',
  'How does this platform work?',
]

// Blinking cursor shown while streaming
function StreamingCursor() {
  return (
    <motion.span
      animate={{ opacity: [1, 0, 1] }}
      transition={{ repeat: Infinity, duration: 0.7 }}
      style={{ display: 'inline-block', width: '2px', height: '14px',
        background: 'var(--accent)', borderRadius: '1px', marginLeft: '2px', verticalAlign: 'middle' }}
    />
  )
}

export default function ChatWindow({ workspaceId, hasFile }) {
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [streaming, setStreaming]   = useState(false)
  const [streamText, setStreamText] = useState('')
  const [streamMeta, setStreamMeta] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const bottomRef  = useRef()
  const inputRef   = useRef()
  const abortRef   = useRef(null)

  // Load chat history from server on mount / workspace change
  useEffect(() => {
    let cancelled = false
    setMessages([])
    setLoadingHistory(true)

    const loadHistory = async () => {
      // Hard timeout — never hang on history forever
      const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('History timeout')), 4000)
      )

      try {
        console.log('[History] Fetching for workspace:', workspaceId)
        const res = await Promise.race([getHistory(workspaceId), timeout])
        console.log('[History] Raw response:', JSON.stringify(res.data))

        if (cancelled) return

        const raw = res.data?.history
        if (!Array.isArray(raw) || raw.length === 0) {
          console.log('[History] Empty or no history')
          return
        }

        const converted = []
        for (const entry of raw) {
          if (entry.role === 'user') {
            converted.push({ role: 'user', content: typeof entry.content === 'string' ? entry.content : String(entry.content || '') })
          } else if (entry.role === 'assistant') {
            converted.push({ role: 'ai', content: typeof entry.content === 'string' ? entry.content : String(entry.content || ''), queryType: 'rag' })
          }
        }
        if (converted.length > 0) setMessages(converted)

      } catch (err) {
        // Timeout or network error — just show empty chat, don't block UI
        console.warn('[History] Skipped:', err?.message)
      } finally {
        if (!cancelled) setLoadingHistory(false)
      }
    }

    loadHistory()

    return () => { cancelled = true }
  }, [workspaceId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamText])

  const stopStream = () => {
    abortRef.current?.()
    abortRef.current = null
    setStreaming(false)
  }

  const send = useCallback((q) => {
    const question = (q || input).trim()
    if (!question || streaming) return
    setInput('')

    // Add user message
    setMessages(p => [...p, { role: 'user', content: question }])

    // Start streaming
    setStreaming(true)
    setStreamText('')
    setStreamMeta(null)

    let accumulated = ''
    let meta = null

    const cleanup = streamQuery(workspaceId, question, {
      onWord: (word) => {
        accumulated += word
        setStreamText(accumulated)
      },
      onMeta: (m) => {
        meta = m
        setStreamMeta(m)
      },
      onDone: async () => {
        // If visualization token present — fetch full chart data separately
        let vizData = null
        if (meta?.viz_token) {
          try {
            const r = await getVizData(meta.viz_token)
            vizData = r.data?.viz_data || null
          } catch (e) {
            console.error('[VizData] fetch failed:', e)
          }
        }

        // Auto-trigger PDF download if pdf_token received
        if (meta?.pdf_token) {
          const authToken = localStorage.getItem('rag_token') || ''
          fetch(`/api/workspaces/pdf/${meta.pdf_token}`, {
            headers: { Authorization: `Bearer ${authToken}` }
          })
            .then(res => res.blob())
            .then(blob => {
              const url = URL.createObjectURL(blob)
              const a   = document.createElement('a')
              a.href     = url
              a.download = 'Analytics_Report.pdf'
              document.body.appendChild(a)
              a.click()
              document.body.removeChild(a)
              URL.revokeObjectURL(url)
            })
            .catch(err => console.error('PDF download failed:', err))
        }

        // For email results, the answer is the EMAIL_SENT_* signal
        // which was streamed as a word — use it directly as content
        const finalContent = meta?.answer || (typeof accumulated === 'string' ? accumulated || '...' : '...')

        setMessages(p => [...p, {
          role: 'ai',
          content: finalContent,
          queryType: meta?.query_type,
          confidence: meta?.confidence,
          intentLabel: meta?.intent_label,
          intent: meta?.intent,
          vizData,
          pdfToken: meta?.pdf_token || null,
        }])
        setStreamText('')
        setStreamMeta(null)
        setStreaming(false)
        abortRef.current = null
        inputRef.current?.focus()
      },
      onError: (err) => {
        const msg = err || 'Something went wrong. Please try again.'
        setMessages(p => [...p, { role: 'ai', content: msg, queryType: 'error' }])
        setStreamText('')
        setStreamMeta(null)
        setStreaming(false)
        abortRef.current = null
      },
    })

    abortRef.current = cleanup
  }, [input, streaming, workspaceId])

  const clear = async () => {
    try {
      await clearHistory(workspaceId)
      setMessages([])
      toast.success('History cleared')
    } catch { toast.error('Failed to clear history') }
  }

  const suggestions = hasFile ? SUGGESTIONS_WITH_FILE : SUGGESTIONS_NO_FILE

  return (
    <div className="flex flex-col h-full">

      {/* ── Header ─────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3.5 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <MessageSquare size={16} style={{ color: 'var(--accent)' }} />
          <span className="font-semibold text-sm t1">Chat</span>
          {messages.length > 0 && (
            <span className="text-xs t3">· {Math.floor(messages.length / 2)} exchange{Math.floor(messages.length / 2) !== 1 ? 's' : ''}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Stop streaming button */}
          {streaming && (
            <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              onClick={stopStream}
              className="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg transition-all"
              style={{ background: 'var(--red-bg)', border: '1px solid var(--red)', color: 'var(--red)' }}>
              <Square size={10} fill="currentColor" /> Stop
            </motion.button>
          )}
          {messages.length > 0 && !streaming && (
            <button onClick={clear}
              className="flex items-center gap-1.5 text-xs t3 transition-all"
              onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}>
              <Trash2 size={12} /> Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Messages ───────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {loadingHistory ? (
          // Skeleton loading state
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 py-2">
            {[1, 2, 3].map(i => (
              <div key={i} className={`flex gap-3 ${i % 2 === 0 ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className="w-8 h-8 rounded-xl flex-shrink-0"
                  style={{ background: 'var(--card-alt)' }} />
                <motion.div
                  animate={{ opacity: [0.4, 0.8, 0.4] }}
                  transition={{ repeat: Infinity, duration: 1.4, delay: i * 0.2 }}
                  className="h-10 rounded-2xl"
                  style={{
                    background: 'var(--card-alt)',
                    width: `${40 + i * 15}%`,
                    border: '1px solid var(--border)'
                  }} />
              </div>
            ))}
          </motion.div>
        ) : messages.length === 0 && !streaming ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
            <div className="text-center mb-4">
              {hasFile
                ? <p className="t3 text-xs">Ask anything about your document</p>
                : <div className="space-y-1">
                    <p className="t2 text-sm font-medium">👋 Hello! I'm your RAG assistant.</p>
                    <p className="t3 text-xs">You can chat with me now — upload a file to ask document questions.</p>
                  </div>}
            </div>
            {suggestions.map((s, i) => (
              <motion.button key={i}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                onClick={() => send(s)}
                className="w-full text-left px-4 py-3 rounded-xl text-sm t2 transition-all card"
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}>
                {s}
              </motion.button>
            ))}
          </motion.div>
        ) : (
          <>
            {/* Committed messages */}
            {messages.map((m, i) => (
              <div key={i}>
                <MessageBubble index={i}
                  message={m.content} isUser={m.role === 'user'}
                  queryType={m.queryType} confidence={m.confidence}
                  intentLabel={m.intentLabel} pdfToken={m.pdfToken} />
                {/* Chart visualization — renders below message bubble */}
                {m.vizData && (
                  <div className="ml-11 mt-2">
                    <ChartMessage vizData={m.vizData} />
                  </div>
                )}

                {/* Action chips — show after last AI message only */}
                {!m.isUser && m.role === 'ai' && i === messages.length - 1 && !streaming && ACTION_CHIPS[m.queryType] && (
                  <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                    className="flex flex-wrap gap-2 ml-11 mt-1 mb-1">
                    {ACTION_CHIPS[m.queryType].map((chip, ci) => (
                      <button key={ci} onClick={() => send(chip)}
                        className="text-xs px-3 py-1.5 rounded-xl transition-all"
                        style={{
                          background: 'var(--card-alt)',
                          border: '1px solid var(--border)',
                          color: 'var(--text-3)',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)' }}
                        onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-3)' }}>
                        {chip}
                      </button>
                    ))}
                  </motion.div>
                )}
              </div>
            ))}

            {/* Live streaming bubble */}
            <AnimatePresence>
              {streaming && (
                <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }}
                  className="flex gap-3">
                  {/* Bot avatar */}
                  <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-1"
                    style={{ background: 'var(--card-alt)', border: '1px solid var(--border)' }}>
                    <motion.div
                      animate={{ scale: [1, 1.15, 1] }}
                      transition={{ repeat: Infinity, duration: 1.2 }}
                      className="w-3 h-3 rounded-full"
                      style={{ background: 'var(--accent)' }} />
                  </div>

                  {/* Streaming text bubble */}
                  <div className="max-w-[76%]">
                    <div className="px-4 py-3 text-sm"
                      style={{
                        background: 'var(--card-alt)',
                        border: '1px solid var(--border)',
                        borderRadius: '4px 18px 18px 18px',
                        color: 'var(--text-1)',
                        lineHeight: '1.65',
                      }}>
                      {streamText
                        ? <>{streamText}<StreamingCursor /></>
                        : <div className="flex gap-1.5 items-center py-1">
                            {[0,1,2].map(j => (
                              <motion.div key={j}
                                animate={{ y: [0, -4, 0] }}
                                transition={{ repeat: Infinity, duration: 0.7, delay: j * 0.14 }}
                                className="w-1.5 h-1.5 rounded-full"
                                style={{ background: 'var(--text-3)' }} />
                            ))}
                          </div>
                      }
                    </div>

                    {/* Streaming status */}
                    {streamMeta && (
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }}
                          className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent)' }} />
                        <span className="text-xs t3">Generating answer…</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* ── Input ──────────────────────────────── */}
      <div className="px-5 py-4 flex-shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
        {!hasFile && (
          <p className="text-xs t3 mb-2 text-center">
            💡 Upload a file above to ask document questions
          </p>
        )}
        <div className="flex gap-2 items-end p-2 rounded-2xl transition-all"
          style={{ background: 'var(--input-bg)', border: '1.5px solid var(--border)' }}
          onFocusCapture={e => e.currentTarget.style.borderColor = 'var(--accent)'}
          onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border)'}>
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)}
            disabled={streaming || loadingHistory}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder={loadingHistory ? 'Loading history…' : streaming ? 'Generating answer…' : hasFile ? 'Ask a question… (Enter to send)' : 'Say hello or ask a question…'}
            rows={1}
            style={{
              resize: 'none', minHeight: '38px', maxHeight: '110px',
              background: 'transparent', color: 'var(--text-1)',
              outline: 'none', border: 'none', fontSize: '14px',
              flex: 1, padding: '8px', opacity: streaming ? 0.5 : 1,
            }}
            className="placeholder:text-[var(--text-4)]" />
          <motion.button whileTap={{ scale: 0.88 }}
            onClick={streaming ? stopStream : () => send()}
            className="btn w-9 h-9 p-0 rounded-xl flex-shrink-0"
            style={{
              background: streaming ? 'var(--red-bg)' : (!input.trim() ? 'var(--card-alt)' : 'var(--accent)'),
              border: streaming ? '1px solid var(--red)' : 'none',
              color: streaming ? 'var(--red)' : 'white',
              opacity: (!streaming && !input.trim()) ? 0.4 : 1,
            }}>
            {streaming
              ? <Square size={13} fill="currentColor" />
              : <Send size={14} />}
          </motion.button>
        </div>
      </div>
    </div>
  )
}