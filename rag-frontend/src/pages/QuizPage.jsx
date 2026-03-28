import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain, ChevronRight, ChevronLeft, Clock, CheckCircle,
  XCircle, ArrowLeft, RotateCcw, Trophy, Target,
  AlertCircle, FileText, Zap
} from 'lucide-react'
import toast from 'react-hot-toast'
import Sidebar from '../components/Sidebar'
import Navbar from '../components/Navbar'
import { getWorkspaces, generateQuiz } from '../api/workspace.service'

const DIFFICULTIES = [
  { value: 'easy',   label: 'Easy',   color: 'var(--green)',  bg: 'var(--green-bg)',  border: 'var(--green)',  desc: 'Basic recall & facts' },
  { value: 'medium', label: 'Medium', color: 'var(--yellow)', bg: 'var(--yellow-bg)', border: 'var(--yellow)', desc: 'Concepts & application' },
  { value: 'hard',   label: 'Hard',   color: 'var(--red)',    bg: 'var(--red-bg)',    border: 'var(--red)',    desc: 'Deep analysis & inference' },
]

const QUESTION_COUNTS = [5, 10, 15, 20]
const OPTION_KEYS = ['A', 'B', 'C', 'D']
const TIMER_SECONDS = { easy: 30, medium: 45, hard: 60 }

function ScoreBadge({ score }) {
  if (score >= 81) return <span style={{ color: 'var(--green)' }} className="font-bold">🏆 Excellent!</span>
  if (score >= 51) return <span style={{ color: 'var(--yellow)' }} className="font-bold">👍 Good Job!</span>
  return <span style={{ color: 'var(--red)' }} className="font-bold">📚 Keep Practicing</span>
}

function TimerRing({ seconds, total }) {
  const pct = seconds / total
  const r = 20
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)
  const color = pct > 0.5 ? '#22c55e' : pct > 0.25 ? '#eab308' : '#ef4444'
  return (
    <div className="relative w-14 h-14 flex items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" width="56" height="56">
        <circle cx="28" cy="28" r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
        <circle cx="28" cy="28" r={r} fill="none" stroke={color} strokeWidth="4"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s linear, stroke 0.3s' }} />
      </svg>
      <span className="font-bold text-sm z-10 t1">{seconds}</span>
    </div>
  )
}

