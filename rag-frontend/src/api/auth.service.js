import axios from './axios'
export const login = (email, password) => axios.post('/api/auth/login', { email, password })
export const register = (name, email, password) => axios.post('/api/auth/register', { name, email, password })
export const getMe = () => axios.get('/api/auth/me')