import './RulesListTable.css'

function RulesListTable({ rules, onView, onDelete, onRefresh }) {
  if (!rules || rules.length === 0) {
    return (
      <div className="rules-list-empty">
        <p>No troubleshooting rules yet. Create rules from natural language or upload a flowchart.</p>
        <p className="hint">Rules are used by Agent B (diagnosis) when analyzing alerts.</p>
        <p className="hint path-hint">Rules are stored in <code>agent-diagnosis/rules/*.md</code></p>
      </div>
    )
  }

  return (
    <div className="rules-list-table-wrap">
      <table className="rules-list-table">
        <thead>
          <tr>
            <th>Rule Name</th>
            <th>Root Cause</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.name}>
              <td>{r.title || r.name}</td>
              <td><code>{r.root_cause}</code></td>
              <td>
                <div className="action-buttons">
                  <button
                    type="button"
                    className="btn-view"
                    onClick={() => onView?.(r.name)}
                    title="View rule"
                  >
                    View
                  </button>
                  <button
                    type="button"
                    className="btn-delete"
                    onClick={() => onDelete?.(r.name)}
                    title="Delete rule"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default RulesListTable
