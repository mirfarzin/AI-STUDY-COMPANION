import axios from 'axios'

// In production (Vercel), use the VITE_API_URL env var pointing to Railway backend.
// In dev, Vite proxy handles it (no baseURL needed), but we fall back to localhost.
axios.defaults.baseURL = import.meta.env.VITE_API_URL || ''

export const uploadPDF = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return axios.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  })
}

export const fetchSubjects = () => axios.get('/subjects')

export const deleteSubject = (subject) => axios.delete(`/subject/${subject}`)

export const sendChat = (query, subject) =>
  axios.post('/chat', { query, subject })

export const predictQuestions = (subject) =>
  axios.post('/predict', { subject })

// Analyzes all uploaded PYQ PDFs for repeated questions
export const fetchPYQPredictions = (threshold = 0.78) =>
  axios.get('/predict-questions', { params: { threshold } })
