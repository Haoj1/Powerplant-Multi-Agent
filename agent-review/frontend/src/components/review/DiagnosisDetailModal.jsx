import { useState, useEffect } from 'react'
import { getApproveAssistant, approveWithCase, approveReview } from '../../services/api'
import './DiagnosisDetailModal.css'
import './ApproveWithSalesforceModal.css'

function DiagnosisDetailModal({ diagnosis, reviewRequest, onApprove, onReject, onClose }) {
  const [approveNotes, setApproveNotes] = useState('')
  const [rejectNotes, setRejectNotes] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [view, setView] = useState('detail') // 'detail' | 'approve-form'
  const [approveLoading, setApproveLoading] = useState(false)
  const [approveError, setApproveError] = useState('')
  const [analysis, setAnalysis] = useState('')
  const [similarCases, setSimilarCases] = useState([])
  const [form, setForm] = useState({
    subject: '',
    description: '',
    priority: 'Medium',
    status: 'New',
    origin: 'Web',
    type: '',
    reason: '',
  })
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [picklists, setPicklists] = useState({
    status: ['New', 'Working', 'Escalated', 'Closed'],
    priority: ['High', 'Medium', 'Low'],
    origin: ['Web', 'Phone', 'Email', 'Internal'],
    type: ['Problem', 'Question', 'Feature Request'],
    reason: ['Performance', 'Installation', 'Other'],
  })

  useEffect(() => {
    if (view === 'approve-form' && reviewRequest?.id) {
      setApproveLoading(true)
      setApproveError('')
      getApproveAssistant(reviewRequest.id)
        .then((data) => {
          setAnalysis(data.analysis || '')
          setSimilarCases(data.similar_cases || [])
          const pl = data.picklists
          if (pl && Object.keys(pl).length) setPicklists(pl)
          const sug = data.suggested_case || {}
          const inList = (val, list, def) =>
            list?.length && list.includes(val) ? val : (list?.[0] ?? def)
          setForm({
            subject: sug.subject || `[${diagnosis?.asset_id || ''}] ${(diagnosis?.root_cause || '').slice(0, 80)}`,
            description: sug.description || `Asset: ${diagnosis?.asset_id || ''}, Plant: ${diagnosis?.plant_id || ''}. Root cause: ${diagnosis?.root_cause || ''}`,
            priority: inList(sug.priority, pl?.priority, 'Medium'),
            status: inList(sug.status, pl?.status, 'New'),
            origin: inList(sug.origin, pl?.origin, 'Web'),
            type: inList(sug.type, pl?.type, '') || '',
            reason: inList(sug.reason, pl?.reason, '') || '',
          })
        })
        .catch((e) => setApproveError(e?.response?.data?.detail || e?.message || 'Failed to load'))
        .finally(() => setApproveLoading(false))
    }
  }, [view, reviewRequest?.id, diagnosis])

  if (!diagnosis) return null

  const confidence = diagnosis.confidence != null
    ? Math.round(Number(diagnosis.confidence) * 100)
    : null
  const actions = Array.isArray(diagnosis.recommended_actions)
    ? diagnosis.recommended_actions
    : typeof diagnosis.recommended_actions === 'string'
      ? [diagnosis.recommended_actions]
      : []
  const evidence = diagnosis.evidence

  const handleApproveClick = () => {
    if (!reviewRequest || actionLoading) return
    setView('approve-form')
  }

  const handleBackToDetail = () => {
    setView('detail')
    setApproveError('')
  }

  const handleSubmitWithCase = async () => {
    if (!reviewRequest?.id || submitting) return
    setSubmitting(true)
    setApproveError('')
    try {
      await approveWithCase(reviewRequest.id, { notes, case: form })
      onClose()
    } catch (e) {
      setApproveError(e?.response?.data?.detail || e?.message || 'Submit failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleApproveOnly = async () => {
    if (!reviewRequest?.id || submitting) return
    setSubmitting(true)
    setApproveError('')
    try {
      await approveReview(reviewRequest.id, notes, false)
      onClose()
    } catch (e) {
      setApproveError(e?.response?.data?.detail || e?.message || 'Approve failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!reviewRequest || actionLoading) return
    setActionLoading(true)
    try {
      await onReject(rejectNotes)
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content diagnosis-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          {view === 'approve-form' ? (
            <div className="modal-header-left">
              <button type="button" className="modal-back" onClick={handleBackToDetail}>
                ← Back
              </button>
              <h3>Approve & Create Salesforce Case</h3>
            </div>
          ) : (
            <h3>Diagnosis #{diagnosis.id}</h3>
          )}
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
          {view === 'approve-form' ? (
            <>
              {approveLoading ? (
                <div className="approve-sf-loading">Analyzing diagnosis and fetching similar cases…</div>
              ) : (
                <>
                  {analysis && (
                    <div className="approve-sf-analysis">
                      <h4>Analysis</h4>
                      <p>{analysis}</p>
                    </div>
                  )}
                  {similarCases.length > 0 && (
                    <div className="approve-sf-similar">
                      <h4>Similar Cases (reference)</h4>
                      <ul>
                        {similarCases.map((c) => (
                          <li key={c.id}>
                            <a href={c.url} target="_blank" rel="noopener noreferrer">
                              {c.subject || c.id}
                            </a>
                            {c.priority && <span className="case-priority">{c.priority}</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="approve-sf-form">
                    <h4>Case Form</h4>
                    <div className="form-row">
                      <label>Subject</label>
                      <input
                        type="text"
                        value={form.subject}
                        onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                        placeholder="Case subject"
                        maxLength={255}
                      />
                    </div>
                    <div className="form-row">
                      <label>Description</label>
                      <textarea
                        value={form.description}
                        onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                        placeholder="Case description"
                        rows={4}
                      />
                    </div>
                    <div className="form-row form-row-group">
                      <div className="form-row">
                        <label>Priority</label>
                        <select
                          value={form.priority}
                          onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                        >
                          {(picklists.priority || []).map((v) => (
                            <option key={v} value={v}>{v}</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-row">
                        <label>* Status</label>
                        <select
                          value={form.status}
                          onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                        >
                          {(picklists.status || []).map((v) => (
                            <option key={v} value={v}>{v}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="form-row form-row-group">
                      <div className="form-row">
                        <label>* Case Origin</label>
                        <select
                          value={form.origin}
                          onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))}
                        >
                          <option value="">--None--</option>
                          {(picklists.origin || []).map((v) => (
                            <option key={v} value={v}>{v}</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-row">
                        <label>Type</label>
                        <select
                          value={form.type}
                          onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                        >
                          <option value="">--None--</option>
                          {(picklists.type || []).map((v) => (
                            <option key={v} value={v}>{v}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div className="form-row">
                      <label>Case Reason</label>
                      <select
                        value={form.reason}
                        onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
                      >
                        <option value="">--None--</option>
                        {(picklists.reason || []).map((v) => (
                          <option key={v} value={v}>{v}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-row">
                      <label>Notes (optional)</label>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Internal notes"
                        rows={2}
                      />
                    </div>
                  </div>
                </>
              )}
            </>
          ) : (
            <>
          <div className="diagnosis-meta">
            <p><strong>Asset:</strong> {diagnosis.asset_id || '-'}</p>
            <p><strong>Plant:</strong> {diagnosis.plant_id || '-'}</p>
            <p><strong>Timestamp:</strong> {diagnosis.ts ? new Date(diagnosis.ts).toLocaleString() : '-'}</p>
          </div>

          <div className="diagnosis-main">
            <p><strong>Root Cause:</strong> {diagnosis.root_cause || '-'}</p>
            {confidence != null && (
              <p>
                <strong>Confidence:</strong>{' '}
                <span className="confidence-bar-wrap">
                  <span className="confidence-bar" style={{ width: `${confidence}%` }} />
                  <span className="confidence-text">{confidence}%</span>
                </span>
              </p>
            )}
            {diagnosis.impact && <p><strong>Impact:</strong> {diagnosis.impact}</p>}
          </div>

          {actions.length > 0 && (
            <div className="diagnosis-section">
              <strong>Recommended Actions:</strong>
              <ul>
                {actions.map((a, i) => (
                  <li key={i}>{typeof a === 'string' ? a : JSON.stringify(a)}</li>
                ))}
              </ul>
            </div>
          )}

          {evidence != null && (
            <div className="diagnosis-section">
              <strong>Evidence:</strong>
              <pre className="evidence-pre">{JSON.stringify(evidence, null, 2)}</pre>
            </div>
          )}
            </>
          )}
        </div>

        <div className="modal-footer">
          {view === 'approve-form' ? (
            <>
              {approveError && <div className="approve-sf-error">{approveError}</div>}
              <div className="footer-buttons">
                <button type="button" className="btn-cancel" onClick={handleBackToDetail}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-approve-only"
                  onClick={handleApproveOnly}
                  disabled={approveLoading || submitting}
                >
                  Approve only
                </button>
                <button
                  type="button"
                  className="btn-submit"
                  onClick={handleSubmitWithCase}
                  disabled={approveLoading || submitting || !form.subject?.trim() || !form.origin?.trim()}
                >
                  {submitting ? 'Submitting…' : 'Submit & Approve'}
                </button>
              </div>
            </>
          ) : reviewRequest?.status === 'pending' && (
            <>
              <div className="footer-actions">
                <div className="action-group">
                  <label>Approve notes (optional)</label>
                  <textarea
                    value={approveNotes}
                    onChange={(e) => setApproveNotes(e.target.value)}
                    placeholder="Optional notes..."
                    rows={2}
                  />
                  <button
                    type="button"
                    className="btn-approve"
                    onClick={handleApproveClick}
                    disabled={actionLoading}
                  >
                    {actionLoading ? '…' : 'Approve'}
                  </button>
                </div>
                <div className="action-group">
                  <label>Reject notes</label>
                  <textarea
                    value={rejectNotes}
                    onChange={(e) => setRejectNotes(e.target.value)}
                    placeholder="Reason for rejection..."
                    rows={2}
                  />
                  <button
                    type="button"
                    className="btn-reject"
                    onClick={handleReject}
                    disabled={actionLoading}
                  >
                    {actionLoading ? '…' : 'Reject'}
                  </button>
                </div>
              </div>
            </>
          )}
          <button type="button" className="btn-close" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default DiagnosisDetailModal
