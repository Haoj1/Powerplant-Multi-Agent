import { useState } from 'react'
import './TriggerAlertModal.css'

const SIGNAL_OPTIONS = [
  'vibration_rms',
  'bearing_temp_c',
  'pressure_bar',
  'motor_current_a',
  'temp_c',
  'flow_m3h',
  'rpm',
  'valve_flow_mismatch',
  'valve_open_pct',
]

function TriggerAlertModal({ onTrigger, onClose }) {
  const [assetId, setAssetId] = useState('pump01')
  const [plantId, setPlantId] = useState('plant01')
  const [signal, setSignal] = useState('vibration_rms')
  const [severity, setSeverity] = useState('critical')
  const [score, setScore] = useState(3.5)
  const [error, setError] = useState('')

  const handleTrigger = () => {
    setError('')
    onTrigger({
      asset_id: assetId,
      plant_id: plantId,
      signal,
      severity,
      score: Number(score),
      method: 'manual',
      evidence: { manual_trigger: true },
    }).catch((e) => {
      setError(e?.response?.data?.detail || e?.message || 'Failed to trigger alert')
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content trigger-alert-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Trigger Alert (Test)</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          <div className="form-row">
            <label>Asset ID</label>
            <input
              type="text"
              value={assetId}
              onChange={(e) => setAssetId(e.target.value)}
              placeholder="pump01"
            />
          </div>
          <div className="form-row">
            <label>Plant ID</label>
            <input
              type="text"
              value={plantId}
              onChange={(e) => setPlantId(e.target.value)}
              placeholder="plant01"
            />
          </div>
          <div className="form-row">
            <label>Signal</label>
            <select value={signal} onChange={(e) => setSignal(e.target.value)}>
              {SIGNAL_OPTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Severity</label>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="form-row">
            <label>Score</label>
            <input
              type="number"
              step="0.1"
              value={score}
              onChange={(e) => setScore(e.target.value)}
            />
          </div>
          {error && <div className="modal-error">{error}</div>}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={handleTrigger}>
            Trigger
          </button>
        </div>
      </div>
    </div>
  )
}

export default TriggerAlertModal
