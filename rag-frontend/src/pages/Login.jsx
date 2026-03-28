import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from '../components/ThemeToggle'
import toast from 'react-hot-toast'

export default function Login() {
  const [form, setForm]     = useState({ email: '', password: '' })
  const [show, setShow]     = useState(false)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate  = useNavigate()

  const submit = async e => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(form.email, form.password)
      toast.success('Welcome back!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.message || 'Login failed')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--page-bg)' }}>
      <div className="fixed top-4 right-4"><ThemeToggle /></div>

      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md">

        {/* Brand */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--accent)' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold t1">RAG Platform</h1>
          <p className="t3 text-sm mt-1">Sign in to your account</p>
        </div>

        {/* Card */}
        <div className="card p-7">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="label block mb-2">Email</label>
              <div className="relative">
                <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-4)' }} />
                <input type="email" value={form.email}
                  onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                  placeholder="you@example.com" required
                  className="input pl-10" />
              </div>
            </div>

            <div>
              <label className="label block mb-2">Password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-4)' }} />
                <input type={show ? 'text' : 'password'} value={form.password}
                  onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                  placeholder="••••••••" required
                  className="input pl-10 pr-11" />
                <button type="button" onClick={() => setShow(p => !p)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 transition-all"
                  style={{ color: 'var(--text-4)' }}>
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className="btn btn-primary w-full py-3 mt-2">
              {loading
                ? <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                : 'Sign In'}
            </button>
          </form>

          <hr className="divider mt-5" />
          <p className="text-center text-sm t3 mt-4">
            No account?{' '}
            <Link to="/register" className="font-semibold" style={{ color: 'var(--accent)' }}>Register</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
