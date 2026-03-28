import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Upload, MessageSquare, Brain, Trophy,
  FolderPlus, ChevronDown, ChevronUp,
  FileText, Database, Search, Zap, Shield, HelpCircle
} from 'lucide-react'
import Sidebar from '../components/Sidebar'
import Navbar from '../components/Navbar'

// ── Workflow Steps ────────────────────────────────────────────────────────────
const STEPS = [
  {
    number: '01',
    icon: FolderPlus,
    title: 'Create a Workspace',
    desc: 'Each workspace holds one document and its own isolated chat history. Create as many as you need.',
    color: '#6366f1',
    bg: 'rgba(99,102,241,0.12)',
  },
  {
    number: '02',
    icon: Upload,
    title: 'Upload Your Document',
    desc: 'Drop in a PDF, TXT, CSV, or JSON file. The platform indexes it automatically using AI embeddings.',
    color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.12)',
  },
  {
    number: '03',
    icon: MessageSquare,
    title: 'Chat with Your Document',
    desc: 'Ask anything in natural language. The AI retrieves the most relevant passages and answers accurately.',
    color: '#06b6d4',
    bg: 'rgba(6,182,212,0.12)',
  },
  {
    number: '04',
    icon: Trophy,
    title: 'Test Your Knowledge',
    desc: 'Generate MCQ quizzes from your document at Easy, Medium, or Hard difficulty to reinforce learning.',
    color: '#f59e0b',
    bg: 'rgba(245,158,11,0.12)',
  },
]

// ── Features ──────────────────────────────────────────────────────────────────
const FEATURES = [
  { icon: Brain,     label: 'Hybrid AI Search',      desc: 'Combines semantic (FAISS) and keyword (BM25) search for maximum accuracy', color: '#6366f1' },
  { icon: FileText,  label: 'Multi-format Support',  desc: 'PDF, TXT, CSV, and JSON files — all intelligently parsed', color: '#8b5cf6' },
  { icon: Database,  label: 'SQL for Tabular Data',  desc: 'CSV and JSON files are auto-loaded into SQL — query with plain English', color: '#06b6d4' },
  { icon: Search,    label: 'Semantic Chunking',      desc: 'Documents are split at sentence boundaries to preserve meaning', color: '#10b981' },
  { icon: Zap,       label: 'Streaming Answers',      desc: 'Responses stream word-by-word so you see results immediately', color: '#f59e0b' },
  { icon: Shield,    label: 'Workspace Isolation',    desc: 'Each workspace has its own index, history, and data — fully separated', color: '#ef4444' },
]

// ── FAQ ───────────────────────────────────────────────────────────────────────
const FAQS = [
  {
    q: 'What file types are supported?',
    a: 'PDF, TXT, CSV, and JSON. PDFs are parsed page-by-page. CSV/JSON are loaded into a SQL database for structured querying. TXT files are chunked and semantically indexed.',
  },
  {
    q: 'Why does my PDF give incomplete answers?',
    a: 'Scanned PDFs (images of text) cannot be read — only text-based PDFs work. If your PDF was created by scanning physical pages, the text extraction will be empty. Try copy-pasting the text into a TXT file instead.',
  },
  {
    q: 'How does the AI find the right answer?',
    a: 'We use Hybrid Search — FAISS finds semantically similar passages, BM25 finds exact keyword matches, and Reciprocal Rank Fusion merges both rankings. This gives better results than either method alone.',
  },
  {
    q: 'Can I upload multiple files to one workspace?',
    a: 'Each workspace holds one file at a time. To work with multiple documents, create separate workspaces — one per document. This keeps chat history and indexes isolated.',
  },
  {
    q: 'Why does the quiz say "Could not retrieve content"?',
    a: 'This usually means the file was uploaded before a recent platform update. Re-upload the file and try generating the quiz again.',
  },
  {
    q: 'What is the difference between RAG, SQL, and Chat responses?',
    a: 'RAG (green badge) = answer from document passages. SQL (yellow badge) = answer from structured CSV/JSON data via database query. Chat (blue badge) = general greeting or conversation with no document lookup.',
  },
]

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.div
      layout
      className="rounded-2xl overflow-hidden cursor-pointer"
      style={{ background: 'var(--card-alt)', border: '1px solid var(--border)' }}
      onClick={() => setOpen(o => !o)}>
      <div className="flex items-center justify-between px-5 py-4 gap-4">
        <span className="font-semibold t1 text-sm">{q}</span>
        <div className="flex-shrink-0" style={{ color: 'var(--accent)' }}>
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="px-5 pb-4 text-sm t2 leading-relaxed"
          style={{ borderTop: '1px solid var(--border)' }}>
          <p className="pt-3">{a}</p>
        </motion.div>
      )}
    </motion.div>
  )
}

