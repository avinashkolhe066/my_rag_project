import React, { useRef, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts'
import { motion } from 'framer-motion'
import { Download, TrendingUp, Users, BarChart2 } from 'lucide-react'

// ── Custom Tooltip ────────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="px-3 py-2 rounded-xl shadow-lg text-xs"
      style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', color: 'var(--text-1)' }}>
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name}: <strong>{typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</strong>
        </p>
      ))}
    </div>
  )
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KPICard({ label, value, color }) {
  return (
    <div className="rounded-2xl p-4 text-center flex-1 min-w-[100px]"
      style={{ background: 'var(--card-alt)', border: `1px solid ${color}30` }}>
      <p className="text-xl font-black" style={{ color }}>{value}</p>
      <p className="text-xs t3 mt-1">{label}</p>
    </div>
  )
}

// ── Bar Chart ─────────────────────────────────────────────────────────────────
function BarChartCard({ chart }) {
  return (
    <div className="rounded-2xl p-4 card">
      <p className="font-semibold text-sm t1 mb-3">{chart.title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chart.data} margin={{ top: 4, right: 8, left: -10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey={chart.nameKey || 'name'} tick={{ fontSize: 10, fill: 'var(--text-3)' }}
            angle={-35} textAnchor="end" interval={0} />
          <YAxis tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey={chart.dataKey || 'value'} fill={chart.color || '#6366f1'} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      {chart.total > 30 && (
        <p className="text-xs t3 text-center mt-1">Showing top 30 of {chart.total} records</p>
      )}
    </div>
  )
}

// ── Multi-Bar Chart ───────────────────────────────────────────────────────────
function MultiBarChartCard({ chart }) {
  const colors = chart.colors || ['#6366f1', '#06b6d4', '#10b981', '#f59e0b']
  return (
    <div className="rounded-2xl p-4 card">
      <p className="font-semibold text-sm t1 mb-3">{chart.title}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chart.data} margin={{ top: 4, right: 8, left: -10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-3)' }}
            angle={-35} textAnchor="end" interval={0} />
          <YAxis tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px', color: 'var(--text-2)' }} />
          {chart.keys.map((key, i) => (
            <Bar key={key} dataKey={key} fill={colors[i % colors.length]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Pie Chart ─────────────────────────────────────────────────────────────────
function PieChartCard({ chart }) {
  return (
    <div className="rounded-2xl p-4 card">
      <p className="font-semibold text-sm t1 mb-3">{chart.title}</p>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width="55%" height={200}>
          <PieChart>
            <Pie data={chart.data} cx="50%" cy="50%" outerRadius={80}
              dataKey="value" nameKey="name" label={false}>
              {chart.data.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        {/* Legend */}
        <div className="flex-1 space-y-1.5">
          {chart.data.map((entry, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: entry.color }} />
              <span className="text-xs t2 truncate">{entry.name}</span>
              <span className="text-xs t3 ml-auto font-semibold">{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Line Chart ────────────────────────────────────────────────────────────────
function LineChartCard({ chart }) {
  return (
    <div className="rounded-2xl p-4 card">
      <p className="font-semibold text-sm t1 mb-3">{chart.title}</p>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chart.data} margin={{ top: 4, right: 8, left: -10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey={chart.nameKey || 'name'} tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
          <YAxis tick={{ fontSize: 10, fill: 'var(--text-3)' }} />
          <Tooltip content={<CustomTooltip />} />
          <Line type="monotone" dataKey={chart.dataKey || 'value'}
            stroke={chart.color || '#10b981'} strokeWidth={2}
            dot={{ r: 3, fill: chart.color || '#10b981' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── PDF Download ──────────────────────────────────────────────────────────────
async function downloadPDF(containerRef, datasetLabel) {
  try {
    const html2canvas = (await import('html2canvas')).default
    const jsPDF       = (await import('jspdf')).default

    const canvas  = await html2canvas(containerRef.current, {
      scale: 2, useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    })

    const imgData = canvas.toDataURL('image/png')
    const pdf     = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pw      = pdf.internal.pageSize.getWidth()
    const ph      = pdf.internal.pageSize.getHeight()

    // Header
    pdf.setFillColor(99, 102, 241)
    pdf.rect(0, 0, pw, 18, 'F')
    pdf.setTextColor(255, 255, 255)
    pdf.setFontSize(13)
    pdf.setFont('helvetica', 'bold')
    pdf.text(`${datasetLabel} — Analysis Report`, 10, 12)
    pdf.setFontSize(8)
    pdf.text(`Generated by RAG Platform · ${new Date().toLocaleDateString()}`, pw - 10, 12, { align: 'right' })

    // Chart image
    const imgH = (canvas.height * (pw - 20)) / canvas.width
    let   yPos = 25

    if (yPos + imgH <= ph - 15) {
      pdf.addImage(imgData, 'PNG', 10, yPos, pw - 20, imgH)
    } else {
      // Multi-page if content is long
      let remaining = imgH
      let srcY      = 0
      while (remaining > 0) {
        const sliceH = Math.min(remaining, ph - yPos - 15)
        const sliceCanvas  = document.createElement('canvas')
        sliceCanvas.width  = canvas.width
        sliceCanvas.height = (sliceH / imgH) * canvas.height
        const ctx = sliceCanvas.getContext('2d')
        ctx.drawImage(canvas, 0, srcY / imgH * canvas.height, canvas.width, sliceCanvas.height, 0, 0, canvas.width, sliceCanvas.height)
        pdf.addImage(sliceCanvas.toDataURL('image/png'), 'PNG', 10, yPos, pw - 20, sliceH)
        remaining -= sliceH
        srcY      += sliceH
        if (remaining > 0) { pdf.addPage(); yPos = 10 }
      }
    }

    // Footer
    pdf.setFillColor(240, 240, 255)
    pdf.rect(0, ph - 10, pw, 10, 'F')
    pdf.setTextColor(120, 120, 180)
    pdf.setFontSize(7)
    pdf.text('RAG Platform — AI Document Intelligence', pw / 2, ph - 4, { align: 'center' })

    pdf.save(`${datasetLabel.replace(/ /g, '_')}_Analysis.pdf`)
  } catch (e) {
    console.error('PDF generation failed:', e)
    alert('PDF download failed. Make sure html2canvas and jspdf are installed.')
  }
}

// ── Main ChartMessage Component ───────────────────────────────────────────────
export default function ChartMessage({ vizData }) {
  const containerRef = useRef()
  const [downloading, setDownloading] = useState(false)

  if (!vizData) return null

  const { charts = [], kpis = [], insights, total_records, dataset_label } = vizData

  const handleDownload = async () => {
    setDownloading(true)
    await downloadPDF(containerRef, dataset_label || 'Data')
    setDownloading(false)
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="space-y-4 w-full">

      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart2 size={16} style={{ color: 'var(--accent)' }} />
          <span className="font-bold text-sm t1">{dataset_label}</span>
          <span className="text-xs t3">· {total_records} records</span>
        </div>
        <button onClick={handleDownload} disabled={downloading}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl transition-all"
          style={{
            background: 'var(--accent-bg)',
            border: '1px solid var(--accent-border)',
            color: 'var(--accent)',
            opacity: downloading ? 0.6 : 1,
          }}>
          <Download size={12} />
          {downloading ? 'Generating PDF…' : 'Download PDF'}
        </button>
      </div>

      {/* Everything captured for PDF */}
      <div ref={containerRef} className="space-y-4 p-1">

        {/* KPI Cards */}
        {kpis.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {kpis.map((kpi, i) => (
              <motion.div key={i} initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }} transition={{ delay: i * 0.05 }}
                className="flex-1 min-w-[90px]">
                <KPICard {...kpi} />
              </motion.div>
            ))}
          </div>
        )}

        {/* Charts grid */}
        <div className="grid grid-cols-1 gap-4">
          {charts.map((chart, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}>
              {chart.type === 'bar'      && <BarChartCard chart={chart} />}
              {chart.type === 'multibar' && <MultiBarChartCard chart={chart} />}
              {chart.type === 'pie'      && <PieChartCard chart={chart} />}
              {chart.type === 'line'     && <LineChartCard chart={chart} />}
            </motion.div>
          ))}
        </div>

        {/* AI Insights */}
        {insights && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
            className="rounded-2xl p-4"
            style={{ background: 'var(--accent-bg)', border: '1px solid var(--accent-border)' }}>
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={14} style={{ color: 'var(--accent)' }} />
              <span className="font-semibold text-xs" style={{ color: 'var(--accent)' }}>AI Insights</span>
            </div>
            <p className="text-sm t2 leading-relaxed">{insights}</p>
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}