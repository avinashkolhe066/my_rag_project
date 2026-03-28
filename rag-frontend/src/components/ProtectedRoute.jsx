import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from './LoadingSpinner'
export default function ProtectedRoute({ children }) {
    const { user, loading } = useAuth()
    if (loading) return <LoadingSpinner />
    return user ? children : <Navigate to="/login" replace />
}