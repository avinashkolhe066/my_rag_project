import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FolderOpen } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import Sidebar from '../components/Sidebar'
import Navbar from '../components/Navbar'
import FileUpload from '../components/FileUpload'
import ChatWindow from '../components/ChatWindow'
import { getWorkspaces, ingestFile } from '../api/workspace.service'

export default function WorkspacePage() {
  const { id }   = useParams()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [loading, setLoading]     = useState(true)
  const [collapsed, setCollapsed] = useState(false)
  const sw = collapsed ? 68 : 240

  useEffect(() => { load() }, [id])

  const load = async () => {
    try {
      const r  = await getWorkspaces()
      const ws = (r.data.workspaces || []).find(w => w.id === id)
      if (!ws) { toast.error('Workspace not found'); navigate('/dashboard'); return }
      setWorkspace(ws)
    } catch { toast.error('Failed to load workspace') }
    setLoading(false)
  }

  const handleUpload = async file => {
    try {
      const r = await ingestFile(id, file)
      toast.success('File uploaded successfully!')
      setWorkspace(p => ({ ...p, hasFile: true, fileName: r.data.ingest?.fileName || file.name, fileType: r.data.ingest?.fileType }))
    } catch (e) { toast.error(e.response?.data?.message || 'Upload failed') }
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--page-bg)' }}>
      <div className="h-10 w-10 border-[3px] rounded-full animate-spin"
        style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
    </div>
  )

  return (
    <div className="min-h-screen" style={{ background: 'var(--page-bg)' }}>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <Navbar sidebarWidth={sw} />

      <main style={{ marginLeft: sw, paddingTop: 64, transition: 'margin-left 0.28s ease' }}>
        <div className="p-6 h-[calc(100vh-64px)] flex flex-col gap-4">

          {/* Header */}
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-4 flex-shrink-0">
            <button onClick={() => navigate('/dashboard')}
              className="flex items-center gap-1.5 text-sm t3 transition-all"
              onMouseEnter={e => e.currentTarget.style.color = 'var(--text-1)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}>
              <ArrowLeft size={15} /> Back
            </button>
            <div className="h-5 w-px" style={{ background: 'var(--border)' }} />
            <FolderOpen size={18} style={{ color: 'var(--accent)' }} />
            <h1 className="font-bold t1 text-lg">{workspace?.name}</h1>
            <span className={`badge ${workspace?.hasFile ? 'badge-green' : 'badge-yellow'}`}>
              {workspace?.hasFile ? 'File Ready' : 'No File'}
            </span>
          </motion.div>

          {/* Split layout */}
          <div className="flex gap-4 flex-1 min-h-0">

            {/* Left panel — compact document panel */}
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }}
              className="card flex-shrink-0 p-4 flex flex-col gap-3 overflow-y-auto"
              style={{ width: '220px' }}>

              {/* Title */}
              <div>
                <h2 className="font-semibold t1 text-xs uppercase tracking-wide">Document</h2>
              </div>

              {/* File status */}
              <FileUpload onUpload={handleUpload} hasFile={workspace?.hasFile} fileName={workspace?.fileName} compact />

              {/* File info — only when file exists */}
              {workspace?.hasFile && (
                <div className="pt-3" style={{ borderTop: '1px solid var(--border)' }}>
                  <p className="label mb-2 text-xs">FILE INFO</p>
                  <div className="space-y-1.5">
                    {[
                      { label: 'Name', value: workspace.fileName },
                      { label: 'Type', value: workspace.fileType?.toUpperCase() || '—' },
                    ].map(row => (
                      <div key={row.label} className="flex flex-col gap-0.5">
                        <span className="t3" style={{ fontSize: '10px' }}>{row.label}</span>
                        <span className="t2 font-medium truncate" style={{ fontSize: '11px' }}>{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>

            {/* Right panel — chat */}
            <motion.div initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}
              className="card flex-1 flex flex-col min-h-0 overflow-hidden">
              <ChatWindow workspaceId={id} hasFile={workspace?.hasFile} />
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  )
}