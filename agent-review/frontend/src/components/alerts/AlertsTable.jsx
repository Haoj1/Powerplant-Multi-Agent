import { Link } from 'react-router-dom'
import { timeAgo } from '../../utils/timeAgo'
import './AlertsTable.css'

function AlertsTable({ alerts, onAlertClick }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="alerts-table-empty">
        <p>No alerts match the current filters.</p>
      </div>
    )
  }

  return (
    <div className="alerts-table-wrap">
      <table className="alerts-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Asset</th>
            <th>Signal</th>
            <th>Severity</th>
            <th>Score</th>
            <th>Diagnosis</th>
            <th>Ticket</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <tr
              key={a.alert_id}
              className="alerts-table-row-clickable"
              onClick={() => onAlertClick && onAlertClick(a)}
            >
              <td>{a.alert_id}</td>
              <td>{a.asset_id || '-'}</td>
              <td>{a.signal || '-'}</td>
              <td>
                <span className={`badge severity-${String(a.severity || '').toLowerCase()}`}>
                  {a.severity || '-'}
                </span>
              </td>
              <td>{a.score != null ? Number(a.score).toFixed(2) : '-'}</td>
              <td onClick={(e) => e.stopPropagation()}>
                {a.diagnosis_id != null ? (
                  <Link to="/review" className="link-btn">
                    #{a.diagnosis_id}
                  </Link>
                ) : (
                  '-'
                )}
              </td>
              <td onClick={(e) => e.stopPropagation()}>
                {a.ticket_url ? (
                  <a href={a.ticket_url} target="_blank" rel="noopener noreferrer" className="link-btn">
                    {a.ticket_id || 'Ticket'}
                  </a>
                ) : a.ticket_id ? (
                  <span>{a.ticket_id}</span>
                ) : (
                  '-'
                )}
              </td>
              <td>{timeAgo(a.ts)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default AlertsTable
