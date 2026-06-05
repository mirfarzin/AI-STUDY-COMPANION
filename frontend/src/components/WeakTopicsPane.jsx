import { useState, useEffect } from 'react'
import { Brain, RefreshCw, AlertCircle, X } from 'lucide-react'
import { analyzeWeakTopics } from '../api'

export default function WeakTopicsPane({ subject, weakData, setWeakData, onBack }) {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load from prop or localStorage on mount
  useEffect(() => {
    if (weakData) {
      setTopics(weakData)
    } else if (subject) {
      const stored = localStorage.getItem(`weak_topics_${subject}`)
      if (stored) {
        try {
          setTopics(JSON.parse(stored))
        } catch {}
      }
    }
  }, [weakData, subject])

  const triggerAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      // Retrieve wrong questions history from localStorage
      const wrong = localStorage.getItem(`quiz_history_${subject}`)
      const incorrect_questions = wrong ? JSON.parse(wrong) : []
      const res = await analyzeWeakTopics(subject, incorrect_questions)
      setTopics(res.data)
      setWeakData(res.data)
      localStorage.setItem(`weak_topics_${subject}`, JSON.stringify(res.data))
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to analyze weak topics')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="animate-spin" size={48} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-6 space-y-4">
        <AlertCircle className="text-red-400" size={36} />
        <p className="text-red-400 text-center">{error}</p>
        <button
          onClick={triggerAnalysis}
          className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded"
        >
          <RefreshCw size={16} className="animate-spin" /> Retry
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full p-6 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-txt-primary flex items-center gap-2">
          <Brain className="text-accent-primary" size={20} /> Weak Topics
        </h2>
        <button onClick={onBack} className="text-txt-secondary hover:text-txt-primary">
          ← Back to Quiz
        </button>
      </div>
      {topics && topics.length ? (
        <div className="grid gap-3">
          {topics.map((t, idx) => (
            <details key={idx} className="bg-bg-primary border border-bg-border rounded-lg p-3">
              <summary className="cursor-pointer font-medium text-txt-primary">{t.topic}</summary>
              <p className="mt-2 text-txt-secondary">{t.suggestion || t.advice}</p>
            </details>
          ))}
        </div>
      ) : (
        <div className="text-center text-txt-secondary">
          No weak topics data. Click the button below to analyse.
          <button
            onClick={triggerAnalysis}
            className="mt-4 flex items-center gap-2 px-4 py-2 bg-accent-primary text-white rounded"
          >
            <Brain size={16} /> Analyse Weak Topics
          </button>
        </div>
      )}
    </div>
  )
}
