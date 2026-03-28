import React, { useState, useEffect } from 'react'
import { FolderOpen, Plus } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import Sidebar from '../components/Sidebar'
import Navbar from '../components/Navbar'
import WorkspaceCard from '../components/WorkspaceCard'
import CreateWorkspaceModal from '../components/CreateWorkspaceModal'
import LoadingSpinner from '../components/LoadingSpinner'
import { getWorkspaces, createWorkspace, deleteWorkspace } from '../api/workspace.service'

export default function WorkspacesPage() {
    const [workspaces, setWorkspaces] = useState([])
    const [loading, setLoading] = useState(true)
    const [modal, setModal] = useState(false)
    const [collapsed, setCollapsed] = useState(false)
    const sw = collapsed ? 72 : 240

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

    return (
        <div className="min-h-screen bg-light-100 dark:bg-dark-200">
            <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
            <Navbar sidebarWidth={sw} />
            <main className="transition-all duration-300" style={{ marginLeft: sw, paddingTop: 64 }}>
                <div className="p-6 max-w-7xl mx-auto">
                    {/* Page header */}
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <FolderOpen size={20} className="text-primary-600 dark:text-primary-500" />
                                <h1 className="text-dark-900 dark:text-light-50 text-2xl font-bold">Workspaces</h1>
                            </div>
                            <p className="text-light-600 dark:text-dark-700 text-sm">View and manage your document workspaces</p>
                        </div>
                        <motion.button whileTap={{ scale: 0.95 }} onClick={() => setModal(true)}
                            className="btn btn-primary font-medium text-sm shadow-lg shadow-primary-900/30"
                            style={{ background: 'var(--accent)', color: '#fff', border: 'none' }}>
                            <Plus size={18} /> New Workspace
                        </motion.button>
                    </motion.div>

                    {/* Workspaces grid */}
                    {loading ? (
                        <div className="flex justify-center py-20"><div className="h-8 w-8 border-3 border-primary-600 border-t-transparent rounded-full animate-spin" /></div>
                    ) : workspaces.length === 0 ? (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                            className="flex flex-col items-center justify-center py-24 gap-4">
                            <div className="w-20 h-20 bg-light-200 dark:bg-dark-100 rounded-3xl flex items-center justify-center">
                                <FolderOpen size={36} style={{ color: 'var(--text-1)' }} />
                            </div>
                            <div className="text-center">
                                <p className="t1 font-semibold text-lg">No workspaces yet</p>
                                <p className="t3 text-sm mt-1">Create your first workspace to get started</p>
                            </div>
                            <button onClick={() => setModal(true)}
                                className="btn btn-primary mt-2" style={{ background: 'var(--accent)', color: '#fff' }}>
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