import './AssetSelector.css'

const DEFAULT_ASSETS = ['pump01', 'pump02', 'motor01']

function AssetSelector({
  selectedAsset,
  onAssetChange,
  autoRefresh,
  onAutoRefreshChange,
  refreshInterval,
  onRefreshIntervalChange,
}) {
  return (
    <div className="asset-selector">
      <label>
        <span>Asset:</span>
        <select
          value={selectedAsset}
          onChange={(e) => onAssetChange(e.target.value)}
        >
          {DEFAULT_ASSETS.map((id) => (
            <option key={id} value={id}>{id}</option>
          ))}
        </select>
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={autoRefresh}
          onChange={(e) => onAutoRefreshChange(e.target.checked)}
        />
        <span>Auto-refresh</span>
      </label>
      {autoRefresh && (
        <label>
          <span>Interval:</span>
          <select
            value={refreshInterval}
            onChange={(e) => onRefreshIntervalChange(Number(e.target.value))}
          >
            <option value={3000}>3s</option>
            <option value={5000}>5s</option>
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
          </select>
        </label>
      )}
    </div>
  )
}

export default AssetSelector
