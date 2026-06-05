import { useState, useEffect } from 'react'
import { Loader2, AlertCircle, CheckCircle, XCircle, RefreshCw, Brain } from 'lucide-react'
import { generateQuiz, analyzeWeakTopics } from '../api'

export default function QuizPane({ activeSubject, subjects, onSelectSubject }) {
  const [questions, setQuestions] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [score, setScore] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [wrongQuestions, setWrongQuestions] = useState([])
  const [showWeakBtn, setShowWeakBtn] = useState(false)

  // Load any stored wrong questions for the subject
  useEffect(() => {
    if (activeSubject) {
      const stored = localStorage.getItem(`quiz_history_${activeSubject}`)
      if (stored) {
        try {
          setWrongQuestions(JSON.parse(stored))
        } catch {}
      }
    }
  }, [activeSubject])

  const loadQuiz = async () => {
    setIsLoading(true)
    setError(null)
    setQuestions([])
    setCurrentIdx(0)
    setScore(0)
    setSelected(null)
    setWrongQuestions([])
    setShowWeakBtn(false)
    try {
      const res = await generateQuiz(activeSubject, 'medium')
      setQuestions(res.data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to generate quiz')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (activeSubject) loadQuiz()
  }, [activeSubject])

  const handleAnswer = (choice) => {
    if (selected) return
    const q = questions[currentIdx]
    const isCorrect = choice === q.correct
    setSelected(choice)
    if (isCorrect) setScore((s) => s + 1)
    else setWrongQuestions((arr) => [...arr, { question: q.question, selected: choice, correct: q.correct }])
    // Persist wrong questions
    const storageKey = `quiz_history_${activeSubject}`
    const updated = isCorrect ? wrongQuestions : [...wrongQuestions, { question: q.question, selected: choice, correct: q.correct }]
    localStorage.setItem(storageKey, JSON.stringify(updated))
    // Move to next after short delay
    setTimeout(() => {
      if (currentIdx + 1 < questions.length) {
        setCurrentIdx((i) => i + 1)
        setSelected(null)
      } else {
        // Quiz done
        setShowWeakBtn(wrongQuestions.length > 0)
      }
    }, 1200)
  }

  const handleSeeWeak = async () => {
    try {
      const res = await analyzeWeakTopics(activeSubject, wrongQuestions)
      localStorage.setItem(`weak_topics_${activeSubject}`, JSON.stringify(res.data))
      const event = new CustomEvent('weakDataReady', { detail: { subject: activeSubject, data: res.data } })
      window.dispatchEvent(event)
    } catch (err) {
      console.error(err)
      alert('Failed to analyze weak topics')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent-primary" size={48} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-6 space-y-4">
        <AlertCircle className="text-red-400" size={36} />
        <p className="text-red-400 text-center">{error}</p>
        <button
          onClick={loadQuiz}
          className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded"
        >
          <RefreshCw size={16} className="animate-spin" /> Retry
        </button>
      </div>
    )
  }

  if (!questions.length) {
    return <div className="text-center text-txt-secondary mt-8">No quiz data available.</div>
  }

  const q = questions[currentIdx]

  return (
    <div className="flex flex-col h-full p-6 overflow-y-auto">
      <div className="space-y-4 mb-4">
        <h2 className="text-xl font-bold text-txt-primary">Quiz: {activeSubject}</h2>
        <p className="text-txt-secondary">Question {currentIdx + 1} of {questions.length}</p>
      </div>
      <div className="bg-bg-primary border border-bg-border rounded-lg p-4 space-y-4">
        <p className="text-txt-primary font-medium">{q.question}</p>
        <div className="grid grid-cols-1 gap-3">
          {q.options.map((opt, idx) => {
            const isSelected = selected === opt
            const isCorrect = q.correct === opt
            const bg = selected ? (isCorrect ? 'bg-green-500/10' : 'bg-red-500/10') : 'bg-bg-card'
            const border = selected ? (isCorrect ? 'border-green-500' : 'border-red-500') : 'border-bg-border'
            return (
              <button
                key={idx}
                onClick={() => handleAnswer(opt)}
                disabled={!!selected}
                className={`flex items-center justify-between p-3 rounded border ${bg} ${border} text-left`}
              >
                <span className="text-txt-primary">{opt}</span>
                {selected && isCorrect && <CheckCircle className="text-green-500" size={18} />}
                {selected && !isCorrect && isSelected && <XCircle className="text-red-500" size={18} />}
              </button>
            )
          })}
        </div>
        {selected && (
          <div className="mt-2 text-sm text-txt-secondary">
            <p>{q.explanation}</p>
          </div>
        )}
      </div>

      {/* Final screen */}
      {showWeakBtn && currentIdx + 1 >= questions.length && (
        <div className="mt-6 flex flex-col items-center space-y-4">
          <h3 className="text-2xl font-bold text-txt-primary">Score: {score} / {questions.length}</h3>
          <button
            onClick={loadQuiz}
            className="flex items-center gap-2 px-6 py-2 bg-accent-primary text-white rounded"
          >
            <RefreshCw size={16} /> Retry Quiz
          </button>
          <button
            onClick={handleSeeWeak}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded"
          >
            <Brain size={16} /> See Weak Topics
          </button>
        </div>
      )}
    </div>
  )
}
