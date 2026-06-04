import { useState, useEffect } from 'react'
import { Loader2, CheckCircle2, XCircle, Brain, Target, RefreshCw, ChevronRight } from 'lucide-react'
import { generateQuiz, analyzeWeakTopics } from '../api'

export default function QuizPane({ activeSubject, subjects, onSelectSubject }) {
  const [config, setConfig] = useState({ difficulty: 'medium', topic: '' })
  const [quizState, setQuizState] = useState('config') // config | playing | analyzing | results
  
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedOption, setSelectedOption] = useState(null)
  const [isAnswerRevealed, setIsAnswerRevealed] = useState(false)
  
  const [score, setScore] = useState(0)
  const [missedQuestions, setMissedQuestions] = useState([])
  const [weakTopics, setWeakTopics] = useState([])
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load persisted weak topics from localStorage
  useEffect(() => {
    if (activeSubject && quizState === 'config') {
      try {
        const stored = localStorage.getItem(`weak_topics_${activeSubject}`)
        if (stored) setWeakTopics(JSON.parse(stored))
        else setWeakTopics([])
      } catch (e) {
        console.error("Local storage read error", e)
      }
    }
  }, [activeSubject, quizState])

  const startQuiz = async () => {
    if (!activeSubject) {
      setError("Please select a subject first.")
      return
    }
    
    setIsLoading(true)
    setError(null)
    
    try {
      const res = await generateQuiz(activeSubject, config.difficulty, config.topic)
      setQuestions(res.data)
      setCurrentIndex(0)
      setScore(0)
      setMissedQuestions([])
      setSelectedOption(null)
      setIsAnswerRevealed(false)
      setQuizState('playing')
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to generate quiz. Note: AI might take a moment to respond.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectOption = (opt) => {
    if (isAnswerRevealed) return
    setSelectedOption(opt)
  }

  const handleConfirmAnswer = () => {
    if (!selectedOption) return
    
    setIsAnswerRevealed(true)
    const currentQ = questions[currentIndex]
    
    // Check if correct (assuming option starts with A) B) etc matching correct)
    // We check if the selected option string starts with the correct letter, or equals it
    const isCorrect = selectedOption.startsWith(currentQ.correct) || 
                      selectedOption.includes(` ${currentQ.correct})`) ||
                      selectedOption === currentQ.correct
                      
    if (isCorrect) {
      setScore(s => s + 1)
    } else {
      setMissedQuestions(prev => [...prev, {
        question: currentQ.question,
        user_answer: selectedOption,
        correct_answer: currentQ.options.find(o => o.startsWith(currentQ.correct) || o === currentQ.correct) || currentQ.correct
      }])
    }
  }

  const handleNextQuestion = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(i => i + 1)
      setSelectedOption(null)
      setIsAnswerRevealed(false)
    } else {
      finishQuiz()
    }
  }

  const finishQuiz = async () => {
    if (missedQuestions.length > 0) {
      setQuizState('analyzing')
      try {
        const res = await analyzeWeakTopics(activeSubject, missedQuestions)
        const analysis = res.data
        setWeakTopics(analysis)
        try {
          localStorage.setItem(`weak_topics_${activeSubject}`, JSON.stringify(analysis))
        } catch(e) {}
      } catch (err) {
        console.error('Failed to analyze weak topics', err)
      }
    }
    setQuizState('results')
  }

  const resetQuiz = () => {
    setQuizState('config')
    setQuestions([])
    setConfig({ ...config, topic: '' })
  }

  return (
    <div className="flex flex-col h-full bg-bg-card p-6 overflow-y-auto">
      <div className="max-w-3xl mx-auto w-full space-y-8 pb-12">
        
        {/* Header */}
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-txt-primary flex items-center gap-2">
            <Brain className="text-accent-primary" />
            Quiz Me
          </h2>
          <p className="text-txt-secondary text-sm">
            Generate smart multiple-choice questions from your notes to test your knowledge and identify weak areas.
          </p>
        </div>

        {/* --- STATE: CONFIG --- */}
        {quizState === 'config' && (
          <div className="space-y-8 animate-fade-in">
            <div className="bg-bg-primary border border-bg-border rounded-xl p-5 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-txt-secondary uppercase tracking-wider">Subject</label>
                  <select 
                    value={activeSubject || ''} 
                    onChange={(e) => onSelectSubject(e.target.value)}
                    className="w-full bg-bg-card border border-bg-border rounded-lg px-3 py-2.5 text-sm text-txt-primary outline-none focus:border-accent-primary"
                  >
                    {!activeSubject && <option value="">Select a subject...</option>}
                    {subjects.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-txt-secondary uppercase tracking-wider">Difficulty</label>
                  <select 
                    value={config.difficulty} 
                    onChange={(e) => setConfig({...config, difficulty: e.target.value})}
                    className="w-full bg-bg-card border border-bg-border rounded-lg px-3 py-2.5 text-sm text-txt-primary outline-none focus:border-accent-primary"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>
              
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-txt-secondary uppercase tracking-wider">Specific Topic (Optional)</label>
                <input
                  type="text"
                  value={config.topic}
                  onChange={(e) => setConfig({...config, topic: e.target.value})}
                  placeholder="e.g., Virtual Memory, Linked Lists, Kinematics..."
                  className="w-full bg-bg-card border border-bg-border rounded-lg px-3 py-2.5 text-sm text-txt-primary outline-none focus:border-accent-primary"
                />
              </div>

              {error && <div className="text-red-400 text-sm mt-2">{error}</div>}

              <div className="flex justify-end pt-2">
                <button
                  onClick={startQuiz}
                  disabled={isLoading || !activeSubject}
                  className="flex items-center gap-2 px-8 py-3 rounded-lg text-sm font-bold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
                >
                  {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Brain size={18} />}
                  {isLoading ? 'Generating Quiz...' : 'Start Quiz'}
                </button>
              </div>
            </div>

            {/* Weak Areas Display */}
            {weakTopics.length > 0 && (
              <div className="bg-bg-primary border border-bg-border rounded-xl p-5 space-y-4">
                <h3 className="text-lg font-bold text-txt-primary flex items-center gap-2">
                  <Target className="text-red-400" />
                  Your Weak Areas in {activeSubject}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {weakTopics.map((topic, i) => (
                    <div key={i} className="bg-bg-card border border-bg-border rounded-lg p-4 space-y-2">
                      <div className="flex justify-between items-start">
                        <h4 className="font-semibold text-accent-light text-sm">{topic.topic}</h4>
                        <span className="text-[10px] bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-bold">
                          Missed {topic.question_count}
                        </span>
                      </div>
                      <p className="text-xs text-txt-secondary leading-relaxed">
                        {topic.suggestion}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- STATE: PLAYING --- */}
        {quizState === 'playing' && questions.length > 0 && (
          <div className="animate-fade-in space-y-6">
            <div className="flex justify-between items-center text-sm font-semibold text-txt-secondary">
              <span>Question {currentIndex + 1} of {questions.length}</span>
              <span className="text-accent-light">Score: {score}</span>
            </div>
            
            <div className="bg-bg-primary border border-bg-border rounded-xl overflow-hidden">
              <div className="p-6 border-b border-bg-border bg-bg-card">
                <h3 className="text-lg font-medium text-txt-primary leading-relaxed">
                  {questions[currentIndex].question}
                </h3>
              </div>
              
              <div className="p-6 space-y-3 bg-bg-primary">
                {questions[currentIndex].options.map((opt, i) => {
                  const isCorrectAnswer = opt.startsWith(questions[currentIndex].correct) || opt === questions[currentIndex].correct;
                  const isSelected = selectedOption === opt;
                  
                  let optStyle = "border-bg-border bg-bg-card text-txt-secondary hover:border-accent-primary/50 hover:bg-accent-primary/5";
                  
                  if (isAnswerRevealed) {
                    if (isCorrectAnswer) {
                      optStyle = "border-green-500/50 bg-green-500/10 text-green-400 ring-1 ring-green-500/50"
                    } else if (isSelected) {
                      optStyle = "border-red-500/50 bg-red-500/10 text-red-400"
                    } else {
                      optStyle = "border-bg-border bg-bg-card opacity-50 text-txt-muted"
                    }
                  } else if (isSelected) {
                    optStyle = "border-accent-primary ring-1 ring-accent-primary bg-accent-primary/10 text-accent-light"
                  }

                  return (
                    <button
                      key={i}
                      onClick={() => handleSelectOption(opt)}
                      disabled={isAnswerRevealed}
                      className={`w-full text-left p-4 rounded-xl border text-sm transition-all duration-200 flex justify-between items-center ${optStyle}`}
                    >
                      <span>{opt}</span>
                      {isAnswerRevealed && isCorrectAnswer && <CheckCircle2 size={18} className="text-green-400" />}
                      {isAnswerRevealed && isSelected && !isCorrectAnswer && <XCircle size={18} className="text-red-400" />}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Explanation & Controls */}
            {isAnswerRevealed && (
              <div className="animate-slide-up space-y-6">
                <div className="bg-bg-card border border-bg-border rounded-xl p-5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-txt-secondary mb-2">Explanation</h4>
                  <p className="text-sm text-txt-primary leading-relaxed">
                    {questions[currentIndex].explanation}
                  </p>
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={handleNextQuestion}
                    className="flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold bg-white text-black transition-all hover:bg-gray-200 active:scale-95"
                  >
                    {currentIndex < questions.length - 1 ? 'Next Question' : 'Finish Quiz'}
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            )}
            
            {!isAnswerRevealed && (
              <div className="flex justify-end">
                <button
                  onClick={handleConfirmAnswer}
                  disabled={!selectedOption}
                  className="flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-bold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
                >
                  Check Answer
                </button>
              </div>
            )}
          </div>
        )}

        {/* --- STATE: ANALYZING / RESULTS --- */}
        {(quizState === 'analyzing' || quizState === 'results') && (
          <div className="animate-fade-in space-y-8">
            <div className="bg-bg-primary border border-bg-border rounded-2xl p-8 text-center space-y-6">
              <div className="w-24 h-24 mx-auto rounded-full flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c3aed22, #4f46e522)', border: '2px solid #7c3aed44' }}>
                <span className="text-3xl font-bold text-accent-light">{score}/{questions.length}</span>
              </div>
              <div>
                <h3 className="text-2xl font-bold text-txt-primary">Quiz Completed!</h3>
                <p className="text-txt-secondary mt-2">
                  {score === questions.length ? "Perfect score! You're ready for the exam." : "Great effort! Review your weak areas below."}
                </p>
              </div>
              <button
                onClick={resetQuiz}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95"
                style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
              >
                <RefreshCw size={16} /> Take Another Quiz
              </button>
            </div>

            {quizState === 'analyzing' && (
              <div className="flex flex-col items-center justify-center p-8 text-txt-secondary gap-3">
                <Loader2 size={24} className="animate-spin text-accent-primary" />
                <p className="text-sm">Analyzing your missed questions...</p>
              </div>
            )}

            {quizState === 'results' && weakTopics.length > 0 && (
               <div className="bg-bg-primary border border-bg-border rounded-xl p-6 space-y-5">
                 <h3 className="text-lg font-bold text-txt-primary flex items-center gap-2">
                   <Target className="text-red-400" />
                   AI Weakness Analysis
                 </h3>
                 <p className="text-sm text-txt-secondary">Based on the questions you missed, here are areas you should focus on:</p>
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                   {weakTopics.map((topic, i) => (
                     <div key={i} className="bg-bg-card border border-bg-border rounded-lg p-5 space-y-3">
                       <div className="flex justify-between items-start">
                         <h4 className="font-bold text-accent-light">{topic.topic}</h4>
                         <span className="text-[10px] bg-red-500/20 text-red-400 px-2 py-1 rounded-full font-bold">
                           Missed {topic.question_count}
                         </span>
                       </div>
                       <p className="text-sm text-txt-primary leading-relaxed">
                         {topic.suggestion}
                       </p>
                     </div>
                   ))}
                 </div>
               </div>
            )}
          </div>
        )}
        
      </div>
    </div>
  )
}