// ── Setup Screen ──────────────────────────────────────────────────────────────
function SetupScreen({ workspaces, onStart }) {
  const [selectedWs, setSelectedWs] = useState('')
  const [difficulty, setDifficulty] = useState('medium')
  const [numQ, setNumQ] = useState(5)
  const ws = workspaces.filter(w => w.hasFile)
  const canStart = selectedWs && difficulty

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto space-y-6">

      {/* Header */}
      <div className="text-center space-y-2">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto"
          style={{ background: 'var(--accent-bg)', border: '1px solid var(--accent-border)' }}>
          <Brain size={32} style={{ color: 'var(--accent)' }} />
        </div>
        <h1 className="text-2xl font-bold t1">Quiz Generator</h1>
        <p className="text-sm t3">Generate an MCQ quiz from your uploaded documents</p>
      </div>

      {/* Step 1 */}
      <div className="card rounded-2xl p-5 space-y-3">
        <h2 className="t1 font-semibold flex items-center gap-2">
          <span className="w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold"
            style={{ background: 'var(--accent)', color: '#fff' }}>1</span>
          Select Document
        </h2>
        {ws.length === 0 ? (
          <div className="flex items-center gap-3 p-4 rounded-xl"
            style={{ background: 'var(--yellow-bg)', border: '1px solid var(--yellow)' }}>
            <AlertCircle size={18} style={{ color: 'var(--yellow)' }} className="flex-shrink-0" />
            <p className="text-sm" style={{ color: 'var(--yellow)' }}>No workspaces with uploaded files. Please upload a file first.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {ws.map(w => (
              <motion.button key={w.id} whileTap={{ scale: 0.98 }} onClick={() => setSelectedWs(w.id)}
                className="w-full flex items-center gap-3 p-3.5 rounded-xl border transition-all text-left"
                style={{
                  background: selectedWs === w.id ? 'var(--accent-bg)' : 'var(--card-alt)',
                  borderColor: selectedWs === w.id ? 'var(--accent)' : 'var(--border)',
                }}>
                <FileText size={16} style={{ color: selectedWs === w.id ? 'var(--accent)' : 'var(--text-3)' }} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate t1">{w.name}</p>
                  <p className="text-xs t3 truncate">{w.fileName}</p>
                </div>
                {selectedWs === w.id && <CheckCircle size={16} style={{ color: 'var(--accent)' }} className="flex-shrink-0" />}
              </motion.button>
            ))}
          </div>
        )}
      </div>

      {/* Step 2 */}
      <div className="card rounded-2xl p-5 space-y-3">
        <h2 className="t1 font-semibold flex items-center gap-2">
          <span className="w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold"
            style={{ background: 'var(--accent)', color: '#fff' }}>2</span>
          Select Difficulty
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {DIFFICULTIES.map(d => (
            <motion.button key={d.value} whileTap={{ scale: 0.97 }} onClick={() => setDifficulty(d.value)}
              className="flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all"
              style={{
                background: difficulty === d.value ? d.bg : 'var(--card-alt)',
                borderColor: difficulty === d.value ? d.border : 'var(--border)',
                color: d.color,
              }}>
              <span className="font-semibold text-sm">{d.label}</span>
              <span className="text-xs text-center leading-tight t3">{d.desc}</span>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Step 3 */}
      <div className="card rounded-2xl p-5 space-y-3">
        <h2 className="t1 font-semibold flex items-center gap-2">
          <span className="w-6 h-6 rounded-full text-xs flex items-center justify-center font-bold"
            style={{ background: 'var(--accent)', color: '#fff' }}>3</span>
          Number of Questions
        </h2>
        <div className="flex gap-3">
          {QUESTION_COUNTS.map(n => (
            <motion.button key={n} whileTap={{ scale: 0.95 }} onClick={() => setNumQ(n)}
              className="flex-1 py-3 rounded-xl border font-bold text-lg transition-all"
              style={{
                background: numQ === n ? 'var(--accent)' : 'var(--card-alt)',
                borderColor: numQ === n ? 'var(--accent)' : 'var(--border)',
                color: numQ === n ? '#fff' : 'var(--text-3)',
              }}>
              {n}
            </motion.button>
          ))}
        </div>
        <p className="text-xs t3 text-center">Timer per question: {TIMER_SECONDS[difficulty]}s</p>
      </div>

      {/* Start */}
      <motion.button whileTap={{ scale: 0.97 }} onClick={() => onStart(selectedWs, difficulty, numQ)}
        disabled={!canStart}
        className="btn btn-primary w-full py-4 rounded-2xl font-bold text-lg disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3">
        <Zap size={22} /> Generate Quiz
      </motion.button>
    </motion.div>
  )
}

// ── Loading Screen ────────────────────────────────────────────────────────────
function LoadingScreen({ difficulty, numQ }) {
  const msgs = ['Reading your document...', 'Extracting key concepts...', 'Crafting questions...', 'Preparing answer options...', 'Almost ready...']
  const [msgIdx, setMsgIdx] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setMsgIdx(p => (p + 1) % msgs.length), 2000)
    return () => clearInterval(t)
  }, [])
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] gap-6">
      <div className="relative w-24 h-24">
        <div className="absolute inset-0 rounded-full" style={{ border: '4px solid var(--border)' }} />
        <div className="absolute inset-0 rounded-full animate-spin"
          style={{ border: '4px solid transparent', borderTopColor: 'var(--accent)' }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <Brain size={32} style={{ color: 'var(--accent)' }} />
        </div>
      </div>
      <div className="text-center space-y-2">
        <h2 className="font-bold text-xl t1">Generating Your Quiz</h2>
        <AnimatePresence mode="wait">
          <motion.p key={msgIdx} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="text-sm t3">{msgs[msgIdx]}</motion.p>
        </AnimatePresence>
        <p className="text-xs t3">{numQ} {difficulty} questions · This may take 30–60 seconds</p>
      </div>
    </motion.div>
  )
}

