import { useState } from 'react'
import { createRuleFromText, createRuleFromFlowchart } from '../../services/api'
import './CreateRuleModal.css'

function CreateRuleModal({ onCreated, onClose }) {
  const [mode, setMode] = useState('text') // 'text' | 'flowchart'
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setError('')
    setLoading(true)
    try {
      if (mode === 'text') {
        if (!text.trim()) {
          setError('Please enter a description of the troubleshooting rule.')
          return
        }
        await createRuleFromText(text.trim())
      } else {
        if (!file) {
          setError('Please select a flowchart image to upload.')
          return
        }
        await createRuleFromFlowchart(file)
      }
      onCreated?.()
      onClose?.()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to create rule')
    } finally {
      setLoading(false)
    }
  }

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    setFile(f || null)
    setError('')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content create-rule-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Troubleshooting Rule</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          <div className="mode-tabs">
            <button
              type="button"
              className={mode === 'text' ? 'active' : ''}
              onClick={() => { setMode('text'); setError('') }}
            >
              Natural Language
            </button>
            <button
              type="button"
              className={mode === 'flowchart' ? 'active' : ''}
              onClick={() => { setMode('flowchart'); setError('') }}
            >
              Upload Flowchart
            </button>
          </div>

          {mode === 'text' ? (
            <>
              <p className="hint">
                Describe the fault scenario and troubleshooting steps in natural language. The AI will extract a structured rule for Agent B.
              </p>
              <textarea
                className="rule-text-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="e.g. When vibration and bearing temperature are elevated, it may indicate bearing wear. Recommend checking lubrication and scheduling a shutdown for inspection."
                rows={6}
              />
            </>
          ) : (
            <>
              <p className="hint">
                Upload a flowchart image (PNG, JPG, WebP). The AI will analyze it and extract troubleshooting rules.
              </p>
              <div className="file-upload">
                <input
                  type="file"
                  id="flowchart-file"
                  accept=".png,.jpg,.jpeg,.webp"
                  onChange={handleFileChange}
                />
                <label htmlFor="flowchart-file" className="file-label">
                  {file ? file.name : 'Choose flowchart image...'}
                </label>
              </div>
            </>
          )}

          {error && <div className="modal-error">{error}</div>}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading || (mode === 'text' ? !text.trim() : !file)}
          >
            {loading ? 'Creating…' : 'Create Rule'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default CreateRuleModal
