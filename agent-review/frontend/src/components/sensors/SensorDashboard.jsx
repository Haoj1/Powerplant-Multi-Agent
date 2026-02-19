import './SensorDashboard.css'

const SENSOR_FIELDS = [
  { key: 'pressure_bar', label: 'Pressure', unit: 'bar' },
  { key: 'flow_m3h', label: 'Flow', unit: 'm³/h' },
  { key: 'temp_c', label: 'Temperature', unit: '°C' },
  { key: 'bearing_temp_c', label: 'Bearing temp', unit: '°C' },
  { key: 'vibration_rms', label: 'Vibration', unit: 'RMS' },
  { key: 'rpm', label: 'RPM', unit: '' },
  { key: 'motor_current_a', label: 'Motor current', unit: 'A' },
  { key: 'valve_open_pct', label: 'Valve open', unit: '%' },
]

function SensorDashboard({ telemetry }) {
  if (!telemetry) return null

  const ts = telemetry.ts ? new Date(telemetry.ts).toLocaleString() : '-'

  return (
    <div className="sensor-dashboard">
      <div className="sensor-dashboard-meta">
        <span>Last updated: {ts}</span>
        {telemetry.fault != null && telemetry.fault !== 0 && (
          <span className="fault-badge">Fault</span>
        )}
        {telemetry.severity && (
          <span className={`severity-badge severity-${String(telemetry.severity).toLowerCase()}`}>
            {telemetry.severity}
          </span>
        )}
      </div>
      <div className="sensor-grid">
        {SENSOR_FIELDS.map(({ key, label, unit }) => {
          const value = telemetry[key]
          const display = value != null && value !== '' ? Number(value).toFixed(2) : '-'
          return (
            <div key={key} className="sensor-card">
              <div className="sensor-label">{label}</div>
              <div className="sensor-value">
                {display}
                {unit && display !== '-' && <span className="sensor-unit">{unit}</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default SensorDashboard
