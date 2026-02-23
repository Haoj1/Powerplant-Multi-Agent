import { useState, useEffect } from 'react'
import { getRuleDetail } from '../../services/api'
import './ViewRuleModal.css'

function ViewRuleModal({ ruleName, onClose }) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!ruleName) return
    setLoading(true)
    setError('')
    getRuleDetail(ruleName)
      .then((data) => setContent(data.content || ''))
      .catch((e) => setError(e?.response?.data?.detail || e?.message || 'Failed to load rule'))
      .finally(() => setLoading(false))
  }, [ruleName])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content view-rule-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>View Rule: {ruleName?.replace(/_/g, ' ') || ''}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          {loading ? (
            <div className="view-rule-loading">Loading…</div>
          ) : error ? (
            <div className="view-rule-error">{error}</div>
          ) : (
            <pre className="view-rule-content">{content}</pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default ViewRuleModal
