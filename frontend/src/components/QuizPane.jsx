import { useState, useEffect } from 'react'
import { Loader2, AlertCircle, CheckCircle, XCircle, RefreshCw, Brain, Trophy } from 'lucide-react'
import { generateQuiz, analyzeWeakTopics } from '../api'

export default function QuizPane({ activeSubject, subjects, onSelectSubject }) {
  const [questions, setQuestions] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [score, setScore] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [wrongQuestions, setWrongQuestions] = useState([])
  const [quizDone, setQuizDone] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  // Load any stored wrong questions for the subject
  useEffect(() => {
    if (activeSubject) {
      const stored = localStorage.getItem(`quiz_history_${activeSubject}`)
      if (stored) {
        try { setWrongQuestions(JSON.parse(stored)) } catch {}
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
    setQuizDone(false)
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

    const newScore = isCorrect ? score + 1 : score
    const newWrong = isCorrect
      ? wrongQuestions
      : [...wrongQuestions, {
          question: q.question,
          user_answer: choice,
          correct_answer: q.correct
        }]

    if (isCorrect) setScore((s) => s + 1)
    else setWrongQuestions(newWrong)

    // Persist wrong questions
    if (!isCorrect) {
      localStorage.setItem(`quiz_history_${activeSubject}`, JSON.stringify(newWrong))
    }

    setTimeout(() => {
      if (currentIdx + 1 < questions.length) {
        setCurrentIdx((i) => i + 1)
        setSelected(null)
      } else {
        setQuizDone(true)
      }
    }, 1200)
  }

  const handleSeeWeak = async () => {
    const wrongList = wrongQuestions.length > 0
      ? wrongQuestions
      : (() => {
          try {
            const stored = localStorage.getItem(`quiz_history_${activeSubject}`)
            return stored ? JSON.parse(stored) : []
          } catch { return [] }
        })()

    if (!wrongList.length) {
      alert('No wrong answers to analyse!')
      return
    }

    setAnalyzing(true)
    try {
      const res = await analyzeWeakTopics(activeSubject, wrongList)
      localStorage.setItem(`weak_topics_${activeSubject}`, JSON.stringify(res.data))
      window.dispatchEvent(new CustomEvent('weakDataReady', { detail: { subject: activeSubject, data: res.data } }))
    } catch (err) {
      console.error(err)
      alert(err.response?.data?.detail || 'Failed to analyze weak topics')
    } finally {
      setAnalyzing(false)
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
        <button onClick={loadQuiz} className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded">
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    )
  }

  if (!questions.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-txt-secondary">No subject selected or no data available.</p>
        {activeSubject && (
          <button onClick={loadQuiz} className="flex items-center gap-2 px-4 py-2 bg-accent-primary text-white rounded">
            <RefreshCw size={16} /> Generate Quiz
          </button>
        )}
      </div>
    )
  }

  // Quiz done screen
  if (quizDone) {
    const finalScore = score
    const hasWrong = wrongQuestions.length > 0

    return (
      <div className="flex flex-col items-center justify-center h-full gap-6 p-6">
        <Trophy className="text-yellow-400" size={56} />
        <div className="text-center">
          <h2 className="text-3xl font-bold text-txt-primary">Quiz Complete!</h2>
          <p className="text-txt-secondary mt-2 text-lg">
            Score: <span className="font-bold text-accent-light">{finalScore}</span> / {questions.length}
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={loadQuiz}
            className="flex items-center gap-2 px-6 py-2.5 bg-bg-secondary border border-bg-border text-txt-primary rounded-lg hover:border-accent-primary transition-colors"
          >
            <RefreshCw size={16} /> Retry Quiz
          </button>
          {hasWrong && (
            <button
              onClick={handleSeeWeak}
              disabled={analyzing}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg text-white disabled:opacity-60"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
            >
              {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Brain size={16} />}
              {analyzing ? 'Analysing...' : 'See Weak Topics'}
            </button>
          )}
        </div>
      </div>
    )
  }

  const q = questions[currentIdx]
  const progress = Math.round(((currentIdx) / questions.length) * 100)

  return (
    <div className="flex flex-col h-full p-6 overflow-y-auto">
      <div className="space-y-3 mb-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-txt-primary">Quiz: {activeSubject}</h2>
          <span className="text-sm text-txt-secondary">
            {currentIdx + 1} / {questions.length}
          </span>
        </div>
        {/* Progress bar */}
        <div className="h-1.5 bg-bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #7c3aed, #4f46e5)' }}
          />
        </div>
      </div>

      <div className="bg-bg-primary border border-bg-border rounded-xl p-5 space-y-5">
        <p className="text-txt-primary font-medium text-base leading-relaxed">{q.question}</p>
        <div className="grid grid-cols-1 gap-3">
          {q.options.map((opt, idx) => {
            const isSelected = selected === opt
            const isCorrect = q.correct === opt
            let bg = 'bg-bg-card hover:bg-bg-secondary'
            let border = 'border-bg-border hover:border-accent-primary/50'
            if (selected) {
              if (isCorrect) { bg = 'bg-green-500/10'; border = 'border-green-500' }
              else if (isSelected) { bg = 'bg-red-500/10'; border = 'border-red-500' }
            }
            return (
              <button
                key={idx}
                onClick={() => handleAnswer(opt)}
                disabled={!!selected}
                className={`flex items-center justify-between p-4 rounded-lg border text-left transition-all ${bg} ${border}`}
              >
                <span className="text-txt-primary text-sm">{opt}</span>
                {selected && isCorrect && <CheckCircle className="text-green-500 shrink-0" size={18} />}
                {selected && !isCorrect && isSelected && <XCircle className="text-red-500 shrink-0" size={18} />}
              </button>
            )
          })}
        </div>
        {selected && q.explanation && (
          <div className="mt-2 p-3 bg-bg-secondary rounded-lg border border-bg-border">
            <p className="text-sm text-txt-secondary"><span className="font-medium text-txt-primary">Explanation: </span>{q.explanation}</p>
          </div>
        )}
      </div>

      {/* Score tally */}
      <div className="mt-4 text-sm text-txt-muted text-center">
        Current score: {score} correct · {wrongQuestions.length} wrong
      </div>
    </div>
  )
}
