import { useState } from 'react'
import './LoadScenarioModal.css'

const SCENARIO_TEMPLATES = [
  {
    id: 'healthy_baseline',
    label: 'Healthy baseline (no faults)',
    json: '{"version":"1.0","name":"healthy_baseline","description":"Healthy pump operation with no faults","plant_id":"plant01","asset_id":"pump01","seed":12345,"duration_sec":600,"initial_conditions":{"rpm":2950,"valve_open_pct":60},"faults":[],"setpoints":[{"time_sec":200,"valve_open_pct":70},{"time_sec":400,"valve_open_pct":50}]}',
  },
  {
    id: 'bearing_wear_chronic',
    label: 'Bearing wear (chronic)',
    json: '{"version":"1.0","name":"bearing_wear_chronic","description":"Chronic bearing wear - gradual degradation over time","plant_id":"plant01","asset_id":"pump01","seed":12345,"duration_sec":3600,"initial_conditions":{"rpm":2950,"valve_open_pct":60},"faults":[{"type":"bearing_wear","start_time_sec":100,"params":{"rate_per_sec":0.0001}}],"setpoints":[]}',
  },
  {
    id: 'clogging_ramp',
    label: 'Clogging (ramp)',
    json: '{"version":"1.0","name":"clogging_ramp","description":"Gradual clogging - resistance increases linearly over time","plant_id":"plant01","asset_id":"pump01","seed":12345,"duration_sec":3600,"initial_conditions":{"rpm":2950,"valve_open_pct":60},"faults":[{"type":"clogging","start_time_sec":200,"params":{"ramp_rate":0.0005}}],"setpoints":[]}',
  },
  {
    id: 'test_alert_quick',
    label: 'Test alert (quick)',
    json: '{"version":"1.0","name":"test_alert_quick","description":"Quick test scenario - high pressure/current to trigger alerts","plant_id":"plant01","asset_id":"pump01","seed":12345,"duration_sec":120,"initial_conditions":{"rpm":2950,"valve_open_pct":60},"faults":[{"type":"clogging","start_time_sec":10,"params":{"resistance_factor":3.5}}],"setpoints":[]}',
  },
]

function LoadScenarioModal({ onLoad, onClose }) {
  const [jsonText, setJsonText] = useState('')
  const [error, setError] = useState('')

  const applyTemplate = (template) => {
    try {
      const formatted = JSON.stringify(JSON.parse(template.json), null, 2)
      setJsonText(formatted)
      setError('')
    } catch {
      setJsonText(template.json)
    }
  }

  const handleLoad = () => {
    setError('')
    let scenario
    try {
      scenario = JSON.parse(jsonText.trim())
    } catch (e) {
      setError('Invalid JSON. Please check the scenario format.')
      return
    }
    if (!scenario || typeof scenario !== 'object') {
      setError('Scenario must be a JSON object.')
      return
    }
    onLoad(scenario).catch((e) => {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load scenario')
    })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content load-scenario-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Load Scenario</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          <div className="template-row">
            <label>Template:</label>
            <select
              value=""
              onChange={(e) => {
                const id = e.target.value
                if (id) {
                  const t = SCENARIO_TEMPLATES.find((x) => x.id === id)
                  if (t) applyTemplate(t)
                  e.target.value = ''
                }
              }}
            >
              <option value="">— Choose a template —</option>
              {SCENARIO_TEMPLATES.map((t) => (
                <option key={t.id} value={t.id}>{t.label}</option>
              ))}
            </select>
          </div>
          <p className="hint">
            Pick a template above or paste/edit scenario JSON below. Include <code>plant_id</code> and <code>asset_id</code>.
          </p>
          <textarea
            className="scenario-json-input"
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            placeholder='{"name":"my_scenario","plant_id":"plant01","asset_id":"pump01","duration_sec":600,...}'
            rows={12}
            spellCheck={false}
          />
          {error && <div className="modal-error">{error}</div>}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={handleLoad}>
            Load
          </button>
        </div>
      </div>
    </div>
  )
}

export default LoadScenarioModal
