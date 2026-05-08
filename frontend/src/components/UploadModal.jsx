import { useState, useCallback } from 'react'
import { X, Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { uploadPDF } from '../api'

export default function UploadModal({ onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle | uploading | success | error
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const handleFile = (f) => {
    if (!f?.name.toLowerCase().endsWith('.pdf')) {
      setMessage('Please select a PDF file.')
      return
    }
    setFile(f)
    setMessage('')
    setStatus('idle')
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')
    setProgress(0)
    try {
      const res = await uploadPDF(file, setProgress)
      setStatus('success')
      setMessage(`✅ Ingested ${res.data.chunks} chunks from "${res.data.filename}"`)
      setTimeout(() => onUploaded(res.data.doc_id), 1200)
    } catch (err) {
      setStatus('error')
      setMessage(err.response?.data?.detail || 'Upload failed. Please try again.')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(6px)' }}>
      <div className="w-full max-w-md bg-bg-card border border-bg-border rounded-2xl shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-bg-border">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>
              <Upload size={13} className="text-white" />
            </div>
            <h2 className="text-sm font-semibold text-txt-primary">Upload PDF Notes</h2>
          </div>
          <button onClick={onClose} className="text-txt-muted hover:text-txt-primary transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          {/* Drop zone */}
          <div
            onDrop={onDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => document.getElementById('pdf-input').click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? 'border-accent-purple bg-accent-glow'
                : 'border-bg-border hover:border-accent-purple/60 hover:bg-bg-secondary'
            }`}
          >
            <input id="pdf-input" type="file" accept=".pdf" className="hidden"
              onChange={e => handleFile(e.target.files[0])} />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText size={20} className="text-accent-light" />
                <div className="text-left">
                  <p className="text-sm font-medium text-txt-primary truncate max-w-[200px]">{file.name}</p>
                  <p className="text-xs text-txt-muted">{(file.size / 1024).toFixed(0)} KB</p>
                </div>
              </div>
            ) : (
              <div>
                <Upload size={28} className="text-txt-muted mx-auto mb-3" />
                <p className="text-sm text-txt-secondary">Drop your PDF here or <span className="text-accent-light font-medium">browse</span></p>
                <p className="text-xs text-txt-muted mt-1">PDF files only</p>
              </div>
            )}
          </div>

          {/* Progress bar */}
          {status === 'uploading' && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-txt-muted">
                <span>Uploading & processing…</span>
                <span>{progress}%</span>
              </div>
              <div className="h-1.5 bg-bg-border rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #7c3aed, #4f46e5)' }} />
              </div>
            </div>
          )}

          {/* Message */}
          {message && (
            <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${
              status === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
            }`}>
              {status === 'success'
                ? <CheckCircle size={13} />
                : <AlertCircle size={13} />
              }
              {message}
            </div>
          )}

          {/* Upload button */}
          <button
            onClick={handleUpload}
            disabled={!file || status === 'uploading' || status === 'success'}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-40"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}
          >
            {status === 'uploading'
              ? <><Loader2 size={15} className="animate-spin" /> Processing…</>
              : status === 'success'
              ? <><CheckCircle size={15} /> Done!</>
              : <><Upload size={15} /> Upload & Ingest PDF</>
            }
          </button>
        </div>
      </div>
    </div>
  )
}
