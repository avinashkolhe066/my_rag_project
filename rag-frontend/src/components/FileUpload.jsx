import React, { useState, useRef } from 'react'
import { Upload, CheckCircle, Loader } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function FileUpload({ onUpload, hasFile, fileName, compact = false }) {
  const [dragging, setDragging]   = useState(false)
  const [uploading, setUploading] = useState(false)
  const ref = useRef()

  const handle = async file => {
    if (!file) return
    setUploading(true)
    await onUpload(file)
    setUploading(false)
  }

  return (
    <div className="space-y-2">

      {/* File ready badge */}
      {hasFile && (
        <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 px-3 py-2 rounded-xl"
          style={{ background: 'var(--green-bg)', border: '1px solid var(--green)' }}>
          <CheckCircle size={13} style={{ color: 'var(--green)' }} className="flex-shrink-0" />
          <div className="min-w-0">
            <p className="font-semibold" style={{ color: 'var(--green)', fontSize: '11px' }}>File Ready</p>
            <p className="t3 truncate mt-0.5" style={{ fontSize: '10px' }}>{fileName}</p>
          </div>
        </motion.div>
      )}

      {/* Drop zone — compact or full */}
      <motion.div
        animate={{ borderColor: dragging ? 'var(--accent)' : 'var(--border)' }}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files[0]) }}
        onClick={() => ref.current?.click()}
        className="border-2 border-dashed rounded-xl cursor-pointer transition-all text-center"
        style={{
          background: dragging ? 'var(--accent-bg)' : 'var(--card-alt)',
          padding: compact ? '16px 10px' : '28px 16px',
        }}>
        <input ref={ref} type="file" accept=".csv,.json,.pdf,.txt" className="hidden"
          onChange={e => handle(e.target.files[0])} />

        <AnimatePresence mode="wait">
          {uploading ? (
            <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-2">
              <Loader size={compact ? 18 : 26} className="animate-spin" style={{ color: 'var(--accent)' }} />
              <p style={{ fontSize: '11px' }} className="t2">Indexing...</p>
            </motion.div>
          ) : (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-2">
              <motion.div animate={{ scale: dragging ? 1.08 : 1 }}
                className="rounded-xl flex items-center justify-center"
                style={{
                  background: 'var(--accent-bg)',
                  border: '1px solid var(--accent-border)',
                  width: compact ? '36px' : '48px',
                  height: compact ? '36px' : '48px',
                }}>
                <Upload size={compact ? 15 : 20} style={{ color: 'var(--accent)' }} />
              </motion.div>
              <div>
                <p className="t1 font-medium" style={{ fontSize: compact ? '11px' : '13px' }}>
                  {hasFile ? 'Replace file' : 'Drop file here'}
                </p>
                <p className="t3 mt-0.5" style={{ fontSize: '10px' }}>CSV, JSON, PDF, TXT</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}