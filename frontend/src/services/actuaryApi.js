/**
 * Actuarial Engine API Service
 * Decoupled HTTP client connecting Vue 3 components directly to FastAPI backend endpoints.
 */

// Base URL defaults to relative path (using Vite dev proxy) or configured environment variable
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = BASE_URL ? `${BASE_URL}/api/v1` : '/api/v1';

/**
 * Custom Actuarial API Error with status codes and structured details
 */
export class ActuaryApiError extends Error {
  constructor(message, status = null, details = null) {
    super(message);
    this.name = 'ActuaryApiError';
    this.status = status;
    this.details = details;
  }
}

/**
 * Generic request helper with robust error handling for connection & validation issues
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

  const defaultHeaders = {
    'Accept': 'application/json',
  };
  if (!isFormData) {
    defaultHeaders['Content-Type'] = 'application/json';
  }
  
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      let errorData = null;
      
      try {
        errorData = await res.json();
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            // Pydantic 422 validation errors array
            errorDetail = errorData.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
          } else {
            errorDetail = String(errorData.detail);
          }
        }
      } catch {
        // Fallback if response is not JSON
      }

      throw new ActuaryApiError(errorDetail, res.status, errorData);
    }

    return await res.json();
  } catch (err) {
    if (err instanceof ActuaryApiError) {
      throw err;
    }
    // Network errors (e.g. ECONNREFUSED when backend is down)
    throw new ActuaryApiError(
      `Cannot connect to FastAPI backend at ${API_BASE}. Ensure the server is running with 'uvicorn actuary_engine.api.main:app --port 8000'.`,
      0,
      err
    );
  }
}

/**
 * Health check endpoint
 * GET /api/v1/health
 */
export async function checkHealth() {
  return await apiRequest('/health');
}

/**
 * List all available mortality tables (built-in and custom uploaded)
 * GET /api/v1/tables
 */
export async function fetchTables() {
  return await apiRequest('/tables');
}

/**
 * Upload custom mortality table file (CSV or XTbML)
 * POST /api/v1/tables/upload
 * 
 * @param {FormData} formData - Contains 'file', 'table_name', 'table_description'
 * @returns {Promise<Object>} TableUploadResponse
 */
export async function uploadMortalityTable(formData) {
  return await apiRequest('/tables/upload', {
    method: 'POST',
    body: formData,
  });
}

/**
 * Delete a custom mortality table
 * DELETE /api/v1/tables/{table_id}
 */
export async function deleteMortalityTable(tableId) {
  return await apiRequest(`/tables/${tableId}`, {
    method: 'DELETE',
  });
}

/**
 * SOA Illustrative Life Table metadata
 * GET /api/v1/tables/soa_ilt
 */
export async function fetchTableMetadata() {
  return await apiRequest('/tables/soa_ilt');
}

/**
 * Run deterministic valuation: net level premium, prospective/retrospective reserves, and GPV rollout
 * POST /api/v1/valuation/deterministic
 * 
 * @param {Object} payload - { product_type, issue_age, term, sum_assured, interest_rate, gross_premium, table_id, expense, lapse }
 * @returns {Promise<Object>} DeterministicValuationResponse
 */
export async function runDeterministicValuation(payload) {
  return await apiRequest('/valuation/deterministic', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Run stochastic valuation: Vasicek ESG, dynamic S-curve lapses, Monte Carlo liability distribution, and VaR/CVaR
 * POST /api/v1/valuation/stochastic
 * 
 * @param {Object} payload - { product_type, issue_age, term, sum_assured, gross_premium, table_id, vasicek, dynamic_lapse, expense, n_scenarios, seed }
 * @returns {Promise<Object>} StochasticValuationResponse
 */
export async function runStochasticValuation(payload) {
  return await apiRequest('/valuation/stochastic', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Enqueue large-scale asynchronous stochastic simulation job
 * POST /api/v1/valuation/stochastic/async
 *
 * @param {Object} payload - StochasticValuationRequest
 * @returns {Promise<Object>} { job_id, status, total_paths, ws_endpoint }
 */
export async function startAsyncStochasticValuation(payload) {
  return await apiRequest('/valuation/stochastic/async', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Poll job status and retrieve final result when complete
 * GET /api/v1/valuation/stochastic/status/{job_id}
 *
 * @param {string} jobId - Simulation job identifier
 * @returns {Promise<Object>} AsyncJobStatusResponse
 */
export async function getStochasticJobStatus(jobId) {
  return await apiRequest(`/valuation/stochastic/status/${jobId}`);
}

/**
 * Upload portfolio CSV file for seriatim batch valuation
 * POST /api/v1/valuation/portfolio/csv
 *
 * @param {FormData} formData - Multipart form data with 'file' and optional params
 * @returns {Promise<Object>} PortfolioValuationResponse
 */
export async function uploadPortfolioCSV(formData) {
  return await apiRequest('/valuation/portfolio/csv', {
    method: 'POST',
    body: formData,
  });
}

/**
 * Run portfolio batch valuation from JSON records
 * POST /api/v1/valuation/portfolio
 *
 * @param {Object} payload - { policies: Array, interest_rate: Number, table_id: String, expense: Object, lapse: Object }
 * @returns {Promise<Object>} PortfolioValuationResponse
 */
export async function evaluatePortfolioJSON(payload) {
  return await apiRequest('/valuation/portfolio', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Download sample synthetic CSV URL
 * GET /api/v1/valuation/portfolio/sample_csv
 */
export function getSamplePortfolioCSVUrl(nPolicies = 1000) {
  return `${API_BASE}/valuation/portfolio/sample_csv?n_policies=${nPolicies}`;
}

/**
 * Run IFRS 17 / PSAK 117 General Measurement Model (BBA) valuation
 * POST /api/v1/valuation/ifrs17
 *
 * @param {Object} payload - IFRS17ValuationRequest
 * @returns {Promise<Object>} IFRS17ValuationResponse
 */
export async function runIFRS17Valuation(payload) {
  return await apiRequest('/valuation/ifrs17', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Run multi-model Economic Scenario Generator simulation (Hull-White 1F, CIR, Vasicek)
 * POST /api/v1/esg/simulate
 *
 * @param {Object} payload - ESGSimulationRequest
 * @returns {Promise<Object>} ESGSimulationResponse
 */
export async function simulateESG(payload) {
  return await apiRequest('/esg/simulate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Run stress testing and Tornado sensitivity analysis
 * POST /api/v1/valuation/sensitivity/tornado
 *
 * @param {Object} payload - SensitivityRequest
 * @returns {Promise<Object>} SensitivityResponse
 */
export async function runSensitivityAnalysis(payload) {
  return await apiRequest('/valuation/sensitivity/tornado', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}