// ── Quiz Screen ───────────────────────────────────────────────────────────────
function QuizScreen({ questions, difficulty, onFinish }) {
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState({})
  const [selected, setSelected] = useState(null)
  const [timer, setTimer] = useState(TIMER_SECONDS[difficulty])
  const [showFeedback, setShowFeedback] = useState(false)

  const total = TIMER_SECONDS[difficulty]
  const q = questions[current]
  const isLast = current === questions.length - 1
  const answered = selected !== null

  useEffect(() => {
    if (showFeedback) return
    if (timer <= 0) { handleNext(true); return }
    const t = setTimeout(() => setTimer(p => p - 1), 1000)
    return () => clearTimeout(t)
  }, [timer, showFeedback])

  const handleSelect = (opt) => {
    if (answered || showFeedback) return
    setSelected(opt)
    setAnswers(p => ({ ...p, [current]: opt }))
    setShowFeedback(true)
  }

  const handleNext = useCallback((timedOut = false) => {
    if (timedOut && !answers[current]) setAnswers(p => ({ ...p, [current]: null }))
    setShowFeedback(false)
    setSelected(null)
    if (isLast) {
      onFinish({ ...answers, ...(timedOut ? { [current]: null } : {}) })
    } else {
      setCurrent(p => p + 1)
      setTimer(TIMER_SECONDS[difficulty])
    }
  }, [current, isLast, answers, difficulty])

  const getOptionStyle = (key) => {
    if (!showFeedback) {
      if (selected === key) return { background: 'var(--accent-bg)', borderColor: 'var(--accent)', color: 'var(--accent)' }
      return { background: 'var(--card-alt)', borderColor: 'var(--border)', color: 'var(--text-2)' }
    }
    if (key === q.correct) return { background: 'var(--green-bg)', borderColor: 'var(--green)', color: 'var(--green)' }
    if (key === selected && key !== q.correct) return { background: 'var(--red-bg)', borderColor: 'var(--red)', color: 'var(--red)' }
    return { background: 'var(--card-alt)', borderColor: 'var(--border)', color: 'var(--text-3)', opacity: 0.5 }
  }

  const getKeyStyle = (key) => {
    if (showFeedback && key === q.correct) return { background: 'var(--green)', borderColor: 'var(--green)', color: '#fff' }
    if (showFeedback && key === selected && key !== q.correct) return { background: 'var(--red)', borderColor: 'var(--red)', color: '#fff' }
    if (selected === key && !showFeedback) return { background: 'var(--accent)', borderColor: 'var(--accent)', color: '#fff' }
    return { background: 'var(--card-alt)', borderColor: 'var(--border)', color: 'var(--text-3)' }
  }

  return (
    <motion.div key={current} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }}
      className="max-w-2xl mx-auto space-y-5">

      {/* Progress + Timer */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <div className="flex justify-between text-xs t3 mb-1.5">
            <span>Question {current + 1} of {questions.length}</span>
            <span>{Math.round((current / questions.length) * 100)}% complete</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
            <motion.div className="h-full rounded-full" style={{ background: 'var(--accent)' }}
              animate={{ width: `${(current / questions.length) * 100}%` }}
              transition={{ duration: 0.4 }} />
          </div>
        </div>
        <TimerRing seconds={timer} total={total} />
      </div>

      {/* Difficulty badge */}
      {(() => {
        const d = DIFFICULTIES.find(d => d.value === difficulty)
        return d ? (
          <span className="inline-block px-2.5 py-1 rounded-lg text-xs font-medium border"
            style={{ background: d.bg, borderColor: d.border, color: d.color }}>
            {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
          </span>
        ) : null
      })()}

      {/* Question */}
      <div className="card rounded-2xl p-6">
        <p className="font-semibold text-lg leading-relaxed t1">{q.question}</p>
      </div>

      {/* Options */}
      <div className="space-y-3">
        {OPTION_KEYS.map(key => (
          <motion.button key={key} whileTap={!answered ? { scale: 0.98 } : {}}
            onClick={() => handleSelect(key)}
            className="w-full flex items-center gap-4 p-4 rounded-xl border transition-all text-left"
            style={getOptionStyle(key)}>
            <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0 border"
              style={getKeyStyle(key)}>
              {key}
            </span>
            <span className="text-sm flex-1">{q.options[key]}</span>
            {showFeedback && key === q.correct && <CheckCircle size={18} style={{ color: 'var(--green)' }} className="flex-shrink-0" />}
            {showFeedback && key === selected && key !== q.correct && <XCircle size={18} style={{ color: 'var(--red)' }} className="flex-shrink-0" />}
          </motion.button>
        ))}
      </div>

      {/* Explanation */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl border"
            style={{
              background: selected === q.correct ? 'var(--green-bg)' : 'var(--red-bg)',
              borderColor: selected === q.correct ? 'var(--green)' : 'var(--red)',
            }}>
            <div className="flex items-start gap-3">
              {selected === q.correct
                ? <CheckCircle size={18} style={{ color: 'var(--green)' }} className="flex-shrink-0 mt-0.5" />
                : <XCircle size={18} style={{ color: 'var(--red)' }} className="flex-shrink-0 mt-0.5" />}
              <div>
                <p className="font-semibold text-sm mb-1"
                  style={{ color: selected === q.correct ? 'var(--green)' : 'var(--red)' }}>
                  {selected === q.correct ? 'Correct!' : `Incorrect — Answer is ${q.correct}`}
                </p>
                <p className="text-sm t2">{q.explanation}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Next */}
      {showFeedback && (
        <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          whileTap={{ scale: 0.97 }} onClick={() => handleNext()}
          className="btn btn-primary w-full py-3.5 rounded-xl font-semibold flex items-center justify-center gap-2">
          {isLast ? 'See Results' : 'Next Question'} <ChevronRight size={18} />
        </motion.button>
      )}
    </motion.div>
  )
}

