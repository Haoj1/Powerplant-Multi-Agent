import { useState, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { getTelemetry } from '../../services/api'
import LoadingSpinner from '../common/LoadingSpinner'
import './SensorCharts.css'

const TIME_RANGES = [
  { value: '1h', label: 'Last 1 hour', minutes: 60 },
  { value: '6h', label: 'Last 6 hours', minutes: 360 },
  { value: '24h', label: 'Last 24 hours', minutes: 1440 },
]

const CHART_SERIES = [
  { key: 'pressure_bar', name: 'Pressure', unit: 'bar', color: '#2563eb' },
  { key: 'flow_m3h', name: 'Flow', unit: 'm³/h', color: '#059669' },
  { key: 'temp_c', name: 'Temperature', unit: '°C', color: '#dc2626' },
  { key: 'bearing_temp_c', name: 'Bearing temp', unit: '°C', color: '#ea580c' },
  { key: 'vibration_rms', name: 'Vibration', unit: 'RMS', color: '#7c3aed' },
  { key: 'rpm', name: 'RPM', unit: '', color: '#0d9488' },
  { key: 'motor_current_a', name: 'Motor current', unit: 'A', color: '#ca8a04' },
  { key: 'valve_open_pct', name: 'Valve open', unit: '%', color: '#4b5563' },
]

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function SensorCharts({ assetId }) {
  const [timeRange, setTimeRange] = useState('1h')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!assetId) return
    let cancelled = false
    let sinceTs
    let untilTs

    if (timeRange === 'custom') {
      // Manual time window: use user-entered datetime-local
      if (!customFrom && !customTo) {
        // Custom time range incomplete, skip request
        return
      }
      const fromDate = customFrom ? new Date(customFrom) : null
      const toDate = customTo ? new Date(customTo) : null
      if ((fromDate && Number.isNaN(fromDate.getTime())) || (toDate && Number.isNaN(toDate.getTime()))) {
        return
      }
      if (fromDate) sinceTs = fromDate.toISOString()
      const until = toDate || new Date()
      untilTs = until.toISOString()
    } else {
      const range = TIME_RANGES.find((r) => r.value === timeRange) || TIME_RANGES[0]
      const until = new Date()
      const since = new Date(until.getTime() - range.minutes * 60 * 1000)
      sinceTs = since.toISOString()
      untilTs = until.toISOString()
    }

    setLoading(true)
    setError(null)
    getTelemetry(assetId, sinceTs, untilTs, 500)
      .then((raw) => {
        if (cancelled) return
        const list = Array.isArray(raw) ? [...raw] : []
        list.reverse()
        setData(
          list.map((row) => ({
            ...row,
            time: formatTime(row.ts),
            ts: row.ts,
          }))
        )
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || 'Failed to load chart data')
        setData([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [assetId, timeRange, customFrom, customTo])

  if (!assetId) return null

  return (
    <div className="sensor-charts">
      <div className="sensor-charts-header">
        <h3>Sensor history</h3>
        <div className="time-range-controls">
          <div className="time-range-buttons">
            {TIME_RANGES.map((r) => (
              <button
                key={r.value}
                type="button"
                className={`time-range-btn ${timeRange === r.value ? 'active' : ''}`}
                onClick={() => setTimeRange(r.value)}
              >
                {r.label}
              </button>
            ))}
          </div>
          <div className="time-range-custom">
            <label>
              <span>From</span>
              <input
                type="datetime-local"
                value={customFrom}
                onChange={(e) => {
                  setCustomFrom(e.target.value)
                  setTimeRange('custom')
                }}
              />
            </label>
            <label>
              <span>To</span>
              <input
                type="datetime-local"
                value={customTo}
                onChange={(e) => {
                  setCustomTo(e.target.value)
                  setTimeRange('custom')
                }}
              />
            </label>
          </div>
        </div>
      </div>

      {loading && <LoadingSpinner />}
      {error && <div className="sensor-charts-error">{error}</div>}

      {!loading && !error && data.length === 0 && (
        <div className="sensor-charts-empty">No data in this time window</div>
      )}

      {!loading && !error && data.length > 0 && (
        <div className="charts-grid">
          {CHART_SERIES.map(({ key, name, unit, color }) => {
            const hasData = data.some((d) => d[key] != null && d[key] !== '')
            if (!hasData) return null
            return (
              <div key={key} className="chart-card">
                <div className="chart-title">
                  {name}
                  {unit && <span className="chart-unit">{unit}</span>}
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} width={40} />
                    <Tooltip
                      labelFormatter={(t) => t}
                      formatter={(v) => [v != null ? Number(v).toFixed(2) : '-', name]}
                    />
                    <Line
                      type="monotone"
                      dataKey={key}
                      name={name}
                      stroke={color}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={data.length < 200}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default SensorCharts
