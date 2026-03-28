import React, { createContext, useContext, useState, useEffect } from 'react'
import axios from '../api/axios'
import toast from 'react-hot-toast'
const AuthContext = createContext()
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    useEffect(() => {
        const token = localStorage.getItem('rag_token')
        if (token) {
            axios.get('/api/auth/me').then(r => setUser(r.data.user)).catch(() => { localStorage.removeItem('rag_token'); }).finally(() => setLoading(false))
        } else setLoading(false)
    }, [])
    const login = async (email, password) => {
        const r = await axios.post('/api/auth/login', { email, password })
        localStorage.setItem('rag_token', r.data.token)
        setUser(r.data.user)
        return r.data
    }
    const register = async (name, email, password) => {
        const r = await axios.post('/api/auth/register', { name, email, password })
        localStorage.setItem('rag_token', r.data.token)
        setUser(r.data.user)
        return r.data
    }
    const logout = () => {
        localStorage.removeItem('rag_token')
        setUser(null)
        toast.success('Logged out successfully')
    }
    return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)