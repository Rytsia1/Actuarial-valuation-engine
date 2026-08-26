/**
 * Actuarial Engine API Service
 * Centralized API interface using Axios with global interceptors, automatic error handling, and timeout safety.
 */

import httpClient, { ActuaryApiError } from '../api/httpClient'

export { ActuaryApiError }

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
const API_BASE = BASE_URL ? `${BASE_URL}/api/v1` : '/api/v1'

/**
 * Health check endpoint
 * GET /api/v1/health
 */
export async function checkHealth() {
  return await httpClient.get('/health')
}

/**
 * List all available mortality tables (built-in and custom uploaded)
 * GET /api/v1/tables
 */
export async function fetchTables() {
  return await httpClient.get('/tables')
}

/**
 * Upload custom mortality table file (CSV or XTbML)
 * POST /api/v1/tables/upload
 * 
 * @param {FormData} formData - Contains 'file', 'table_name', 'table_description'
 * @returns {Promise<Object>} TableUploadResponse
 */
export async function uploadMortalityTable(formData) {
  return await httpClient.post('/tables/upload', formData)
}

/**
 * Delete a custom mortality table
 * DELETE /api/v1/tables/{table_id}
 * 
 * @param {string} tableId - ID of table to delete
 * @returns {Promise<Object>} Status response
 */
export async function deleteMortalityTable(tableId) {
  return await httpClient.delete(`/tables/${encodeURIComponent(tableId)}`)
}

/**
 * Run deterministic baseline valuation
 * POST /api/v1/valuation/deterministic
 * 
 * @param {Object} payload - DeterministicValuationRequest
 * @returns {Promise<Object>} DeterministicValuationResponse
 */
export async function runDeterministicValuation(payload) {
  return await httpClient.post('/valuation/deterministic', payload)
}

/**
 * Run IFRS 17 standard valuation
 * POST /api/v1/valuation/ifrs17
 * 
 * @param {Object} payload - IFRS17ValuationRequest
 * @returns {Promise<Object>} IFRS17ValuationResponse
 */
export async function runIFRS17Valuation(payload) {
  return await httpClient.post('/valuation/ifrs17', payload)
}

/**
 * Start asynchronous Monte Carlo stochastic simulation job
 * POST /api/v1/valuation/stochastic/async
 * 
 * @param {Object} payload - StochasticValuationRequest
 * @returns {Promise<Object>} AsyncJobCreateResponse { job_id, status }
 */
export async function startAsyncStochasticValuation(payload) {
  return await httpClient.post('/valuation/stochastic/async', payload)
}

/**
 * Check status of background stochastic valuation job
 * GET /api/v1/valuation/stochastic/status/{job_id}
 * 
 * @param {string} jobId - UUID of the async job
 * @returns {Promise<Object>} AsyncJobStatusResponse
 */
export async function getStochasticJobStatus(jobId) {
  return await httpClient.get(`/valuation/stochastic/status/${encodeURIComponent(jobId)}`)
}

/**
 * Run synchronous stochastic valuation (legacy / fast simulation)
 * POST /api/v1/valuation/stochastic
 * 
 * @param {Object} payload - StochasticValuationRequest
 * @returns {Promise<Object>} StochasticValuationResponse
 */
export async function runStochasticValuation(payload) {
  return await httpClient.post('/valuation/stochastic', payload)
}

/**
 * Upload seriatim portfolio CSV for parallel batch valuation
 * POST /api/v1/valuation/portfolio/csv
 * 
 * @param {FormData} formData - Multipart with 'file' and valuation parameters
 * @returns {Promise<Object>} PortfolioValuationResponse
 */
export async function uploadPortfolioCSV(formData) {
  return await httpClient.post('/valuation/portfolio/csv', formData)
}

/**
 * Get direct download URL for synthetic portfolio CSV
 * 
 * @param {number} count - Number of policies to generate
 * @returns {string} URL string
 */
export function getSamplePortfolioCSVUrl(count = 1000) {
  return `${API_BASE}/valuation/portfolio/sample-csv?count=${count}`
}

/**
 * Run multi-factor sensitivity analysis & Tornado chart evaluation
 * POST /api/v1/valuation/sensitivity/tornado
 * 
 * @param {Object} payload - SensitivityRequest
 * @returns {Promise<Object>} SensitivityResponse
 */
export async function runSensitivityAnalysis(payload) {
  return await httpClient.post('/valuation/sensitivity/tornado', payload)
}

/**
 * Run real-time stress testing with interactive slider shocks
 * POST /api/v1/valuation/stress-test
 * 
 * @param {Object} payload - StressTestRequest
 * @returns {Promise<Object>} StressTestResponse
 */
export async function runStressTest(payload) {
  return await httpClient.post('/valuation/stress-test', payload)
}

/**
 * Simulate visual node-based contract graph DAG
 * POST /api/v1/contracts/simulate-graph
 * 
 * @param {Object} payload - ContractGraphPayload
 * @returns {Promise<Object>} SimulateGraphResponse
 */
export async function simulateContractGraph(payload) {
  return await httpClient.post('/contracts/simulate-graph', payload)
}
