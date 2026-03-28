import axios from './axios'

export const getWorkspaces    = ()             => axios.get('/api/workspaces')
export const createWorkspace  = (name)         => axios.post('/api/workspaces', { name })
export const deleteWorkspace  = (id)           => axios.delete(`/api/workspaces/${id}`)
export const ingestFile       = (id, file)     => {
  const form = new FormData()
  form.append('file', file)
  return axios.post(`/api/workspaces/${id}/ingest`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const queryWorkspace   = (id, question) => axios.post(`/api/workspaces/${id}/query`, { question })
export const clearHistory     = (id)           => axios.delete(`/api/workspaces/${id}/history`)
export const getHistory       = (id)           => axios.get(`/api/workspaces/${id}/history`)
export const generateQuiz     = (id, difficulty, num_questions) =>
  axios.post(`/api/workspaces/${id}/quiz`, { difficulty, num_questions })

/**
 * Stream answer word-by-word via SSE.
 * Gets the JWT token from the same axios instance so auth is always consistent.
 */
export const getVizData = (token) =>
  axios.get(`/api/workspaces/viz/${token}`)

export const getPdfUrl = (token) => `/api/workspaces/pdf/${token}`

export const streamQuery = (id, question, { onWord, onMeta, onDone, onError }) => {
  const controller = new AbortController()

  // Get token from axios default headers (same place axios interceptor sets it)
  const authHeader = axios.defaults.headers.common['Authorization'] || ''
  const token = authHeader.replace('Bearer ', '').trim()

  // Also try common localStorage key names as fallback
  const fallbackToken = localStorage.getItem('rag_token') || ''

  if (!fallbackToken) {
    onError?.('Not authenticated. Please log in again.')
    return () => {}
  }

  fetch(`/api/workspaces/${id}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${fallbackToken}`,
    },
    body: JSON.stringify({ question }),
    signal: controller.signal,
  })
    .then(res => {
      if (res.status === 401) {
        onError?.('Session expired. Please log in again.')
        return
      }
      if (res.status === 400) {
        onError?.('Please upload a file before asking document questions.')
        return
      }
      if (!res.ok) {
        onError?.(`Server error (HTTP ${res.status}). Please try again.`)
        return
      }

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      const pump = () =>
        reader.read().then(({ done, value }) => {
          if (done) { onDone?.(); return }

          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n\n')
          buffer = parts.pop() // keep incomplete last part

          for (const part of parts) {
            if (!part.startsWith('data: ')) continue
            const data = part.slice(6)

            if (data.startsWith('__DONE__')) {
              onDone?.()
              return
            } else if (data.startsWith('__ERROR__')) {
              onError?.(data.slice(9))
              return
            } else if (data.startsWith('__META__')) {
              try {
                onMeta?.(JSON.parse(data.slice(8)))
              } catch { /* ignore malformed meta */ }
            } else {
              // Restore escaped newlines back to real newlines
              const word = data.replace(/\\n/g, '\n')
              onWord?.(word)
            }
          }
          pump()
        })

      pump()
    })
    .catch(err => {
      if (err.name !== 'AbortError') {
        const errorMsg = typeof err === 'string' ? err : (err?.message || 'Connection failed.')
        onError?.(errorMsg)
      }
    })

  return () => controller.abort()
}