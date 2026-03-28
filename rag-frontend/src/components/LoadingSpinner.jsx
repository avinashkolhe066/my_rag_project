import React from 'react'

export default function LoadingSpinner({ size = 'lg' }) {
  const s = size === 'lg' ? 'h-11 w-11' : 'h-5 w-5'
  return (
    <div className="flex items-center justify-center min-h-screen" style={{ background: 'var(--page-bg)' }}>
      <div className={`${s} border-[3px] rounded-full animate-spin`}
        style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
    </div>
  )
}
