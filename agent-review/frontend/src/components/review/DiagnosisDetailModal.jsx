import { useState } from 'react'
import './DiagnosisDetailModal.css'

function DiagnosisDetailModal({ diagnosis, reviewRequest, onApprove, onReject, onClose }) {
  const [approveNotes, setApproveNotes] = useState('')
  const [rejectNotes, setRejectNotes] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

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

  const handleApprove = async () => {
    if (!reviewRequest || actionLoading) return
    setActionLoading(true)
    try {
      await onApprove(approveNotes)
      onClose()
    } catch (e) {
      console.error(e)
    } finally {
      setActionLoading(false)
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
          <h3>Diagnosis #{diagnosis.id}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
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
        </div>

        <div className="modal-footer">
          {reviewRequest?.status === 'pending' && (
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
                    onClick={handleApprove}
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
