import axios from 'axios'

// Get API base URL from environment or use same-origin relative path for Vercel
const API_BASE = import.meta.env.VITE_API_URL || ''

// Create axios instance with timeout and headers
const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
      url: error.config?.url
    })
    return Promise.reject(error)
  }
)

export default api
export { API_BASE }

// API methods
export const uploadPDF = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/api/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  })
}

export const fetchSubjects = () => api.get('/api/subjects')

export const deleteSubject = (subject) => api.delete(`/api/subject/${subject}`)

export const sendChat = (query, subject) =>
  api.post('/api/chat', { query, subject })

export const predictQuestions = (subject) =>
  api.post('/api/predict', { subject })

export const fetchPYQPredictions = (threshold = 0.78) =>
  api.get('/api/predict-questions', { params: { threshold } })

export const solvePYQ = (question, subject) =>
  api.post('/api/pyq', { question, subject })

export const generateQuiz = (subject, difficulty = "medium", topic = null) =>
  api.get('/api/quiz', { params: { subject, difficulty, topic } })

export const analyzeWeakTopics = (subject, incorrect_questions) =>
  api.post('/api/weak-topics', { subject, incorrect_questions })

