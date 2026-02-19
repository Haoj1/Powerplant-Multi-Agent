import './ScenarioListTable.css'

function ScenarioListTable({ scenarios, onStart, onStop, onReset }) {
  if (!scenarios || scenarios.length === 0) {
    return (
      <div className="scenario-list-empty">
        <p>No scenarios loaded. Use &quot;Load Scenario&quot; to load a scenario JSON.</p>
      </div>
    )
  }

  return (
    <div className="scenario-list-table-wrap">
      <table className="scenario-list-table">
        <thead>
          <tr>
            <th>Asset ID</th>
            <th>Scenario Name</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => {
            const duration = s.duration_sec || 1
            const current = s.current_time || 0
            const pct = duration > 0 ? Math.min(100, (current / duration) * 100) : 0
            return (
              <tr key={s.asset_id}>
                <td>{s.asset_id}</td>
                <td>{s.scenario_name}</td>
                <td>
                  <span className={`badge status-${s.running ? 'running' : 'stopped'}`}>
                    {s.running ? 'Running' : 'Stopped'}
                  </span>
                </td>
                <td>
                  <div className="progress-wrap">
                    <div className="progress-bar" style={{ width: `${pct}%` }} />
                    <span className="progress-text">
                      {current.toFixed(0)}s / {duration}s
                    </span>
                  </div>
                </td>
                <td>
                  <div className="action-buttons">
                    {!s.running ? (
                      <button
                        type="button"
                        className="btn-start"
                        onClick={() => onStart(s.asset_id)}
                      >
                        Start
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn-stop"
                        onClick={() => onStop(s.asset_id)}
                      >
                        Stop
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-reset"
                      onClick={() => onReset(s.asset_id)}
                    >
                      Reset
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default ScenarioListTable
