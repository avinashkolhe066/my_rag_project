
import React, { useState } from 'react'
import { ArrowRight, FileText, Clock, AlertTriangle } from 'lucide-react'
import '../deleteButton.css'
import CardPattern from './CardPattern'
import '../cardPattern.css'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

export default function WorkspaceCard({ workspace, onDelete, index }) {
  const [confirm, setConfirm] = useState(false)
  const navigate = useNavigate()
  const date = new Date(workspace.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.06 }}
      className="card card-pattern-hover p-5 flex flex-col gap-4">
      <CardPattern />

      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm t1 truncate">{workspace.name}</h3>
          <div className="flex items-center gap-1.5 mt-1">
            <Clock size={11} style={{ color: 'var(--text-4)' }} />
            <span className="text-xs t3">{date}</span>
          </div>
        </div>
        <span className={`badge ${workspace.hasFile ? 'badge-green' : 'badge-yellow'} flex-shrink-0`}>
          {workspace.hasFile ? '● File Ready' : '○ No File'}
        </span>
      </div>

      {/* File name pill */}
      {workspace.fileName && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl"
          style={{ background: 'var(--card-alt)', border: '1px solid var(--border)' }}>
          <FileText size={13} style={{ color: 'var(--accent)' }} className="flex-shrink-0" />
          <span className="text-xs t2 truncate">{workspace.fileName}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 mt-auto">
        <motion.button whileTap={{ scale: 0.97 }}
          onClick={() => navigate(`/workspace/${workspace.id}`)}
          className="btn btn-primary flex-1 text-sm py-2">
          Open <ArrowRight size={14} />
        </motion.button>
        <motion.button whileTap={{ scale: 0.95 }}
          onClick={() => setConfirm(true)}
          className="delete-anim-btn">
          {/* Bin top */}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 69 14" className="svgIcon bin-top">
            <g clipPath="url(#clip0_35_24)">
              <path fill="white" d="M20.8232 2.62734L19.9948 4.21304C19.8224 4.54309 19.4808 4.75 19.1085 4.75H4.92857C2.20246 4.75 0 6.87266 0 9.5C0 12.1273 2.20246 14.25 4.92857 14.25H64.0714C66.7975 14.25 69 12.1273 69 9.5C69 6.87266 66.7975 4.75 64.0714 4.75H49.8915C49.5192 4.75 49.1776 4.54309 49.0052 4.21305L48.1768 2.62734C47.3451 1.00938 45.6355 0 43.7719 0H25.2281C23.3645 0 21.6549 1.00938 20.8232 2.62734ZM64.0023 20.0648C64.0397 19.4882 63.5822 19 63.0044 19H5.99556C5.4178 19 4.96025 19.4882 4.99766 20.0648L8.19375 69.3203C8.44018 73.0758 11.6746 76 15.5712 76H53.4288C57.3254 76 60.5598 73.0758 60.8062 69.3203L64.0023 20.0648Z" />
            </g>
            <defs>
              <clipPath id="clip0_35_24">
                <rect fill="white" height="14" width="69"></rect>
              </clipPath>
            </defs>
          </svg>
          {/* Bin bottom */}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 69 57" className="svgIcon bin-bottom">
            <g clipPath="url(#clip0_35_22)">
              <path fill="white" d="M20.8232 -16.3727L19.9948 -14.787C19.8224 -14.4569 19.4808 -14.25 19.1085 -14.25H4.92857C2.20246 -14.25 0 -12.1273 0 -9.5C0 -6.8727 2.20246 -4.75 4.92857 -4.75H64.0714C66.7975 -4.75 69 -6.8727 69 -9.5C69 -12.1273 66.7975 -14.25 64.0714 -14.25H49.8915C49.5192 -14.25 49.1776 -14.4569 49.0052 -14.787L48.1768 -16.3727C47.3451 -17.9906 45.6355 -19 43.7719 -19H25.2281C23.3645 -19 21.6549 -17.9906 20.8232 -16.3727ZM64.0023 1.0648C64.0397 0.4882 63.5822 0 63.0044 0H5.99556C5.4178 0 4.96025 0.4882 4.99766 1.0648L8.19375 50.3203C8.44018 54.0758 11.6746 57 15.5712 57H53.4288C57.3254 57 60.5598 54.0758 60.8062 50.3203L64.0023 1.0648Z" />
            </g>
            <defs>
              <clipPath id="clip0_35_22">
                <rect fill="white" height="57" width="69"></rect>
              </clipPath>
            </defs>
          </svg>
        </motion.button>
      </div>

      {/* Delete confirm modal */}
      <AnimatePresence>
        {confirm && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(6px)' }}
            onClick={() => setConfirm(false)}>
            <motion.div initial={{ scale: 0.92, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.92, opacity: 0 }}
              onClick={e => e.stopPropagation()}
              className="card p-6 w-full max-w-sm"
              style={{ boxShadow: 'var(--shadow-lg)' }}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: 'var(--red-bg)', border: '1px solid var(--red)' }}>
                  <AlertTriangle size={18} style={{ color: 'var(--red)' }} />
                </div>
                <div>
                  <p className="font-semibold t1 text-sm">Delete Workspace?</p>
                  <p className="t3 text-xs mt-0.5">This cannot be undone.</p>
                </div>
              </div>
              <p className="t2 text-sm mb-5">
                "<span className="font-semibold t1">{workspace.name}</span>" and all its data will be permanently deleted.
              </p>
              <div className="flex gap-3">
                <button onClick={() => setConfirm(false)} className="btn btn-secondary flex-1 text-sm py-2">Cancel</button>
                <button onClick={() => { onDelete(workspace.id); setConfirm(false) }}
                  className="btn btn-danger flex-1 text-sm py-2 justify-center">Delete</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
