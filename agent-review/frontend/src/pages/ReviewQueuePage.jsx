import { useState, useEffect } from 'react'
import { getReviewRequests, getDiagnosis, approveReview, rejectReview } from '../services/api'
import ReviewListTable from '../components/review/ReviewListTable'
import DiagnosisDetailModal from '../components/review/DiagnosisDetailModal'
import LoadingSpinner from '../components/common/LoadingSpinner'
import Pagination from '../components/common/Pagination'
import './ReviewQueuePage.css'

const PAGE_SIZE_OPTIONS = [10, 20, 50]

function ReviewQueuePage() {
  const [reviewRequests, setReviewRequests] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selectedDiagnosis, setSelectedDiagnosis] = useState(null)
  const [filters, setFilters] = useState({ status: 'pending', asset_id: '' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const statusForApi = filters.status || 'pending'

  useEffect(() => {
    setPage(1)
  }, [filters.status, filters.asset_id])

  useEffect(() => {
    loadReviewRequests()
    const interval = setInterval(loadReviewRequests, 30000)
    return () => clearInterval(interval)
  }, [filters, page, pageSize])

  const loadReviewRequests = async () => {
    try {
      setLoading(true)
      const offset = (page - 1) * pageSize
      const res = await getReviewRequests(
        statusForApi,
        filters.asset_id || null,
        pageSize,
        offset
      )
      setReviewRequests(res.data)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to load review requests:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewDiagnosis = async (diagnosisId) => {
    try {
      const diagnosis = await getDiagnosis(diagnosisId)
      setSelectedDiagnosis(diagnosis)
    } catch (error) {
      console.error('Failed to load diagnosis:', error)
    }
  }

  const handleCloseModal = () => {
    setSelectedDiagnosis(null)
    loadReviewRequests() // Refresh list after approve/reject
  }

  const handleApprove = async (notes = '') => {
    const req = reviewRequests.find(r => r.diagnosis_id === selectedDiagnosis?.id)
    if (!req) return
    await approveReview(req.id, notes, false)
    handleCloseModal()
  }

  const handleReject = async (notes = '') => {
    const req = reviewRequests.find(r => r.diagnosis_id === selectedDiagnosis?.id)
    if (!req) return
    await rejectReview(req.id, notes)
    handleCloseModal()
  }

  return (
    <div className="review-queue-page">
      <div className="page-header">
        <h2>Review Queue</h2>
        <div className="filters">
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="">All</option>
          </select>
          <input
            type="text"
            placeholder="Filter by Asset ID"
            value={filters.asset_id}
            onChange={(e) => setFilters({ ...filters, asset_id: e.target.value })}
          />
          <label className="page-size-label">
            Per page:
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
          <button onClick={loadReviewRequests}>Refresh</button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <>
          <ReviewListTable
            requests={reviewRequests}
            onViewDiagnosis={handleViewDiagnosis}
          />
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
          />
        </>
      )}

      {selectedDiagnosis && (
        <DiagnosisDetailModal
          diagnosis={selectedDiagnosis}
          reviewRequest={reviewRequests.find(r => r.diagnosis_id === selectedDiagnosis.id)}
          onApprove={handleApprove}
          onReject={handleReject}
          onClose={handleCloseModal}
        />
      )}
    </div>
  )
}

export default ReviewQueuePage
