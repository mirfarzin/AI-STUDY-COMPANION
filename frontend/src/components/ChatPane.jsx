import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Bot, User, MessageSquare, FileText } from 'lucide-react'
import { sendChat } from '../api'

// ── Citation footer ───────────────────────────────────────────────────────────
function CitationBar({ citations }) {
  if (!citations?.length) return null
  return (
    <div className="mt-2.5 pt-2 border-t border-bg-border/60 space-y-1">
      <p className="text-[10px] font-semibold text-txt-muted uppercase tracking-wider">Source</p>
      {citations.map((c, i) => (
        <div key={i} className="flex items-center gap-2">
          <FileText size={11} className="text-accent-light shrink-0" />
          <span className="text-xs text-txt-secondary font-medium truncate">{c.source}</span>
          <span className="ml-auto flex items-center gap-1.5 shrink-0">
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-border text-txt-muted font-medium">
              {c.type}
            </span>
            <span className="text-[10px] font-semibold text-accent-light">
              {c.similarity}%
            </span>
          </span>
        </div>
      ))}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2.5 animate-fade-in">
      <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
        <Bot size={14} className="text-white" />
      </div>
      <div className="bg-bg-secondary border border-bg-border px-4 py-3 rounded-2xl rounded-bl-sm">
        <div className="flex gap-1 items-center h-4">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  )
}

export default function ChatPane({ activeSubject, subjects, onSelectSubject }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setLoading(true)
    try {
      const res = await sendChat(q, activeSubject)
      setMessages(prev => [...prev, {
        role: 'ai',
        text: res.data.answer,
        citations: res.data.citations || [],
      }])
    } catch (err) {
      const msg = err.response?.data?.detail || 'Something went wrong.'
      setMessages(prev => [...prev, { role: 'ai', text: `❌ ${msg}`, error: true }])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  if (!activeSubject) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-4">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #7c3aed22, #4f46e522)', border: '1px solid #7c3aed44' }}>
          <MessageSquare size={28} className="text-accent-light" />
        </div>
        <div>
          <p className="text-txt-primary font-semibold">No subject selected</p>
          <p className="text-txt-secondary text-sm mt-1">Select a subject to chat.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Doc selector */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-bg-border bg-bg-secondary">
        <span className="text-xs text-txt-muted font-medium">Active subject:</span>
        <select
          value={activeSubject || ''}
          onChange={e => onSelectSubject(e.target.value)}
          className="text-xs bg-bg-card border border-bg-border text-txt-primary rounded-lg px-2 py-1 outline-none focus:border-accent-purple transition-colors"
        >
          {subjects.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-txt-secondary text-sm">Ask anything about your notes 👇</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex items-end gap-2.5 animate-slide-up ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
              msg.role === 'user' ? 'bg-accent-indigo' : ''
            }`} style={msg.role === 'ai' ? { background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' } : {}}>
              {msg.role === 'user'
                ? <User size={14} className="text-white" />
                : <Bot size={14} className="text-white" />
              }
            </div>
            {/* Bubble */}
            <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'rounded-br-sm text-white'
                : 'rounded-bl-sm bg-bg-secondary border border-bg-border text-txt-primary prose-dark'
            } ${msg.error ? 'border-red-500/30 text-red-400' : ''}`}
              style={msg.role === 'user' ? { background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' } : {}}
            >
              {msg.role === 'ai'
                ? (
                  <>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                    <CitationBar citations={msg.citations} />
                  </>
                )
                : msg.text
              }
            </div>
          </div>
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-bg-border bg-bg-secondary">
        <div className="flex items-end gap-3 bg-bg-card border border-bg-border rounded-2xl px-4 py-3 focus-within:border-accent-purple transition-colors">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a question about your notes…"
            className="flex-1 bg-transparent text-sm text-txt-primary placeholder-txt-muted resize-none outline-none max-h-32"
            style={{ lineHeight: '1.5' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2 rounded-xl transition-all disabled:opacity-30 hover:opacity-90 active:scale-95 shrink-0"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
          >
            <Send size={15} className="text-white" />
          </button>
        </div>
        <p className="text-xs text-txt-muted mt-2 text-center">Shift+Enter for new line</p>
      </div>
    </div>
  )
}
