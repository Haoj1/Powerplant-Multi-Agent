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

export const getApproveAssistant = async (reviewId) => {
  const response = await api.get(`/review/${reviewId}/approve-assistant`)
  return response.data
}

export const approveWithCase = async (reviewId, { notes, case: caseData }) => {
  const response = await api.post(`/review/${reviewId}/approve-with-case`, {
    notes,
    case: caseData,
  })
  return response.data
}

/** Get Case picklist values from Salesforce (Status, Priority, Origin, Type, Reason). */
export const getCasePicklists = async () => {
  const response = await api.get('/salesforce/case-picklists')
  return response.data.picklists
}

// Troubleshooting Rules (Scenario Management)
export const getRules = async () => {
  const response = await api.get('/rules')
  return response.data.rules
}

export const getRuleDetail = async (name) => {
  const response = await api.get(`/rules/${encodeURIComponent(name)}`)
  return response.data
}

export const createRuleFromText = async (text) => {
  const response = await api.post('/rules/create-from-text', { text })
  return response.data
}

export const createRuleFromFlowchart = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  // Use fetch to avoid axios default Content-Type overriding multipart boundary
  const res = await fetch('/api/rules/create-from-flowchart', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const deleteRule = async (name) => {
  await api.delete(`/rules/${encodeURIComponent(name)}`)
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

// Single alert + diagnosis (for modal)
export const getAlertDetail = async (alertId) => {
  const response = await api.get(`/alerts/${alertId}`)
  return {
    alert: response.data.alert,
    diagnosis: response.data.diagnosis,
    in_review_queue: response.data.in_review_queue,
  }
}

// Generate diagnosis (one-shot, no ReAct - reliable, does not save)
export const generateDiagnosisForAlert = async (alertId) => {
  const response = await api.post(`/alerts/${alertId}/generate-diagnosis`)
  return response.data.diagnosis_text
}

// Create diagnosis for an alert (from modal after agent generated content)
export const createDiagnosisForAlert = async (alertId, payload) => {
  const response = await api.post(`/alerts/${alertId}/diagnosis`, payload)
  return response.data
}

// Add diagnosis to Review Queue
export const addDiagnosisToReviewQueue = async (diagnosisId) => {
  const response = await api.post(`/diagnosis/${diagnosisId}/add-to-review`)
  return response.data
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

export const deleteChatSession = async (sessionId) => {
  await api.post(`/chat/sessions/${sessionId}/delete`)
}

/**
 * Send a question to the chat API and consume SSE stream.
 * onEvent: (event) => void where event is { type: 'step'|'result'|'error', step?, answer?, error? }
 * options: { alertId, mode: 'diagnosis_assistant' } for alert modal chat (same tools as Agent D).
 * Returns the session_id from the result event (or null).
 */
export async function chatAskStream(question, sessionId, conversationHistory, onEvent, options = {}) {
  const url = '/api/chat/ask'
  const body = {
    question,
    session_id: sessionId || null,
    conversation_history: conversationHistory || [],
  }
  if (options.alertId != null) body.alert_id = options.alertId
  if (options.mode) body.mode = options.mode
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
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
