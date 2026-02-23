import { useState, useEffect } from 'react'
import { getScenarios, loadScenario, startScenario, stopScenario, resetScenario, triggerAlert } from '../services/simulatorApi'
import { getRules, deleteRule } from '../services/api'
import ScenarioListTable from '../components/scenarios/ScenarioListTable'
import LoadScenarioModal from '../components/scenarios/LoadScenarioModal'
import TriggerAlertModal from '../components/scenarios/TriggerAlertModal'
import CreateRuleModal from '../components/scenarios/CreateRuleModal'
import ViewRuleModal from '../components/scenarios/ViewRuleModal'
import RulesListTable from '../components/scenarios/RulesListTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import './ScenariosPage.css'

function ScenariosPage() {
  const [activeTab, setActiveTab] = useState('scenarios') // 'scenarios' | 'rules'
  const [scenarios, setScenarios] = useState([])
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [rulesLoading, setRulesLoading] = useState(false)
  const [showLoadModal, setShowLoadModal] = useState(false)
  const [showTriggerModal, setShowTriggerModal] = useState(false)
  const [showCreateRuleModal, setShowCreateRuleModal] = useState(false)
  const [viewRuleName, setViewRuleName] = useState(null)

  useEffect(() => {
    loadScenarios()
    const interval = setInterval(loadScenarios, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (activeTab === 'rules') loadRules()
  }, [activeTab])

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

  const loadRules = async () => {
    setRulesLoading(true)
    try {
      const data = await getRules()
      setRules(data || [])
    } catch (error) {
      console.error('Failed to load rules:', error)
      setRules([])
    } finally {
      setRulesLoading(false)
    }
  }

  const handleRuleCreated = () => {
    loadRules()
  }

  const handleDeleteRule = async (name) => {
    if (!window.confirm(`Delete rule "${name}"?`)) return
    try {
      await deleteRule(name)
      loadRules()
    } catch (error) {
      console.error('Failed to delete rule:', error)
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
        <div className="page-tabs">
          <button
            type="button"
            className={activeTab === 'scenarios' ? 'active' : ''}
            onClick={() => setActiveTab('scenarios')}
          >
            Simulator Scenarios
          </button>
          <button
            type="button"
            className={activeTab === 'rules' ? 'active' : ''}
            onClick={() => setActiveTab('rules')}
          >
            Troubleshooting Rules
          </button>
        </div>
        <div className="actions">
          {activeTab === 'scenarios' && (
            <>
              <button onClick={() => setShowLoadModal(true)} className="btn-primary">
                + Load Scenario
              </button>
              <button onClick={() => setShowTriggerModal(true)} className="btn-secondary">
                Trigger Alert (Test)
              </button>
              <button onClick={loadScenarios} className="btn-refresh">Refresh</button>
            </>
          )}
          {activeTab === 'rules' && (
            <>
              <button onClick={() => setShowCreateRuleModal(true)} className="btn-primary">
                + Create Rule
              </button>
              <button onClick={loadRules} className="btn-refresh">Refresh</button>
            </>
          )}
        </div>
      </div>

      {activeTab === 'scenarios' && (
        loading ? (
          <LoadingSpinner />
        ) : (
          <ScenarioListTable
            scenarios={scenarios}
            onStart={handleStart}
            onStop={handleStop}
            onReset={handleReset}
          />
        )
      )}

      {activeTab === 'rules' && (
        rulesLoading ? (
          <LoadingSpinner />
        ) : (
          <RulesListTable
            rules={rules}
            onView={(name) => setViewRuleName(name)}
            onDelete={handleDeleteRule}
            onRefresh={loadRules}
          />
        )
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

      {showCreateRuleModal && (
        <CreateRuleModal
          onCreated={handleRuleCreated}
          onClose={() => setShowCreateRuleModal(false)}
        />
      )}

      {viewRuleName && (
        <ViewRuleModal
          ruleName={viewRuleName}
          onClose={() => setViewRuleName(null)}
        />
      )}
    </div>
  )
}

export default ScenariosPage
