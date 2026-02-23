import { useState, useEffect } from 'react'
import { getTelemetry } from '../services/api'
import SensorDashboard from '../components/sensors/SensorDashboard'
import SensorCharts from '../components/sensors/SensorCharts'
import AssetSelector from '../components/sensors/AssetSelector'
import LoadingSpinner from '../components/common/LoadingSpinner'
import './SensorsPage.css'

function SensorsPage() {
  const [selectedAsset, setSelectedAsset] = useState('pump01')
  const [telemetry, setTelemetry] = useState(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(5000)

  useEffect(() => {
    loadTelemetry()
    
    if (autoRefresh) {
      const interval = setInterval(loadTelemetry, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [selectedAsset, autoRefresh, refreshInterval])

  const loadTelemetry = async () => {
    try {
      setLoading(true)
      const data = await getTelemetry(selectedAsset, null, null, 1) // Get latest only
      setTelemetry(data && data.length > 0 ? data[0] : null)
    } catch (error) {
      console.error('Failed to load telemetry:', error)
      setTelemetry(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sensors-page">
      <div className="page-header">
        <h2>Real-time Sensors</h2>
        <AssetSelector
          selectedAsset={selectedAsset}
          onAssetChange={setSelectedAsset}
          autoRefresh={autoRefresh}
          onAutoRefreshChange={setAutoRefresh}
          refreshInterval={refreshInterval}
          onRefreshIntervalChange={setRefreshInterval}
        />
      </div>

      {loading && !telemetry ? (
        <LoadingSpinner />
      ) : telemetry ? (
        <SensorDashboard telemetry={telemetry} />
      ) : (
        <div className="empty-state">No telemetry data available</div>
      )}

      <SensorCharts assetId={selectedAsset} />
    </div>
  )
}

export default SensorsPage
