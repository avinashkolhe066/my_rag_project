import axios from 'axios'
const instance = axios.create({ baseURL: '' })
instance.interceptors.request.use(cfg => {
    const token = localStorage.getItem('rag_token')
    if (token) cfg.headers.Authorization = `Bearer ${token}`
    return cfg
})
instance.interceptors.response.use(r => r, err => {
    if (err.response?.status === 401) {
        localStorage.removeItem('rag_token')
        window.location.href = '/login'
    }
    return Promise.reject(err)
})
export default instance