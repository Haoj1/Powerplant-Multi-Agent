import { useState, useEffect } from 'react'
import { getScenarios, loadScenario, startScenario, stopScenario, resetScenario, triggerAlert } from '../services/simulatorApi'
import ScenarioListTable from '../components/scenarios/ScenarioListTable'
import LoadScenarioModal from '../components/scenarios/LoadScenarioModal'
import TriggerAlertModal from '../components/scenarios/TriggerAlertModal'
import LoadingSpinner from '../components/common/LoadingSpinner'
import './ScenariosPage.css'

function ScenariosPage() {
  const [scenarios, setScenarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [showLoadModal, setShowLoadModal] = useState(false)
  const [showTriggerModal, setShowTriggerModal] = useState(false)

  useEffect(() => {
    loadScenarios()
    // Auto-refresh every 5 seconds
    const interval = setInterval(loadScenarios, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadScenarios = async () => {
    try {
      const data = await getScenarios()
      setScenarios(data)
    } catch (error) {
      console.error('Failed to load scenarios:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadScenario = async (scenarioData) => {
    try {
      await loadScenario(scenarioData)
      await loadScenarios()
      setShowLoadModal(false)
    } catch (error) {
      console.error('Failed to load scenario:', error)
      throw error
    }
  }

  const handleStart = async (assetId) => {
    try {
      await startScenario(assetId)
      await loadScenarios()
    } catch (error) {
      console.error('Failed to start scenario:', error)
    }
  }

  const handleStop = async (assetId) => {
    try {
      await stopScenario(assetId)
      await loadScenarios()
    } catch (error) {
      console.error('Failed to stop scenario:', error)
    }
  }

  const handleReset = async (assetId) => {
    try {
      await resetScenario(assetId)
      await loadScenarios()
    } catch (error) {
      console.error('Failed to reset scenario:', error)
    }
  }

  const handleTriggerAlert = async (alertData) => {
    try {
      await triggerAlert(alertData)
      setShowTriggerModal(false)
    } catch (error) {
      console.error('Failed to trigger alert:', error)
      throw error
    }
  }

  return (
    <div className="scenarios-page">
      <div className="page-header">
        <h2>Scenario Management</h2>
        <div className="actions">
          <button onClick={() => setShowLoadModal(true)} className="btn-primary">
            + Load Scenario
          </button>
          <button onClick={() => setShowTriggerModal(true)} className="btn-secondary">
            Trigger Alert (Test)
          </button>
          <button onClick={loadScenarios} className="btn-refresh">Refresh</button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : (
        <ScenarioListTable
          scenarios={scenarios}
          onStart={handleStart}
          onStop={handleStop}
          onReset={handleReset}
        />
      )}

      {showLoadModal && (
        <LoadScenarioModal
          onLoad={handleLoadScenario}
          onClose={() => setShowLoadModal(false)}
        />
      )}

      {showTriggerModal && (
        <TriggerAlertModal
          onTrigger={handleTriggerAlert}
          onClose={() => setShowTriggerModal(false)}
        />
      )}
    </div>
  )
}

export default ScenariosPage
