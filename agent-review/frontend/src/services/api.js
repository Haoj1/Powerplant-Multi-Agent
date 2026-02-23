/**
 * API service for Agent D backend (port 8005)
 */

import axios from 'axios'

const API_BASE_URL = '/api'  // Proxy to http://localhost:8005

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Review Requests (paginated)
export const getReviewRequests = async (status = 'pending', assetId = null, limit = 20, offset = 0) => {
  const params = { status, limit, offset }
  if (assetId) params.asset_id = assetId
  const response = await api.get('/review-requests', { params })
  return { data: response.data.data, total: response.data.total ?? 0 }
}

export const approveReview = async (reviewId, notes = '', createSalesforceCase = false) => {
  const response = await api.post(`/review/${reviewId}/approve`, {
    notes,
    create_salesforce_case: createSalesforceCase,
  })
  return response.data
}

export const rejectReview = async (reviewId, notes = '') => {
  const response = await api.post(`/review/${reviewId}/reject`, { notes })
  return response.data
}

// Diagnosis
export const getDiagnosis = async (diagnosisId) => {
  const response = await api.get(`/diagnosis/${diagnosisId}`)
  return response.data.data
}

// Alerts (paginated)
export const getAlerts = async (assetId = null, limit = 20, offset = 0, severity = null) => {
  const params = { limit, offset }
  if (assetId) params.asset_id = assetId
  if (severity) params.severity = severity
  const response = await api.get('/alerts', { params })
  return { data: response.data.data, total: response.data.total ?? 0 }
}

// Telemetry (optionally with time window: since_ts, until_ts)
export const getTelemetry = async (assetId, sinceTs = null, untilTs = null, limit = 500) => {
  const params = { asset_id: assetId, limit }
  if (sinceTs) params.since_ts = sinceTs
  if (untilTs) params.until_ts = untilTs
  const response = await api.get('/telemetry', { params })
  return response.data.data
}

// Chat
export const getChatSessions = async (limit = 20) => {
  const response = await api.get('/chat/sessions', { params: { limit } })
  return response.data.sessions
}

export const getChatSession = async (sessionId) => {
  const response = await api.get(`/chat/sessions/${sessionId}`)
  return response.data
}

/**
 * Send a question to the chat API and consume SSE stream.
 * onEvent: (event) => void where event is { type: 'step'|'result'|'error', step?, answer?, error? }
 * Returns the session_id from the result event (or null).
 */
export async function chatAskStream(question, sessionId, conversationHistory, onEvent) {
  const url = '/api/chat/ask'
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      session_id: sessionId || null,
      conversation_history: conversationHistory || [],
    }),
  })
  if (!res.ok) throw new Error(res.statusText || 'Chat request failed')
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let sessionIdOut = null
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n\n')
    buffer = lines.pop() || ''
    for (const chunk of lines) {
      const dataLine = chunk.split('\n').find((l) => l.startsWith('data:'))
      if (!dataLine) continue
      try {
        const data = JSON.parse(dataLine.slice(5).trim())
        if (data.type === 'result' && data.session_id != null) sessionIdOut = data.session_id
        if (onEvent) onEvent(data)
      } catch (_) {}
    }
  }
  return sessionIdOut
}

export default api
