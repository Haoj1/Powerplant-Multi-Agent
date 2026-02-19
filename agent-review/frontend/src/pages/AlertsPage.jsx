import { useState, useEffect } from 'react'
import { getAlerts } from '../services/api'
import AlertsTable from '../components/alerts/AlertsTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import Pagination from '../components/common/Pagination'
import './AlertsPage.css'

const PAGE_SIZE_OPTIONS = [10, 20, 50]

function AlertsPage() {
  const [alerts, setAlerts] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ asset_id: '', severity: '' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  useEffect(() => {
    setPage(1)
  }, [filters.asset_id, filters.severity])

  useEffect(() => {
    loadAlerts()
    const interval = setInterval(loadAlerts, 30000)
    return () => clearInterval(interval)
  }, [filters, page, pageSize])

  const loadAlerts = async () => {
    try {
      setLoading(true)
      const offset = (page - 1) * pageSize
      const res = await getAlerts(
        filters.asset_id || null,
        pageSize,
        offset,
        filters.severity || null
      )
      setAlerts(res.data)
      setTotal(res.total)
    } catch (error) {
      console.error('Failed to load alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="alerts-page">
      <div className="page-header">
        <h2>Alerts</h2>
        <div className="filters">
          <input
            type="text"
            placeholder="Filter by Asset ID"
            value={filters.asset_id}
            onChange={(e) => setFilters({ ...filters, asset_id: e.target.value })}
          />
          <select
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
          >
            <option value="">All Severities</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
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
          <button onClick={loadAlerts}>Refresh</button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <>
          <AlertsTable alerts={alerts} />
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  )
}

export default AlertsPage
