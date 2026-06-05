import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatPane from './components/ChatPane'
import PredictPane from './components/PredictPane'
import PYQPane from './components/PYQPane'
import QuizPane from './components/QuizPane'
import WeakTopicsPane from './components/WeakTopicsPane'
import { fetchSubjects } from './api'
import { MessageSquare, Sparkles, AlertCircle, RefreshCw, BookOpen, Brain } from 'lucide-react'

export default function App() {
  // Listen for weak data from QuizPane
  useEffect(() => {
    const handler = (e) => {
      setWeakData(e.detail.data);
      setView('weak');
    };
    window.addEventListener('weakDataReady', handler);
    return () => window.removeEventListener('weakDataReady', handler);
  }, []);
  const [subjects, setSubjects] = useState([])
  const [activeSubject, setActiveSubject] = useState(null)
  const [view, setView] = useState('chat') // 'chat' | 'predict' | 'pyq' | 'quiz' | 'weak'
  const [showUpload, setShowUpload] = useState(false)
  const [weakData, setWeakData] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const loadSubjects = async () => {
    try {
      setIsLoading(true)
      setLoadError(null)
      const res = await fetchSubjects()
      const subs = res.data.subjects || []
      setSubjects(subs)
      if (subs.length > 0 && !activeSubject) setActiveSubject(subs[0])
    } catch (err) {
      console.error('Failed to load subjects', err)
      setLoadError(err.response?.data?.detail || 'Failed to connect to backend. Ensure the API is running.')
      setSubjects([])
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { loadSubjects() }, [])

  const handleDocDeleted = (docId) => {
    loadSubjects() // reload subjects on delete
  }

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
            <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg bg-bg-card text-accent-light border border-b-0 border-bg-border">
              <MessageSquare size={15} />
              Chat with Notes
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg text-txt-secondary">
              <Sparkles size={15} />
              Predict Questions
            </button>
          </div>
          <div className="flex-1 overflow-hidden bg-bg-card flex items-center justify-center">
            <div className="flex flex-col items-center justify-center gap-6 p-8 max-w-md">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #7c3aed22, #4f46e522)', border: '1px solid #7c3aed44' }}>
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
        onUploadClick={() => setShowUpload(true)}
        onDocDeleted={handleDocDeleted}
      />

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top tab bar */}
        <div className="flex items-center gap-1 px-6 pt-5 pb-0 border-b border-bg-border">
          <button
            onClick={() => setView('chat')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all ${
              view === 'chat'
                ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border'
                : 'text-txt-secondary hover:text-txt-primary'
            }`}
          >
            <MessageSquare size={15} />
            Chat with Notes
          </button>
          <button
            onClick={() => setView('predict')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all ${
              view === 'predict'
                ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border'
                : 'text-txt-secondary hover:text-txt-primary'
            }`}
          >
            <Sparkles size={15} />
            Predict Questions
          </button>
          <button
            onClick={() => setView('pyq')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all ${
              view === 'pyq'
                ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border'
                : 'text-txt-secondary hover:text-txt-primary'
            }`}
          >
            <BookOpen size={15} />
            PYQ Solver
          </button>
          <button
            onClick={() => setView('weak')}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all ${
              view === 'quiz'
                ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border'
                : 'text-txt-secondary hover:text-txt-primary'
            }`}
          >
            <Brain size={15} />
            Weak Topics
          </button>
        </div>

        {/* View content */}
        <div className="flex-1 overflow-hidden bg-bg-card">
          {view === 'chat' && <ChatPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'predict' && <PredictPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'pyq' && <PYQPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'quiz' && <QuizPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />}
          {view === 'weak' && <WeakTopicsPane subject={activeSubject} weakData={weakData} setWeakData={setWeakData} onBack={() => setView('quiz')} />}
        </div>
      </div>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={(docId) => {
            loadSubjects()
            // Could set active subject here if upload returned the subject, but docId is not subject.
            // setActiveSubject(docId)
            setShowUpload(false)
          }}
        />
      )}
    </div>
  )
}
