import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatPane from './components/ChatPane'
import PredictPane from './components/PredictPane'
import PYQPane from './components/PYQPane'
import QuizPane from './components/QuizPane'
import WeakTopicsPane from './components/WeakTopicsPane'
import { fetchSubjects } from './api'
import { MessageSquare, Sparkles, AlertCircle, RefreshCw, BookOpen, Brain, ClipboardList } from 'lucide-react'

export default function App() {
  const [subjects, setSubjects] = useState([])
  const [activeSubject, setActiveSubject] = useState(null)
  const [view, setView] = useState('chat') // 'chat' | 'predict' | 'pyq' | 'quiz' | 'weak'
  const [weakData, setWeakData] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  // Listen for weak data dispatched from QuizPane after quiz completion
  useEffect(() => {
    const handler = (e) => {
      setWeakData(e.detail.data)
      setView('weak')
    }
    window.addEventListener('weakDataReady', handler)
    return () => window.removeEventListener('weakDataReady', handler)
  }, [])

  const loadSubjects = async () => {
    try {
      setIsLoading(true)
      setLoadError(null)
      const res = await fetchSubjects()
      const subs = res.data.subjects || []
      setSubjects(subs)
      if (subs.length > 0) setActiveSubject((prev) => prev || subs[0])
    } catch (err) {
      console.error('Failed to load subjects', err)
      setLoadError(err.response?.data?.detail || 'Failed to connect to backend. Ensure the API is running.')
      setSubjects([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { loadSubjects() }, [])

  const handleDocDeleted = () => {
    loadSubjects()
  }

  const tabs = [
    { id: 'chat',    label: 'Chat with Notes',  icon: <MessageSquare size={15} /> },
    { id: 'predict', label: 'Predict Questions', icon: <Sparkles size={15} /> },
    { id: 'pyq',     label: 'PYQ Solver',        icon: <BookOpen size={15} /> },
    { id: 'quiz',    label: 'Quiz Me',            icon: <ClipboardList size={15} /> },
    { id: 'weak',    label: 'Weak Topics',        icon: <Brain size={15} /> },
  ]

  // Show error state if backend is not accessible
  if (loadError && subjects.length === 0) {
    return (
      <div className="flex h-screen overflow-hidden bg-bg-primary">
        <Sidebar
          subjects={[]}
          activeSubject={null}
          onSelectSubject={() => {}}
          onUploadClick={() => {}}
          onDocDeleted={() => {}}
        />
        <div className="flex flex-col flex-1 overflow-hidden">
          <div className="flex items-center gap-1 px-6 pt-5 pb-0 border-b border-bg-border">
            {tabs.slice(0, 2).map((t) => (
              <button key={t.id} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg text-txt-secondary">
                {t.icon}{t.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-hidden bg-bg-card flex items-center justify-center">
            <div className="flex flex-col items-center justify-center gap-6 p-8 max-w-md">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: 'linear-gradient(135deg, #7c3aed22, #4f46e522)', border: '1px solid #7c3aed44' }}>
                <AlertCircle size={32} className="text-red-400" />
              </div>
              <div className="text-center">
                <p className="text-txt-primary font-semibold text-lg mb-2">Backend Connection Error</p>
                <p className="text-txt-secondary text-sm mb-4">{loadError}</p>
                <p className="text-txt-muted text-xs mb-6">Check that the backend URL is correct and the server is running.</p>
              </div>
              <button
                onClick={loadSubjects}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-60"
                style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
              >
                {isLoading ? <RefreshCw size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                {isLoading ? 'Retrying...' : 'Retry'}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      <Sidebar
        subjects={subjects}
        activeSubject={activeSubject}
        onSelectSubject={setActiveSubject}
        onUploadClick={() => {}}
        onDocDeleted={handleDocDeleted}
      />

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top tab bar */}
        <div className="flex items-center gap-1 px-6 pt-5 pb-0 border-b border-bg-border overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setView(t.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all whitespace-nowrap ${
                view === t.id
                  ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border'
                  : 'text-txt-secondary hover:text-txt-primary'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* View content */}
        <div className="flex-1 overflow-hidden bg-bg-card">
          {view === 'chat'    && <ChatPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'predict' && <PredictPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'pyq'     && <PYQPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'quiz'    && <QuizPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'weak'    && <WeakTopicsPane subject={activeSubject} weakData={weakData} setWeakData={setWeakData} onBack={() => setView('quiz')} />}
        </div>
      </div>
    </div>
  )
}
