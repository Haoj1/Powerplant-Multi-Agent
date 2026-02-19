import { timeAgo } from '../../utils/timeAgo'
import './ReviewListTable.css'

function ReviewListTable({ requests, onViewDiagnosis }) {
  if (!requests || requests.length === 0) {
    return (
      <div className="review-list-empty">
        <p>No review requests match the current filters.</p>
      </div>
    )
  }

  return (
    <div className="review-list-table-wrap">
      <table className="review-list-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Asset</th>
            <th>Diagnosis ID</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {requests.map((req) => (
            <tr key={req.id}>
              <td>{req.id}</td>
              <td>{req.asset_id || '-'}</td>
              <td>
                <button
                  type="button"
                  className="link-btn"
                  onClick={() => onViewDiagnosis(req.diagnosis_id)}
                >
                  #{req.diagnosis_id}
                </button>
              </td>
              <td>{timeAgo(req.created_at)}</td>
              <td>
                <div className="action-buttons">
                  <button
                    type="button"
                    className="btn-view"
                    onClick={() => onViewDiagnosis(req.diagnosis_id)}
                  >
                    View
                  </button>
                  {req.status === 'pending' && (
                    <>
                      <button
                        type="button"
                        className="btn-approve"
                        onClick={() => onViewDiagnosis(req.diagnosis_id)}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="btn-reject"
                        onClick={() => onViewDiagnosis(req.diagnosis_id)}
                      >
                        Reject
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ReviewListTable
