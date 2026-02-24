/**
 * API service for Simulator (port 8001)
 * Production: VITE_API_BASE_URL=https://api.powerplantagent.com
 * Dev: Vite proxy /simulator -> localhost:8001
 */
import axios from 'axios'

const SIMULATOR_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')}/simulator`
  : '/simulator'

const simulatorApi = axios.create({
  baseURL: SIMULATOR_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Scenarios
export const getScenarios = async () => {
  const response = await simulatorApi.get('/scenarios')
  return response.data.scenarios
}

export const getScenarioStatus = async (assetId = null) => {
  const params = assetId ? { asset_id: assetId } : {}
  const response = await simulatorApi.get('/status', { params })
  return response.data
}

export const loadScenario = async (scenario) => {
  const response = await simulatorApi.post('/scenario/load', { scenario })
  return response.data
}

export const startScenario = async (assetId) => {
  const response = await simulatorApi.post(`/scenario/start/${assetId}`)
  return response.data
}

export const stopScenario = async (assetId) => {
  const response = await simulatorApi.post(`/scenario/stop/${assetId}`)
  return response.data
}

export const stopAllScenarios = async () => {
  const response = await simulatorApi.post('/scenario/stop')
  return response.data
}

export const resetScenario = async (assetId) => {
  const response = await simulatorApi.post(`/scenario/reset/${assetId}`)
  return response.data
}

// Manual Alert Trigger
export const triggerAlert = async (alertData) => {
  const response = await simulatorApi.post('/alert/trigger', alertData)
  return response.data
}

export default simulatorApi
