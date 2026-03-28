
import React from 'react'
import { motion } from 'framer-motion'
import CardPattern from './CardPattern'
import '../cardPattern.css'

export default function StatCard({ icon: Icon, label, value, iconColor = 'var(--accent)', delay = 0 }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}
      className="card card-pattern-hover p-5 flex items-center gap-4">
      <CardPattern />
      <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: 'var(--card-alt)', border: '1px solid var(--border)' }}>
        <Icon size={20} style={{ color: iconColor }} />
      </div>
      <div>
        <p className="label">{label}</p>
        <p className="text-2xl font-bold t1 mt-0.5">{value}</p>
      </div>
    </motion.div>
  )
}
