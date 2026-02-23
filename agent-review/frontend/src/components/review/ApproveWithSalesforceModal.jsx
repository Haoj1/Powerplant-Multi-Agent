import { useState, useEffect } from 'react'
import { getApproveAssistant, approveWithCase, approveReview } from '../../services/api'
import './ApproveWithSalesforceModal.css'

function ApproveWithSalesforceModal({ reviewRequest, diagnosis, onSuccess, onClose }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
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
    if (!reviewRequest?.id) return
    setLoading(true)
    setError('')
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
      .catch((e) => setError(e?.response?.data?.detail || e?.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [reviewRequest?.id, diagnosis])

  const handleSubmit = async () => {
    if (!reviewRequest?.id || submitting) return
    setSubmitting(true)
    setError('')
    try {
      await approveWithCase(reviewRequest.id, {
        notes,
        case: form,
      })
      onSuccess?.()
      onClose?.()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Submit failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleApproveOnly = async () => {
    if (!reviewRequest?.id || submitting) return
    setSubmitting(true)
    setError('')
    try {
      await approveReview(reviewRequest.id, notes, false)
      onSuccess?.()
      onClose?.()
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Approve failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay approve-sf-overlay" onClick={onClose}>
      <div className="modal-content approve-sf-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Approve & Create Salesforce Case</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="modal-body">
          {loading ? (
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
        </div>
        <div className="modal-footer">
          {error && <div className="approve-sf-error">{error}</div>}
          <div className="footer-buttons">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="btn-approve-only"
              onClick={handleApproveOnly}
              disabled={loading || submitting}
            >
              Approve only
            </button>
            <button
              type="button"
              className="btn-submit"
              onClick={handleSubmit}
              disabled={loading || submitting || !form.subject?.trim() || !form.origin?.trim()}
            >
              {submitting ? 'Submitting…' : 'Submit & Approve'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ApproveWithSalesforceModal
