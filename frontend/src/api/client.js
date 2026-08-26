/**
 * Actuarial Engine API Client
 * Connects the Vue frontend to the FastAPI valuation backend.
 */

const API_BASE = '/api/v1';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchTableMetadata() {
  const res = await fetch(`${API_BASE}/tables/soa_ilt`);
  if (!res.ok) throw new Error(`Failed to load table metadata: ${res.statusText}`);
  return await res.json();
}

export async function runDeterministicValuation(payload) {
  const res = await fetch(`${API_BASE}/valuation/deterministic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Deterministic valuation failed (${res.status})`);
  }
  return await res.json();
}

export async function runStochasticValuation(payload) {
  const res = await fetch(`${API_BASE}/valuation/stochastic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Stochastic valuation failed (${res.status})`);
  }
  return await res.json();
}
