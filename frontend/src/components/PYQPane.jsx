import { useState } from 'react'
import { Search, Loader2, BookOpen, AlertCircle, FileText, Sparkles } from 'lucide-react'
import { solvePYQ } from '../api'

export default function PYQPane({ activeSubject, subjects, onSelectSubject }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSolve = async () => {
    if (!question.trim()) return
    setIsLoading(true)
    setError(null)
    setResult(null)
    
    try {
      const res = await solvePYQ(question, activeSubject)
      setResult(res.data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to solve PYQ')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-bg-card p-6 overflow-y-auto">
      <div className="max-w-4xl mx-auto w-full space-y-8">
        
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-txt-primary flex items-center gap-2">
            <BookOpen className="text-accent-primary" />
            PYQ Solver
          </h2>
          <p className="text-txt-secondary text-sm">
            Paste a Previous Year Question (PYQ) here. The AI will use your notes to generate a comprehensive answer and cite exactly where it found the information.
          </p>
        </div>

        {/* Input Section */}
        <div className="bg-bg-primary border border-bg-border rounded-xl p-4 space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 space-y-1">
              <label className="text-xs font-semibold text-txt-secondary uppercase tracking-wider">Subject Filter</label>
              <select 
                value={activeSubject || ''} 
                onChange={(e) => onSelectSubject(e.target.value)}
                className="w-full bg-bg-card border border-bg-border rounded-lg px-3 py-2.5 text-sm text-txt-primary outline-none focus:border-accent-primary"
              >
                <option value="">All Subjects (Global Search)</option>
                {subjects.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="space-y-1">
            <label className="text-xs font-semibold text-txt-secondary uppercase tracking-wider">Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g., Explain the architecture of a 8086 microprocessor with a neat diagram."
              className="w-full h-32 bg-bg-card border border-bg-border rounded-lg p-3 text-sm text-txt-primary outline-none focus:border-accent-primary resize-none"
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleSolve}
              disabled={isLoading || !question.trim()}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
            >
              {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
              {isLoading ? 'Solving...' : 'Solve Question'}
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-start gap-3">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <div className="text-sm">{error}</div>
          </div>
        )}

        {/* Result Section */}
        {result && (
          <div className="space-y-6 animate-fade-in pb-12">
            
            {/* Answer Card */}
            <div className="bg-bg-primary border border-bg-border rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b border-bg-border bg-bg-card flex justify-between items-center">
                <h3 className="font-semibold text-txt-primary flex items-center gap-2">
                  <Sparkles size={16} className="text-yellow-400" />
                  AI Generated Answer
                </h3>
                <span className={`text-xs px-2 py-1 rounded-md font-medium ${
                  result.confidence === 'High' ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
                }`}>
                  {result.confidence} Confidence
                </span>
              </div>
              <div className="p-5 text-txt-primary text-sm leading-relaxed whitespace-pre-wrap">
                {result.answer}
              </div>
            </div>

            {/* Citations Card */}
            {result.sources && result.sources.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-txt-secondary uppercase tracking-wider pl-1 flex items-center gap-2">
                  <FileText size={14} />
                  Sources & Citations
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.sources.map((source, idx) => (
                    <div key={idx} className="bg-bg-primary border border-bg-border p-4 rounded-xl flex flex-col gap-2 hover:border-accent-primary/50 transition-colors">
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-semibold text-accent-light truncate pr-2">
                          {source.filename}
                        </span>
                        <span className="text-[10px] bg-bg-card border border-bg-border px-1.5 py-0.5 rounded text-txt-muted whitespace-nowrap">
                          {source.subject}
                        </span>
                      </div>
                      <p className="text-xs text-txt-secondary italic line-clamp-3">
                        "{source.excerpt.trim()}"
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