export default function SupportPage() {
  const [collapsed, setCollapsed] = useState(false)
  const sw = collapsed ? 68 : 240

  return (
    <div className="min-h-screen" style={{ background: 'var(--page-bg)' }}>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <Navbar sidebarWidth={sw} />

      <main style={{ marginLeft: sw, paddingTop: 64, transition: 'margin-left 0.28s ease' }}>
        <div className="max-w-4xl mx-auto px-6 py-10 space-y-16">

          {/* ── Hero ──────────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            className="text-center space-y-3">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold mb-2"
              style={{ background: 'var(--accent-bg)', color: 'var(--accent)', border: '1px solid var(--accent-border)' }}>
              <HelpCircle size={12} /> Support & Guide
            </div>
            <h1 className="text-3xl font-bold t1">How to Use RAG Platform</h1>
            <p className="t3 text-sm max-w-xl mx-auto">
              A step-by-step guide to uploading documents, chatting with AI, and generating quizzes from your content.
            </p>
          </motion.div>

          {/* ── Workflow Steps — flowing design ───────────────── */}
          <section className="space-y-4">
            <h2 className="font-bold t1 text-lg">Platform Workflow</h2>
            <div className="relative">
              {/* Connector line */}
              <div className="absolute left-8 top-10 bottom-10 w-0.5 hidden md:block"
                style={{ background: 'linear-gradient(to bottom, #6366f1, #8b5cf6, #06b6d4, #f59e0b)' }} />

              <div className="space-y-4">
                {STEPS.map((step, i) => (
                  <motion.div key={i}
                    initial={{ opacity: 0, x: -24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex gap-5 items-start">

                    {/* Icon circle */}
                    <div className="relative flex-shrink-0 z-10">
                      <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                        style={{ background: step.bg, border: `2px solid ${step.color}` }}>
                        <step.icon size={24} style={{ color: step.color }} />
                      </div>
                      <div className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full flex items-center justify-center text-white font-bold"
                        style={{ background: step.color, fontSize: '9px' }}>
                        {i + 1}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 card p-5 rounded-2xl"
                      style={{ borderLeft: `3px solid ${step.color}` }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-xs" style={{ color: step.color }}>{step.number}</span>
                        <h3 className="font-bold t1 text-sm">{step.title}</h3>
                      </div>
                      <p className="t2 text-sm leading-relaxed">{step.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </section>

          {/* ── Features grid ─────────────────────────────────── */}
          <section className="space-y-4">
            <h2 className="font-bold t1 text-lg">Platform Features</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {FEATURES.map((f, i) => (
                <motion.div key={i}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07 }}
                  className="card p-5 rounded-2xl space-y-3 hover:scale-[1.02] transition-transform">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: `${f.color}18`, border: `1px solid ${f.color}40` }}>
                    <f.icon size={18} style={{ color: f.color }} />
                  </div>
                  <div>
                    <p className="font-semibold t1 text-sm">{f.label}</p>
                    <p className="t3 text-xs mt-1 leading-relaxed">{f.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </section>

          {/* ── Supported file types ──────────────────────────── */}
          <section className="space-y-4">
            <h2 className="font-bold t1 text-lg">Supported File Types</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { ext: 'PDF',  desc: 'Text-based PDFs',     color: '#ef4444', tip: 'Best for documents, reports, papers' },
                { ext: 'TXT',  desc: 'Plain text files',    color: '#10b981', tip: 'Notes, articles, transcripts' },
                { ext: 'CSV',  desc: 'Spreadsheet data',    color: '#f59e0b', tip: 'Tables, datasets, exports' },
                { ext: 'JSON', desc: 'Structured data',     color: '#6366f1', tip: 'API exports, config, records' },
              ].map((t, i) => (
                <motion.div key={i}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.08 }}
                  className="card p-4 rounded-2xl text-center space-y-2">
                  <div className="w-12 h-12 rounded-xl mx-auto flex items-center justify-center font-bold text-sm"
                    style={{ background: `${t.color}18`, color: t.color, border: `1px solid ${t.color}40` }}>
                    {t.ext}
                  </div>
                  <p className="font-semibold t1 text-xs">{t.desc}</p>
                  <p className="t3" style={{ fontSize: '10px' }}>{t.tip}</p>
                </motion.div>
              ))}
            </div>
          </section>

          {/* ── FAQ ───────────────────────────────────────────── */}
          <section className="space-y-4">
            <h2 className="font-bold t1 text-lg">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {FAQS.map((faq, i) => (
                <motion.div key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}>
                  <FAQItem q={faq.q} a={faq.a} />
                </motion.div>
              ))}
            </div>
          </section>

          {/* ── Bottom tip ────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
            className="rounded-2xl p-6 text-center"
            style={{ background: 'var(--accent-bg)', border: '1px solid var(--accent-border)' }}>
            <p className="font-semibold t1 text-sm mb-1">💡 Pro Tip</p>
            <p className="t2 text-sm">
              For best results with PDFs, use text-based PDFs (not scanned images). 
              For data analysis, CSV files give the most accurate answers since they use SQL queries directly.
            </p>
          </motion.div>

        </div>
      </main>
    </div>
  )
}