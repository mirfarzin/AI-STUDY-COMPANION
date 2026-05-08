import { FileText, Trash2, Upload, Brain, BookOpen } from 'lucide-react'
import { deleteSubject } from '../api'

export default function Sidebar({ subjects, activeSubject, onSelectSubject, onUploadClick, onDocDeleted }) {
  const handleDelete = async (e, subject) => {
    e.stopPropagation()
    if (!confirm(`Delete "${subject}"?`)) return
    try {
      await deleteSubject(subject)
      onDocDeleted(subject)
    } catch (err) {
      alert('Failed to delete subject.')
    }
  }

  return (
    <aside className="w-72 flex flex-col border-r border-bg-border bg-bg-secondary shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-bg-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
            <Brain size={18} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-txt-primary text-sm leading-tight">VTU Study</h1>
            <p className="text-xs text-txt-secondary">Companion</p>
          </div>
        </div>
      </div>

      {/* Subjects */}
      <div className="flex-1 overflow-y-auto px-3 py-4">
        <div className="flex items-center gap-2 px-2 mb-3">
          <BookOpen size={13} className="text-txt-muted" />
          <span className="text-xs font-semibold text-txt-muted uppercase tracking-wider">
            Subjects ({subjects.length})
          </span>
        </div>

        {subjects.length === 0 ? (
          <div className="text-center py-10 px-4">
            <div className="w-12 h-12 rounded-full bg-bg-card border border-bg-border flex items-center justify-center mx-auto mb-3">
              <FileText size={20} className="text-txt-muted" />
            </div>
            <p className="text-xs text-txt-secondary">No subjects yet.</p>
            <p className="text-xs text-txt-muted mt-1">Upload a PDF to get started.</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {subjects.map((subj) => (
              <li key={subj}>
                <button
                  onClick={() => onSelectSubject(subj)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all group ${
                    activeSubject === subj
                      ? 'bg-accent-glow border border-accent-purple text-txt-primary'
                      : 'hover:bg-bg-card text-txt-secondary hover:text-txt-primary border border-transparent'
                  }`}
                >
                  <FileText size={14} className={activeSubject === subj ? 'text-accent-light' : 'text-txt-muted'} />
                  <span className="flex-1 text-xs font-medium truncate">{subj}</span>
                  <button
                    onClick={(e) => handleDelete(e, subj)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all"
                    title="Delete subject"
                  >
                    <Trash2 size={12} />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Upload button */}
      <div className="px-4 py-4 border-t border-bg-border">
        <button
          onClick={onUploadClick}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 glow-purple"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
        >
          <Upload size={15} />
          Upload PDF
        </button>
      </div>
    </aside>
  )
}
