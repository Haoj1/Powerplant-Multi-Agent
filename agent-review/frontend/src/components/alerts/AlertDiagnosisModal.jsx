import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getAlertDetail, chatAskStream, generateDiagnosisForAlert, createDiagnosisForAlert, addDiagnosisToReviewQueue } from '../../services/api'
import './AlertDiagnosisModal.css'

function AlertDiagnosisModal({ alertId, onClose, onDiagnosisCreated }) {
  const [alert, setAlert] = useState(null)
  const [diagnosis, setDiagnosis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [modalMessages, setModalMessages] = useState([])
  const [input, setInput] = useState('')
  const [streamingSteps, setStreamingSteps] = useState([])
  const [streamingMessage, setStreamingMessage] = useState(null)
  const [pendingUserMessage, setPendingUserMessage] = useState(null)
  const [lastAssistantAnswer, setLastAssistantAnswer] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [inReviewQueue, setInReviewQueue] = useState(false)
  const [addingToReview, setAddingToReview] = useState(false)
  const [generating, setGenerating] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (!alertId) return
    setLoading(true)
    getAlertDetail(alertId)
      .then(({ alert: a, diagnosis: d, in_review_queue }) => {
        setAlert(a)
        setDiagnosis(d)
        setInReviewQueue(!!in_review_queue)
      })
      .catch((e) => setError(e?.message || 'Failed to load alert'))
      .finally(() => setLoading(false))
  }, [alertId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [modalMessages, streamingMessage, streamingSteps, pendingUserMessage])

  const sendMessage = async (question) => {
    if (!question?.trim() || pendingUserMessage != null) return
    setError('')
    setStreamingSteps([])
    setStreamingMessage(null)
    setPendingUserMessage(question)
    const history = modalMessages.map((m) => ({ role: m.role, content: m.content || '' }))

    try {
      await chatAskStream(
        question,
        null,
        history,
        (event) => {
          if (event.type === 'step') setStreamingSteps((prev) => [...prev, event.step || {}])
          if (event.type === 'result') {
            const answer = event.answer ?? ''
            setLastAssistantAnswer(answer)
            const displayContent = answer.trim()
              ? answer
              : 'No diagnosis text was generated. The agent may have hit a limit or returned empty. Try again or ask a shorter question.'
            setModalMessages((prev) => [
              ...prev,
              { role: 'user', content: question },
              { role: 'assistant', content: displayContent },
            ])
            setStreamingMessage(null)
            setStreamingSteps([])
            setPendingUserMessage(null)
          }
          if (event.type === 'error') setError(event.error || 'Unknown error')
        },
        { alertId, mode: 'diagnosis_assistant' }
      )
      setStreamingMessage(null)
      setStreamingSteps([])
      setPendingUserMessage(null)
    } catch (e) {
      setError(e?.message || 'Send failed')
      setStreamingMessage(null)
      setStreamingSteps([])
      setPendingUserMessage(null)
    }
  }

  const handleSend = () => {
    const q = input.trim()
    setInput('')
    sendMessage(q)
  }

  const handleQuickGenerate = async () => {
    if (generating || pendingUserMessage != null) return
    setGenerating(true)
    setError('')
    setStreamingSteps([])
    setStreamingMessage(null)
    const question = diagnosis ? 'Regenerate diagnosis' : 'Generate diagnosis'
    setPendingUserMessage(question)
    try {
      const text = await generateDiagnosisForAlert(alertId)
      setLastAssistantAnswer(text || '')
      const displayContent = (text || '').trim()
        ? text
        : 'No diagnosis was generated. Check backend logs.'
      setModalMessages((prev) => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: displayContent },
      ])
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Generate failed')
      setModalMessages((prev) => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: `Error: ${e?.message || 'Generate failed'}` },
      ])
    } finally {
      setGenerating(false)
      setPendingUserMessage(null)
    }
  }

  const handleSaveAsDiagnosis = async () => {
    const text = streamingMessage || lastAssistantAnswer
    if (!text?.trim()) return
    setSaving(true)
    setError('')
    try {
      const { diagnosis_id } = await createDiagnosisForAlert(alertId, {
        root_cause: text.trim(),
        confidence: 0.9,
        impact: '',
        recommended_actions: [],
      })
      setDiagnosis({ id: diagnosis_id, root_cause: text.trim(), confidence: 0.9, impact: '', recommended_actions: [] })
      setInReviewQueue(false)
      if (onDiagnosisCreated) onDiagnosisCreated()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleAddToReviewQueue = async () => {
    if (!diagnosis?.id || inReviewQueue || addingToReview) return
    setAddingToReview(true)
    setError('')
    try {
      await addDiagnosisToReviewQueue(diagnosis.id)
      setInReviewQueue(true)
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Add to queue failed')
    } finally {
      setAddingToReview(false)
    }
  }

  const displayAnswer = streamingMessage ?? lastAssistantAnswer
  const canSave = displayAnswer?.trim() && !saving
  const canAddToReview = diagnosis?.id && !inReviewQueue && !addingToReview

  if (!alertId) return null
  return (
    <div className="alert-diagnosis-overlay" onClick={onClose}>
      <div className="alert-diagnosis-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Alert #{alertId} · Diagnosis Assistant</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        {loading ? (
          <div className="modal-loading">Loading…</div>
        ) : (
          <>
            {alert && (
              <div className="modal-alert-summary">
                <span>Asset: {alert.asset_id || '—'}</span>
                <span>Signal: {alert.signal || '—'}</span>
                <span className={`badge severity-${String(alert.severity || '').toLowerCase()}`}>{alert.severity || '—'}</span>
                <span>Score: {alert.score != null ? Number(alert.score).toFixed(2) : '—'}</span>
              </div>
            )}
            <div className="modal-diagnosis-block">
              <h4>Current Diagnosis</h4>
              {diagnosis ? (
                <div className="current-diagnosis">
                  <p><strong>Root cause:</strong> {diagnosis.root_cause}</p>
                  {diagnosis.confidence != null && <p><strong>Confidence:</strong> {(diagnosis.confidence * 100).toFixed(0)}%</p>}
                  {diagnosis.impact && <p><strong>Impact:</strong> {diagnosis.impact}</p>}
                  {diagnosis.recommended_actions?.length > 0 && (
                    <p><strong>Recommended actions:</strong> {diagnosis.recommended_actions.join('; ')}</p>
                  )}
                </div>
              ) : (
                <p className="no-diagnosis">No diagnosis yet. You can ask the assistant to generate one below.</p>
              )}
            </div>
            <div className="modal-actions">
              <button type="button" className="btn-quick" onClick={handleQuickGenerate} disabled={!!pendingUserMessage || generating}>
                {generating ? 'Generating…' : (diagnosis ? 'Regenerate diagnosis' : 'Generate diagnosis')}
              </button>
              {canSave && (
                <button type="button" className="btn-save" onClick={handleSaveAsDiagnosis} disabled={saving}>
                  {saving ? 'Saving…' : 'Save as diagnosis'}
                </button>
              )}
              {canAddToReview && (
                <button type="button" className="btn-review" onClick={handleAddToReviewQueue} disabled={addingToReview}>
                  {addingToReview ? 'Adding…' : 'Add to Review Queue'}
                </button>
              )}
              {inReviewQueue && (
                <span className="modal-badge-in-queue">Added to Review Queue</span>
              )}
            </div>
            <div className="modal-chat">
              <div className="modal-chat-messages">
                {modalMessages.map((m, i) => (
                  <div key={i} className={`message message-${m.role}`}>
                    <div className="message-role">{m.role === 'user' ? 'You' : 'Assistant'}</div>
                    <div className="message-content">
                      {m.role === 'assistant' ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || ''}</ReactMarkdown>
                      ) : (
                        <span>{m.content}</span>
                      )}
                    </div>
                  </div>
                ))}
                {pendingUserMessage != null && (
                  <div className="message message-user">
                    <div className="message-role">You</div>
                    <div className="message-content"><span>{pendingUserMessage}</span></div>
                  </div>
                )}
                {streamingSteps.length > 0 && (
                  <div className="message message-assistant streaming-steps">
                    <div className="message-role">Assistant</div>
                    <div className="message-steps">
                      {streamingSteps.map((step, i) => (
                        <div key={i} className={`step step-${step.step_type || 'thought'}`}>
                          <span className="step-label">
                            {step.step_type === 'tool_call' && '🔧 Tool'}
                            {step.step_type === 'tool_result' && '📋 Result'}
                            {(step.step_type === 'thought' || !step.step_type) && '💭 Thought'}
                          </span>
                          {step.tool_name && <span className="step-tool">{step.tool_name}</span>}
                          {step.content && <pre className="step-content">{step.content}</pre>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {streamingMessage != null && (
                  <div className="message message-assistant">
                    <div className="message-role">Assistant</div>
                    <div className="message-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingMessage}</ReactMarkdown>
                    </div>
                  </div>
                )}
                {pendingUserMessage != null && streamingSteps.length === 0 && !streamingMessage && (
                  <div className="message message-assistant message-loading">
                    <div className="message-role">Assistant</div>
                    <div className="message-content"><span className="typing-dots"><span className="dot" /><span className="dot" /><span className="dot" /></span></div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
              {error && <div className="modal-chat-error">{error}</div>}
              <div className="modal-chat-input-wrap">
                <textarea
                  className="modal-chat-input"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
                  placeholder="Ask a question, e.g. generate diagnosis, regenerate, or query rules and telemetry…"
                  rows={2}
                  disabled={!!pendingUserMessage || generating}
                />
                <button type="button" className="btn-send" onClick={handleSend} disabled={!input.trim() || !!pendingUserMessage || generating}>
                  Send
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default AlertDiagnosisModal
