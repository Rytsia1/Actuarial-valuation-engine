import httpClient from './httpClient'

export const WorkflowStep = {
  PROJECT: 'project',
  CONTRACT: 'contract',
  BLUEPRINT: 'blueprint',
  ASSUMPTIONS: 'assumptions',
  VALIDATION: 'validation',
  RUNNING: 'running',
  RESULTS: 'results'
}

export const workflowApi = {
  start: (name, description = '') =>
    httpClient.post('/workflow/start', { name, description }),

  getState: (projectId) =>
    httpClient.get(`/workflow/${projectId}/state`),

  addContract: (projectId, name, productType, blueprintJson = null) =>
    httpClient.post(`/workflow/${projectId}/contract`, { name, product_type: productType, blueprint_json: blueprintJson }),

  setAssumptions: (projectId, name, assumptions) =>
    httpClient.post(`/workflow/${projectId}/assumptions`, { name, assumptions }),

  runValuation: (projectId) =>
    httpClient.post(`/workflow/${projectId}/run`)
}
