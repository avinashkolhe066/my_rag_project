import React, { useState, useEffect } from 'react'
import { FolderOpen, FileCheck, FolderX, Plus, LayoutDashboard } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import Sidebar from '../components/Sidebar'
import Navbar from '../components/Navbar'
import StatCard from '../components/StatCard'
import WorkspaceCard from '../components/WorkspaceCard'
import CreateWorkspaceModal from '../components/CreateWorkspaceModal'
import { getWorkspaces, createWorkspace, deleteWorkspace } from '../api/workspace.service'

export default function Dashboard() {
  const [workspaces, setWorkspaces] = useState([])
  const [loading, setLoading]       = useState(true)
  const [modal, setModal]           = useState(false)
  const [collapsed, setCollapsed]   = useState(false)
  const sw = collapsed ? 68 : 240

  useEffect(() => { load() }, [])

  const load = async () => {
    try {
      const r = await getWorkspaces()
      setWorkspaces(r.data.workspaces || [])
    } catch { toast.error('Failed to load workspaces') }
    setLoading(false)
  }

  const handleCreate = async name => {
    try {
      await createWorkspace(name)
      toast.success('Workspace created!')
      setModal(false)
      load()
    } catch (e) { toast.error(e.response?.data?.message || 'Failed to create workspace') }
  }

  const handleDelete = async id => {
    try {
      await deleteWorkspace(id)
      toast.success('Workspace deleted')
      setWorkspaces(p => p.filter(w => w.id !== id))
    } catch { toast.error('Failed to delete workspace') }
  }

  const withFile = workspaces.filter(w => w.hasFile).length

  return (
    <div className="min-h-screen" style={{ background: 'var(--page-bg)' }}>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <Navbar sidebarWidth={sw} />

      <main style={{ marginLeft: sw, paddingTop: 64, transition: 'margin-left 0.28s ease' }}>
        <div className="p-6 max-w-7xl mx-auto">

          {/* Page header */}
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between mb-7">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <LayoutDashboard size={19} style={{ color: 'var(--accent)' }} />
                <h1 className="title">Dashboard</h1>
              </div>
              <p className="subtitle">Manage your document workspaces</p>
            </div>
            <motion.button whileTap={{ scale: 0.96 }} onClick={() => setModal(true)}
              className="btn btn-primary">
              <Plus size={17} /> New Workspace
            </motion.button>
          </motion.div>

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-7">
            <StatCard icon={FolderOpen}  label="Total Workspaces"  value={workspaces.length} delay={0}   iconColor="var(--accent)"  />
            <StatCard icon={FileCheck}   label="Files Uploaded"    value={withFile}          delay={0.07} iconColor="var(--green)"  />
            <StatCard icon={FolderX}     label="Empty Workspaces"  value={workspaces.length - withFile} delay={0.14} iconColor="var(--yellow)" />
          </div>

          {/* Workspace grid */}
          {loading ? (
            <div className="flex justify-center py-20">
              <div className="h-8 w-8 border-[3px] rounded-full animate-spin"
                style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
            </div>
          ) : workspaces.length === 0 ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-24 gap-4">
              <div className="w-20 h-20 rounded-3xl flex items-center justify-center"
                style={{ background: 'var(--card-alt)', border: '1px solid var(--border)' }}>
                <FolderOpen size={34} style={{ color: 'var(--text-4)' }} />
              </div>
              <div className="text-center">
                <p className="font-semibold t1 text-lg">No workspaces yet</p>
                <p className="t3 text-sm mt-1">Create your first workspace to get started</p>
              </div>
              <button onClick={() => setModal(true)} className="btn btn-primary mt-1">
                <Plus size={16} /> Create Workspace
              </button>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {workspaces.map((ws, i) => (
                <WorkspaceCard key={ws.id} workspace={ws} onDelete={handleDelete} index={i} />
              ))}
            </div>
          )}
        </div>
      </main>

      <CreateWorkspaceModal open={modal} onClose={() => setModal(false)} onCreate={handleCreate} />
    </div>
  )
}
