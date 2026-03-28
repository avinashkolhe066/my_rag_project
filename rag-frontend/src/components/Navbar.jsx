import React from 'react'
import { LogOut, User } from 'lucide-react'
import '../logoutButton.css'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from './ThemeToggle'

export default function Navbar({ sidebarWidth, title }) {
  const { user, logout } = useAuth()
  return (
    <motion.header
      animate={{ left: sidebarWidth }}
      transition={{ duration: 0.28 }}
      className="fixed top-0 right-0 h-16 z-20 flex items-center justify-between px-6"
      style={{
        background: 'var(--card-bg)',
        borderBottom: '1px solid var(--border)',
        backdropFilter: 'blur(12px)',
      }}>

      {/* Left — page title or welcome */}
      {title ? (
        <h1 className="font-bold t1 text-lg">{title}</h1>
      ) : (
        <p className="font-semibold text-sm t1">
          Welcome back,{' '}
          <span style={{ color: 'var(--accent)' }}>{user?.name?.split(' ')[0]}</span>
        </p>
      )}

      {/* Right controls */}
      <div className="flex items-center gap-3">
        <ThemeToggle />

        {/* User pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl"
          style={{ background: 'var(--card-alt)', border: '1px solid var(--border)' }}>
          <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: 'var(--accent)' }}>
            <User size={12} color="white" />
          </div>
          <span className="text-xs t2 hidden sm:block">{user?.email}</span>
        </div>

        {/* Logout (Animated) */}
        {/* Desktop/Tablet */}
        <button onClick={logout} className="logout-anim-btn hidden sm:flex">
          <span className="logout-sign">
            <LogOut size={17} />
          </span>
          <span className="logout-text">Logout</span>
        </button>
        {/* Mobile */}
        <button onClick={logout} className="logout-anim-btn sm:hidden">
          <span className="logout-sign">
            <LogOut size={17} />
          </span>
        </button>
      </div>
    </motion.header>
  )
}