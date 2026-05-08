import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatPane from './components/ChatPane'
import PredictPane from './components/PredictPane'
import UploadModal from './components/UploadModal'
import { fetchSubjects } from './api'
import { MessageSquare, Sparkles } from 'lucide-react'

export default function App() {
  const [subjects, setSubjects] = useState([])
  const [activeSubject, setActiveSubject] = useState(null)
  const [view, setView] = useState('chat') // 'chat' | 'predict'
  const [showUpload, setShowUpload] = useState(false)

  const loadSubjects = async () => {
    try {
      const res = await fetchSubjects()
      const subs = res.data.subjects || []
      setSubjects(subs)
      if (subs.length > 0 && !activeSubject) setActiveSubject(subs[0])
    } catch (err) {
      console.error('Failed to load subjects', err)
    }
  }

  useEffect(() => { loadSubjects() }, [])

  const handleDocDeleted = (docId) => {
    loadSubjects() // reload subjects on delete
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
        </div>

        {/* View content */}
        <div className="flex-1 overflow-hidden bg-bg-card">
          {view === 'chat'
            ? <ChatPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />
            : <PredictPane activeSubject={activeSubject} subjects={subjects} onSelectSubject={setActiveSubject} />
          }
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
