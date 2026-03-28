
import React, { useState } from 'react'
import { X, Plus } from 'lucide-react'
import CardPattern from './CardPattern'
import '../cardPattern.css'
import { motion, AnimatePresence } from 'framer-motion'

export default function CreateWorkspaceModal({ open, onClose, onCreate }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)

  const handle = async e => {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    await onCreate(name.trim())
    setName('')
    setLoading(false)
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(6px)' }}
          onClick={onClose}>
          <motion.div initial={{ scale: 0.93, opacity: 0, y: 16 }} animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.93, opacity: 0 }}
            onClick={e => e.stopPropagation()}
            className="card card-pattern-hover p-6 w-full max-w-md"
            style={{ boxShadow: 'var(--shadow-lg)' }}>

            <CardPattern />
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="font-bold t1 text-lg">New Workspace</h2>
                <p className="t3 text-xs mt-0.5">Create an isolated chat + file space</p>
              </div>
              <button onClick={onClose}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-all t3"
                style={{ background: 'var(--card-alt)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-bg)'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--card-alt)'}>
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handle} className="space-y-4">
              <div>
                <label className="label block mb-2">Workspace Name</label>
                <input value={name} onChange={e => setName(e.target.value)}
                  placeholder="e.g. Sales Reports Q4, Study Notes..."
                  className="input" autoFocus />
              </div>
              <button type="submit" disabled={!name.trim() || loading}
                className="btn btn-primary w-full py-3 text-sm">
                {loading
                  ? <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  : <><Plus size={16} /> Create Workspace</>}
              </button>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
