import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { User, Mail, Lock } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import ThemeToggle from '../components/ThemeToggle'
import toast from 'react-hot-toast'

export default function Register() {
  const [form, setForm]       = useState({ name: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate     = useNavigate()

  const submit = async e => {
    e.preventDefault()
    if (form.password.length < 6) return toast.error('Password must be at least 6 characters')
    setLoading(true)
    try {
      await register(form.name, form.email, form.password)
      toast.success('Account created!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.message || 'Registration failed')
    }
    setLoading(false)
  }

  const fields = [
    { key: 'name',     label: 'Full Name', type: 'text',     icon: User, placeholder: 'John Doe'         },
    { key: 'email',    label: 'Email',     type: 'email',    icon: Mail, placeholder: 'you@example.com'  },
    { key: 'password', label: 'Password',  type: 'password', icon: Lock, placeholder: '••••••••'         },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--page-bg)' }}>
      <div className="fixed top-4 right-4"><ThemeToggle /></div>

      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--accent)' }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold t1">Create Account</h1>
          <p className="t3 text-sm mt-1">Start using RAG Platform today</p>
        </div>

        <div className="card p-7">
          <form onSubmit={submit} className="space-y-4">
            {fields.map(({ key, label, type, icon: Icon, placeholder }) => (
              <div key={key}>
                <label className="label block mb-2">{label}</label>
                <div className="relative">
                  <Icon size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-4)' }} />
                  <input type={type} value={form[key]}
                    onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
                    placeholder={placeholder} required className="input pl-10" />
                </div>
              </div>
            ))}

            <button type="submit" disabled={loading} className="btn btn-primary w-full py-3 mt-2">
              {loading
                ? <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                : 'Create Account'}
            </button>
          </form>

          <hr className="divider mt-5" />
          <p className="text-center text-sm t3 mt-4">
            Already registered?{' '}
            <Link to="/login" className="font-semibold" style={{ color: 'var(--accent)' }}>Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
