import './AlertRulesTable.css'

function formatRule(r) {
  if (r.type === 'threshold' || r.type === 'threshold_high') {
    return `warning ≥ ${r.warning} ${r.unit}, critical ≥ ${r.critical} ${r.unit}`
  }
  if (r.type === 'threshold_low') {
    return `warning ≤ ${r.warning} ${r.unit}, critical ≤ ${r.critical} ${r.unit}`
  }
  if (r.type === 'range') {
    return `${r.min}–${r.max} ${r.unit}`
  }
  if (r.type === 'combination') {
    return r.desc || 'combination'
  }
  if (r.type === 'slope') {
    return `warning ≥ ${r.warning} ${r.unit}, critical ≥ ${r.critical} ${r.unit}`
  }
  if (r.type === 'slope_drop') {
    return `warning ≤ ${r.warning} ${r.unit}, critical ≤ ${r.critical} ${r.unit}`
  }
  return ''
}

function AlertRulesTable({ rules }) {
  if (!rules || rules.length === 0) {
    return (
      <div className="alert-rules-empty">
        <p>No alert rules loaded.</p>
      </div>
    )
  }

  return (
    <div className="alert-rules-table-wrap">
      <table className="alert-rules-table">
        <thead>
          <tr>
            <th>Signal</th>
            <th>Type</th>
            <th>Condition</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r, i) => (
            <tr key={`${r.signal}-${r.type}-${i}`}>
              <td><code>{r.signal}</code></td>
              <td>{r.type.replace('_', ' ')}</td>
              <td>{formatRule(r)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="alert-rules-hint">
        These rules are used by Agent A (Monitor) to detect anomalies. Use &quot;Trigger Alert (Test)&quot; to manually fire alerts.
      </p>
    </div>
  )
}

export default AlertRulesTable
