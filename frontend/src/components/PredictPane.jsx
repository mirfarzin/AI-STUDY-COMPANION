import { useState } from 'react'
import { Sparkles, ChevronDown, ChevronUp, Loader2, BarChart2, Brain } from 'lucide-react'
import { predictQuestions, fetchPYQPredictions } from '../api'

// ─── Shared helpers ──────────────────────────────────────────────────────────

function parseQA(text) {
  const blocks = text.split(/\n(?=Q\d+\.)/i).filter(Boolean)
  return blocks.map((block) => {
    const lines = block.trim().split('\n')
    const question = lines[0].replace(/^Q\d+\.\s*/i, '').trim()
    const answerLines = lines.slice(1).join('\n').replace(/^A:\s*/i, '').trim()
    return { question, answer: answerLines }
  })
}

function LoadingSkeleton({ count = 5 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border border-bg-border rounded-xl px-4 py-3.5 bg-bg-secondary animate-pulse">
          <div className="h-4 bg-bg-border rounded w-3/4" />
        </div>
      ))}
    </div>
  )
}

// ─── AI Predict tab ───────────────────────────────────────────────────────────

function QACard({ item, index, expanded, onToggle }) {
  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${
      expanded ? 'border-accent-purple' : 'border-bg-border hover:border-accent-purple/50'
    }`}>
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left bg-bg-secondary hover:bg-bg-card transition-colors"
      >
        <span className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white mt-0.5"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
          {index + 1}
        </span>
        <span className="flex-1 text-sm font-medium text-txt-primary leading-snug">{item.question}</span>
        {expanded
          ? <ChevronUp size={15} className="shrink-0 text-accent-light mt-0.5" />
          : <ChevronDown size={15} className="shrink-0 text-txt-muted mt-0.5" />
        }
      </button>
      {expanded && (
        <div className="px-4 pb-4 pt-2 bg-bg-card border-t border-bg-border animate-fade-in">
          <p className="text-sm text-txt-secondary leading-relaxed whitespace-pre-wrap">{item.answer}</p>
        </div>
      )}
    </div>
  )
}

function AIPredictTab({ activeSubject, subjects, onSelectSubject }) {
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState({})

  const handlePredict = async () => {
    if (!activeSubject) return
    setLoading(true); setError(''); setQuestions([]); setExpanded({})
    try {
      const res = await predictQuestions(activeSubject)
      setQuestions(parseQA(res.data.questions))
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate questions.')
    } finally { setLoading(false) }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-bg-border bg-bg-secondary">
        <div className="flex items-center gap-3">
          <span className="text-xs text-txt-muted font-medium">Subject:</span>
          <select value={activeSubject || ''} onChange={e => onSelectSubject(e.target.value)}
            className="text-xs bg-bg-card border border-bg-border text-txt-primary rounded-lg px-2 py-1 outline-none focus:border-accent-purple transition-colors">
            {subjects.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <button onClick={handlePredict} disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-60"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {loading ? 'Generating…' : 'Generate with AI'}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-5">
        {!loading && questions.length === 0 && !error && (
          <div className="text-center py-16">
            <div className="text-4xl mb-4">🧠</div>
            <p className="text-txt-primary font-semibold">AI Question Generator</p>
            <p className="text-txt-secondary text-sm mt-2 max-w-xs mx-auto">
              AI reads your notes and predicts 10 likely VTU exam questions with answers.
            </p>
          </div>
        )}
        {loading && <LoadingSkeleton />}
        {error && <p className="text-red-400 text-sm text-center py-10">{error}</p>}
        {!loading && questions.length > 0 && (
          <div className="space-y-2.5 animate-fade-in">
            <p className="text-xs text-txt-muted mb-4">
              {questions.length} questions for <span className="text-accent-light font-medium">{activeSubject}</span>
            </p>
            {questions.map((item, i) => (
              <QACard key={i} item={item} index={i}
                expanded={!!expanded[i]} onToggle={() => setExpanded(p => ({ ...p, [i]: !p[i] }))} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── PYQ Analysis tab ─────────────────────────────────────────────────────────

const PROB_STYLES = {
  High:   { bg: 'bg-green-500/10',  text: 'text-green-400',  border: 'border-green-500/30',  dot: 'bg-green-400' },
  Medium: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', dot: 'bg-yellow-400' },
  Low:    { bg: 'bg-slate-500/10',  text: 'text-slate-400',  border: 'border-slate-500/30',  dot: 'bg-slate-400' },
}

function PYQCard({ item, index, expanded, onToggle }) {
  const s = PROB_STYLES[item.probability] || PROB_STYLES.Low
  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${
      expanded ? `${s.border}` : 'border-bg-border hover:border-accent-purple/40'
    }`}>
      <button onClick={onToggle}
        className="w-full flex items-start gap-3 px-4 py-3.5 text-left bg-bg-secondary hover:bg-bg-card transition-colors">
        {/* Rank badge */}
        <span className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white mt-0.5"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
          {index + 1}
        </span>
        {/* Question text */}
        <span className="flex-1 text-sm font-medium text-txt-primary leading-snug">{item.question}</span>
        {/* Meta pills */}
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${s.bg} ${s.text} ${s.border}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
            {item.probability}
          </span>
          <span className="text-xs text-txt-muted font-medium">×{item.frequency}</span>
        </div>
        {expanded
          ? <ChevronUp size={15} className="shrink-0 text-accent-light mt-0.5" />
          : <ChevronDown size={15} className="shrink-0 text-txt-muted mt-0.5" />
        }
      </button>
      {expanded && (
        <div className="px-4 pb-4 pt-3 bg-bg-card border-t border-bg-border animate-fade-in space-y-2">
          <div className="flex items-center gap-4 text-xs text-txt-secondary">
            <span>Appeared in <strong className="text-txt-primary">{item.frequency}</strong> document{item.frequency > 1 ? 's' : ''}</span>
            <span>|</span>
            <span className="flex items-center gap-1">
              Years:&nbsp;
              {item.years.map(y => (
                <span key={y} className="px-1.5 py-0.5 rounded bg-bg-border text-txt-secondary font-mono text-xs">{y}</span>
              ))}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

function PYQAnalysisTab() {
  const [results, setResults]     = useState([])
  const [summary, setSummary]     = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [expanded, setExpanded]   = useState({})
  const [filter, setFilter]       = useState('All') // All | High | Medium | Low

  const handleAnalyze = async () => {
    setLoading(true); setError(''); setResults([]); setSummary(null); setExpanded({}); setFilter('All')
    try {
      const res = await fetchPYQPredictions()
      setResults(res.data.questions || [])
      setSummary(res.data.summary || {})
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Upload PYQ PDFs first.')
    } finally { setLoading(false) }
  }

  const visible = filter === 'All' ? results : results.filter(r => r.probability === filter)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-bg-border bg-bg-secondary">
        <div className="flex items-center gap-2">
          {summary && ['All', 'High', 'Medium', 'Low'].map(label => {
            const count = label === 'All' ? results.length : (summary[label] ?? 0)
            const active = filter === label
            const s = label === 'All' ? null : PROB_STYLES[label]
            return (
              <button key={label} onClick={() => setFilter(label)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border ${
                  active
                    ? (s ? `${s.bg} ${s.text} ${s.border}` : 'bg-accent-glow text-accent-light border-accent-purple/50')
                    : 'border-bg-border text-txt-muted hover:text-txt-primary hover:border-txt-muted/30'
                }`}>
                {label} {count > 0 && `(${count})`}
              </button>
            )
          })}
        </div>
        <button onClick={handleAnalyze} disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-60"
          style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : <BarChart2 size={14} />}
          {loading ? 'Analyzing…' : 'Analyze PYQs'}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        {!loading && results.length === 0 && !error && (
          <div className="text-center py-16">
            <div className="text-4xl mb-4">📊</div>
            <p className="text-txt-primary font-semibold">PYQ Frequency Analysis</p>
            <p className="text-txt-secondary text-sm mt-2 max-w-sm mx-auto">
              Upload multiple years of PYQ PDFs, then click <strong>"Analyze PYQs"</strong> to find repeated questions ranked by exam probability.
            </p>
            <div className="flex items-center justify-center gap-6 mt-6">
              {[['High', 'text-green-400', '≥3 PDFs'], ['Medium', 'text-yellow-400', '2 PDFs'], ['Low', 'text-slate-400', '1 PDF']].map(([label, cls, hint]) => (
                <div key={label} className="text-center">
                  <p className={`text-xs font-bold ${cls}`}>{label}</p>
                  <p className="text-xs text-txt-muted mt-0.5">{hint}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {loading && <LoadingSkeleton count={7} />}
        {error && <p className="text-red-400 text-sm text-center py-10">{error}</p>}

        {!loading && visible.length > 0 && (
          <div className="space-y-2.5 animate-fade-in">
            <p className="text-xs text-txt-muted mb-4">
              Showing <span className="text-accent-light font-medium">{visible.length}</span> of {results.length} questions · sorted by frequency
            </p>
            {visible.map((item, i) => (
              <PYQCard key={i} item={item} index={i}
                expanded={!!expanded[i]} onToggle={() => setExpanded(p => ({ ...p, [i]: !p[i] }))} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main export ──────────────────────────────────────────────────────────────

export default function PredictPane({ activeSubject, subjects, onSelectSubject }) {
  const [mode, setMode] = useState('pyq') // 'pyq' | 'ai'

  if (!activeSubject && mode === 'ai') {
    return (
      <div className="flex flex-col h-full">
        <ModeBar mode={mode} setMode={setMode} />
        <div className="flex flex-col items-center justify-center flex-1 text-center gap-4">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #7c3aed22, #4f46e522)', border: '1px solid #7c3aed44' }}>
            <Sparkles size={28} className="text-accent-light" />
          </div>
          <div>
            <p className="text-txt-primary font-semibold">No subject selected</p>
            <p className="text-txt-secondary text-sm mt-1">Select a subject to predict exam questions.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ModeBar mode={mode} setMode={setMode} />
      <div className="flex-1 overflow-hidden">
        {mode === 'ai'
          ? <AIPredictTab activeSubject={activeSubject} subjects={subjects} onSelectSubject={onSelectSubject} />
          : <PYQAnalysisTab />
        }
      </div>
    </div>
  )
}

function ModeBar({ mode, setMode }) {
  return (
    <div className="flex items-center gap-1 px-4 pt-3 pb-0 border-b border-bg-border bg-bg-secondary">
      <button onClick={() => setMode('pyq')}
        className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all ${
          mode === 'pyq' ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border' : 'text-txt-secondary hover:text-txt-primary'
        }`}>
        <BarChart2 size={13} /> PYQ Analysis
      </button>
      <button onClick={() => setMode('ai')}
        className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all ${
          mode === 'ai' ? 'bg-bg-card text-accent-light border border-b-0 border-bg-border' : 'text-txt-secondary hover:text-txt-primary'
        }`}>
        <Brain size={13} /> AI Generate
      </button>
    </div>
  )
}
