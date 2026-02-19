/**
 * API service for Agent D backend and Simulator.
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8005';
const SIMULATOR_URL = process.env.REACT_APP_SIMULATOR_URL || 'http://localhost:8001';

// Agent D API client
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Simulator API client
const simulatorClient = axios.create({
  baseURL: SIMULATOR_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Agent D API ---

export const reviewAPI = {
  // Review Requests
  getReviewRequests: (params = {}) => {
    return apiClient.get('/api/review-requests', { params });
  },

  // Diagnosis
  getDiagnosis: (diagnosisId) => {
    return apiClient.get(`/api/diagnosis/${diagnosisId}`);
  },

  // Alerts
  getAlerts: (params = {}) => {
    return apiClient.get('/api/alerts', { params });
  },

  // Telemetry
  getTelemetry: (params = {}) => {
    return apiClient.get('/api/telemetry', { params });
  },

  // Review Actions
  approveReview: (reviewId, body = {}) => {
    return apiClient.post(`/api/review/${reviewId}/approve`, body);
  },

  rejectReview: (reviewId, body = {}) => {
    return apiClient.post(`/api/review/${reviewId}/reject`, body);
  },
};

// --- Chat API ---

export const chatAPI = {
  // Sessions
  getSessions: (limit = 20) => {
    return apiClient.get('/api/chat/sessions', { params: { limit } });
  },

  getSession: (sessionId) => {
    return apiClient.get(`/api/chat/sessions/${sessionId}`);
  },

  // Chat (SSE - handled separately, this is just for reference)
  // Use EventSource directly: new EventSource(`/api/chat/ask?question=...&session_id=...`)
};

// --- Simulator API ---

export const simulatorAPI = {
  // Scenarios
  getScenarios: () => {
    return simulatorClient.get('/scenarios');
  },

  getStatus: (assetId = null) => {
    const params = assetId ? { asset_id: assetId } : {};
    return simulatorClient.get('/status', { params });
  },

  loadScenario: (scenario) => {
    return simulatorClient.post('/scenario/load', { scenario });
  },

  startScenario: (assetId) => {
    return simulatorClient.post(`/scenario/start/${assetId}`);
  },

  stopScenario: (assetId) => {
    return simulatorClient.post(`/scenario/stop/${assetId}`);
  },

  stopAllScenarios: () => {
    return simulatorClient.post('/scenario/stop');
  },

  resetScenario: (assetId) => {
    return simulatorClient.post(`/scenario/reset/${assetId}`);
  },

  // Manual Alert Trigger
  triggerAlert: (alertData) => {
    return simulatorClient.post('/alert/trigger', alertData);
  },
};

export default {
  reviewAPI,
  chatAPI,
  simulatorAPI,
};
