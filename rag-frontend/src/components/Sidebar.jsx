import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, FolderOpen, HelpCircle, Brain, ChevronLeft, ChevronRight } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const links = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/workspaces', icon: FolderOpen,       label: 'Workspaces' },
  { to: '/quiz',       icon: Brain,            label: 'Quiz'       },
  { to: '/support',    icon: HelpCircle,       label: 'Support'    },
]

export default function Sidebar({ collapsed, setCollapsed }) {
  return (
    <motion.aside
      animate={{ width: collapsed ? 68 : 240 }}
      transition={{ duration: 0.28, ease: 'easeInOut' }}
      className="sidebar-bg h-screen fixed left-0 top-0 z-30 flex flex-col overflow-hidden">

      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 flex-shrink-0 divider" style={{ borderTop: 'none' }}>
        <div className="w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center"
          style={{ background: 'var(--accent)' }}>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}>
              <p className="font-bold text-sm t1">RAG Platform</p>
              <p className="text-xs t3" style={{ marginTop: 1 }}>AI Document Intelligence</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-hidden">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            {({ isActive }) => (
              <>
                <Icon size={17} className="flex-shrink-0" style={{ color: isActive ? 'var(--accent)' : 'var(--text-3)' }} />
                <AnimatePresence>
                  {!collapsed && (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      transition={{ duration: 0.12 }}>
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="px-3 pb-4 pt-3 flex-shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
        <button onClick={() => setCollapsed(p => !p)}
          className="w-full flex items-center justify-center p-2 rounded-xl transition-all"
          style={{ color: 'var(--text-3)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-bg)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </motion.aside>
  )
}