// ── Results Screen ────────────────────────────────────────────────────────────
function ResultsScreen({ questions, answers, difficulty, workspaceName, onRetry, onNewQuiz }) {
  const [showReview, setShowReview] = useState(false)
  const [reviewIdx, setReviewIdx] = useState(0)

  const correct = questions.filter((q, i) => answers[i] === q.correct).length
  const total = questions.length
  const score = Math.round((correct / total) * 100)
  const skipped = questions.filter((_, i) => answers[i] === null || answers[i] === undefined).length
  const scoreColor = score >= 81 ? 'var(--green)' : score >= 51 ? 'var(--yellow)' : 'var(--red)'

  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className="max-w-2xl mx-auto space-y-5">
      {!showReview ? (
        <>
          {/* Score card */}
          <div className="card rounded-2xl p-8 text-center space-y-4">
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', delay: 0.2 }}
              className="w-24 h-24 mx-auto relative">
              <svg className="-rotate-90" width="96" height="96">
                <circle cx="48" cy="48" r="40" fill="none" stroke="var(--border)" strokeWidth="8" />
                <motion.circle cx="48" cy="48" r="40" fill="none"
                  stroke={scoreColor} strokeWidth="8" strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 40}
                  initial={{ strokeDashoffset: 2 * Math.PI * 40 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 40 * (1 - score / 100) }}
                  transition={{ duration: 1.2, delay: 0.3, ease: 'easeOut' }} />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <Trophy size={28} style={{ color: scoreColor }} />
              </div>
            </motion.div>
            <div>
              <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                className="text-5xl font-black t1">{score}%</motion.p>
              <p className="text-sm t3 mt-1">{workspaceName}</p>
              <p className="text-lg mt-2"><ScoreBadge score={score} /></p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Correct', value: correct,                       color: 'var(--green)',  bg: 'var(--green-bg)',  border: 'var(--green)' },
              { label: 'Wrong',   value: total - correct - skipped,     color: 'var(--red)',    bg: 'var(--red-bg)',    border: 'var(--red)' },
              { label: 'Skipped', value: skipped,                       color: 'var(--yellow)', bg: 'var(--yellow-bg)', border: 'var(--yellow)' },
            ].map(s => (
              <div key={s.label} className="rounded-xl p-4 text-center border"
                style={{ background: s.bg, borderColor: s.border }}>
                <p className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</p>
                <p className="text-xs t3 mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => setShowReview(true)}
              className="btn btn-secondary flex items-center justify-center gap-2 py-3 text-sm font-medium rounded-xl">
              <Target size={16} /> Review Answers
            </button>
            <button onClick={onRetry}
              className="btn btn-primary flex items-center justify-center gap-2 py-3 text-sm font-medium rounded-xl">
              <RotateCcw size={16} /> Try Again
            </button>
          </div>
          <button onClick={onNewQuiz}
            className="btn btn-secondary w-full py-3 rounded-xl text-sm">
            ← New Quiz Setup
          </button>
        </>
      ) : (
        /* Review */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button onClick={() => setShowReview(false)}
              className="flex items-center gap-2 t3 hover:t1 text-sm transition-all">
              <ChevronLeft size={16} /> Back to Results
            </button>
            <span className="text-sm t3">{reviewIdx + 1} / {questions.length}</span>
          </div>
          {questions.map((q, i) => {
            if (i !== reviewIdx) return null
            const userAns = answers[i]
            const isCorrect = userAns === q.correct
            return (
              <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                <div className="card rounded-2xl p-5">
                  <div className="flex items-start gap-3 mb-4">
                    {isCorrect
                      ? <CheckCircle size={20} style={{ color: 'var(--green)' }} className="flex-shrink-0 mt-0.5" />
                      : userAns === null
                      ? <Clock size={20} style={{ color: 'var(--yellow)' }} className="flex-shrink-0 mt-0.5" />
                      : <XCircle size={20} style={{ color: 'var(--red)' }} className="flex-shrink-0 mt-0.5" />}
                    <p className="font-semibold t1">{q.question}</p>
                  </div>
                  <div className="space-y-2">
                    {OPTION_KEYS.map(key => {
                      const isAns = key === q.correct
                      const isWrong = key === userAns && !isCorrect
                      return (
                        <div key={key} className="flex items-center gap-3 p-3 rounded-xl border text-sm"
                          style={{
                            background: isAns ? 'var(--green-bg)' : isWrong ? 'var(--red-bg)' : 'var(--card-alt)',
                            borderColor: isAns ? 'var(--green)' : isWrong ? 'var(--red)' : 'var(--border)',
                            color: isAns ? 'var(--green)' : isWrong ? 'var(--red)' : 'var(--text-3)',
                          }}>
                          <span className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                            style={{ background: 'var(--accent-bg)', color: 'var(--accent)' }}>
                            {key}
                          </span>
                          <span className="flex-1">{q.options[key]}</span>
                          {isAns && <CheckCircle size={14} style={{ color: 'var(--green)' }} />}
                          {isWrong && <XCircle size={14} style={{ color: 'var(--red)' }} />}
                        </div>
                      )
                    })}
                  </div>
                  <div className="mt-4 p-3 rounded-xl" style={{ background: 'var(--card-alt)' }}>
                    <p className="text-xs t3 font-medium mb-1">Explanation</p>
                    <p className="text-sm t2">{q.explanation}</p>
                  </div>
                  {userAns === null && (
                    <p className="mt-3 text-xs flex items-center gap-1" style={{ color: 'var(--yellow)' }}>
                      <Clock size={12} /> Time ran out — skipped
                    </p>
                  )}
                </div>
                <div className="flex gap-3">
                  <button onClick={() => setReviewIdx(p => Math.max(0, p - 1))} disabled={reviewIdx === 0}
                    className="btn btn-secondary flex-1 py-2.5 rounded-xl text-sm flex items-center justify-center gap-1 disabled:opacity-30">
                    <ChevronLeft size={16} /> Prev
                  </button>
                  <button onClick={() => setReviewIdx(p => Math.min(questions.length - 1, p + 1))} disabled={reviewIdx === questions.length - 1}
                    className="btn btn-primary flex-1 py-2.5 rounded-xl text-sm flex items-center justify-center gap-1 disabled:opacity-30">
                    Next <ChevronRight size={16} />
                  </button>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </motion.div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function QuizPage() {
  const [collapsed, setCollapsed] = useState(false)
  const sw = collapsed ? 72 : 240
  const [workspaces, setWorkspaces] = useState([])
  const [loadingWs, setLoadingWs] = useState(true)
  const [screen, setScreen] = useState('setup')
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [quizMeta, setQuizMeta] = useState({ difficulty: 'medium', numQ: 5, workspaceName: '', workspaceId: '' })

  useEffect(() => {
    getWorkspaces()
      .then(r => setWorkspaces(r.data.workspaces || []))
      .catch(() => toast.error('Failed to load workspaces'))
      .finally(() => setLoadingWs(false))
  }, [])

  const handleStart = async (wsId, difficulty, numQ) => {
    const ws = workspaces.find(w => w.id === wsId)
    setQuizMeta({ difficulty, numQ, workspaceName: ws?.name || '', workspaceId: wsId })
    setScreen('loading')
    try {
      const r = await generateQuiz(wsId, difficulty, numQ)
      const qs = r.data?.quiz?.questions || r.data?.questions || []
      if (!qs.length) throw new Error('No questions returned')
      setQuestions(qs)
      setAnswers({})
      setScreen('quiz')
    } catch (e) {
      toast.error(e.response?.data?.message || 'Failed to generate quiz. Try again.')
      setScreen('setup')
    }
  }

  return (
    <div className="min-h-screen" style={{ background: 'var(--page-bg)' }}>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <Navbar sidebarWidth={sw} />
      <main style={{ marginLeft: sw, paddingTop: 64, transition: 'margin-left 0.28s ease' }}>
        <div className="p-6">
          {screen !== 'loading' && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-4 mb-8">
              {screen !== 'setup' && (
                <button onClick={() => setScreen('setup')}
                  className="flex items-center gap-2 t3 text-sm transition-all"
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--text-1)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}>
                  <ArrowLeft size={16} /> Back
                </button>
              )}
              <div>
                <div className="flex items-center gap-2">
                  <Brain size={20} style={{ color: 'var(--accent)' }} />
                  <h1 className="text-2xl font-bold t1">
                    {screen === 'setup' ? 'Quiz Generator'
                      : screen === 'quiz' ? `${quizMeta.workspaceName} — Quiz`
                      : 'Quiz Results'}
                  </h1>
                </div>
                {screen === 'setup' && <p className="t3 text-sm mt-0.5">Test your knowledge from uploaded documents</p>}
              </div>
            </motion.div>
          )}

          <AnimatePresence mode="wait">
            {screen === 'setup' && !loadingWs && <SetupScreen key="setup" workspaces={workspaces} onStart={handleStart} />}
            {screen === 'loading' && <LoadingScreen key="loading" difficulty={quizMeta.difficulty} numQ={quizMeta.numQ} />}
            {screen === 'quiz' && questions.length > 0 && <QuizScreen key="quiz" questions={questions} difficulty={quizMeta.difficulty} onFinish={(a) => { setAnswers(a); setScreen('results') }} />}
            {screen === 'results' && <ResultsScreen key="results" questions={questions} answers={answers} difficulty={quizMeta.difficulty} workspaceName={quizMeta.workspaceName} onRetry={() => handleStart(quizMeta.workspaceId, quizMeta.difficulty, quizMeta.numQ)} onNewQuiz={() => setScreen('setup')} />}
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}