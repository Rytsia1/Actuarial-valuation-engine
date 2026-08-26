<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  checkHealth,
  fetchTables,
  uploadMortalityTable,
  deleteMortalityTable,
  runDeterministicValuation,
  runIFRS17Valuation,
  runSensitivityAnalysis,
  startAsyncStochasticValuation,
  getStochasticJobStatus,
  runStochasticValuation,
  uploadPortfolioCSV,
  getSamplePortfolioCSVUrl,
  ActuaryApiError,
} from './services/actuaryApi'
import { connectSimulationSocket } from './services/simulationSocket'

// ────────────────────────────────────────────────────────────
// Reactive Dashboard State
// ────────────────────────────────────────────────────────────

const activeTab = ref('overview') // 'overview', 'sensitivity', 'ifrs17', 'portfolio', 'reserves', 'stochastic', 'cashflows', 'table'
const backendStatus = ref('checking') // 'healthy', 'error', 'checking'
const loading = ref(false)
const errorMessage = ref(null)
const backendDetails = ref(null)

// Mortality Table Registry State
const availableTables = ref([])
const showTableModal = ref(false)
const uploadTableLoading = ref(false)
const uploadTableError = ref(null)
const uploadTableName = ref('')
const uploadTableDesc = ref('')
const uploadTableFile = ref(null)
const isTableDragging = ref(false)

// Simulation Progress Tracking
const isSimulating = ref(false)
const simProgress = ref(0)
const completedPaths = ref(0)
const totalPaths = ref(0)
const partialMetrics = ref(null)
let activeSocketConnection = null

// Portfolio Batch State
const portfolioLoading = ref(false)
const portfolioError = ref(null)
const portfolioData = ref(null)
const portfolioInterestRate = ref(0.05)
const isDragging = ref(false)

// IFRS 17 State
const ifrs17Data = ref(null)
const ifrs17Loading = ref(false)

// Sensitivity & Stress State
const sensitivityData = ref(null)
const sensitivityLoading = ref(false)

// Form Parameters with standard actuarial defaults
const form = reactive({
  product_type: 'endowment',
  issue_age: 30,
  term: 20,
  sum_assured: 1000000,
  premium_paying_term: null,
  interest_rate: 0.05,
  gross_premium: null,
  table_id: 'soa_ilt',
  ra_ratio: 0.06,
  expense: {
    percent_of_premium_first: 0.35,
    percent_of_premium_renewal: 0.05,
    per_policy_first: 200.0,
    per_policy_renewal: 20.0,
  },
  lapse: {
    duration_rates: [0.08, 0.05, 0.04, 0.03],
    flat_annual_rate: 0.02,
  },
  vasicek: {
    r0: 0.05,
    kappa: 0.20,
    theta: 0.05,
    sigma: 0.015,
  },
  enable_dynamic_lapse: true,
  dynamic_lapse: {
    base_lapse_rate: 0.04,
    credited_rate: 0.04,
    min_lapse_rate: 0.01,
    max_lapse_rate: 0.35,
    sensitivity: 25.0,
    spread_threshold: 0.0,
  },
  n_scenarios: 5000,
  seed: 42,
})

// Valuation Results from FastAPI
const deterministicData = ref(null)
const stochasticData = ref(null)

// Chart DOM refs & instances
const heroChartRef = ref(null)
const reserveChartRef = ref(null)
const fanChartRef = ref(null)
const cashFlowChartRef = ref(null)
const distChartRef = ref(null)
const portfolioCfChartRef = ref(null)
const portfolioProdChartRef = ref(null)
const portfolioAgeChartRef = ref(null)
const ifrs17LrcChartRef = ref(null)
const ifrs17PnlChartRef = ref(null)
const tornadoChartRef = ref(null)

let heroChart = null
let reserveChart = null
let fanChart = null
let cashFlowChart = null
let distChart = null
let portfolioCfChart = null
let portfolioProdChart = null
let portfolioAgeChart = null
let ifrs17LrcChart = null
let ifrs17PnlChart = null
let tornadoChart = null
let resizeObserver = null

// ────────────────────────────────────────────────────────────
// Formatting Helpers
// ────────────────────────────────────────────────────────────

function formatCurrency(val) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val)
}

function formatNumber(val, decimals = 2) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  return Number(val).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// ────────────────────────────────────────────────────────────
// Preset Contract Loaders
// ────────────────────────────────────────────────────────────

function applyPreset(type) {
  if (type === 'endowment_20') {
    form.product_type = 'endowment'
    form.issue_age = 30
    form.term = 20
    form.sum_assured = 1000000
    form.interest_rate = 0.05
    form.vasicek.sigma = 0.015
    form.enable_dynamic_lapse = true
  } else if (type === 'term_30') {
    form.product_type = 'term'
    form.issue_age = 35
    form.term = 30
    form.sum_assured = 750000
    form.interest_rate = 0.045
    form.vasicek.sigma = 0.02
    form.enable_dynamic_lapse = true
  } else if (type === 'whole_life') {
    form.product_type = 'whole_life'
    form.issue_age = 40
    form.term = null
    form.sum_assured = 500000
    form.interest_rate = 0.05
    form.vasicek.sigma = 0.012
    form.enable_dynamic_lapse = false
  } else if (type === 'large_scale_10k') {
    form.product_type = 'endowment'
    form.issue_age = 30
    form.term = 20
    form.sum_assured = 1000000
    form.n_scenarios = 10000
    form.vasicek.sigma = 0.02
    form.enable_dynamic_lapse = true
  }
  executeValuation()
}

// ────────────────────────────────────────────────────────────
// API Communication & Valuation Orchestrator
// ────────────────────────────────────────────────────────────

async function loadTableCatalogue() {
  try {
    const tables = await fetchTables()
    availableTables.value = tables
    if (tables.length > 0 && !availableTables.value.some(t => t.table_id === form.table_id)) {
      form.table_id = tables[0].table_id
    }
  } catch (err) {
    console.warn('Failed to load table catalogue:', err)
  }
}

async function checkBackendConnection() {
  try {
    const health = await checkHealth()
    backendStatus.value = health.status === 'healthy' ? 'healthy' : 'error'
    backendDetails.value = health
    await loadTableCatalogue()
    return true
  } catch (err) {
    console.warn('Backend health check error:', err)
    backendStatus.value = 'error'
    return false
  }
}

async function executeValuation() {
  loading.value = true
  errorMessage.value = null

  if (activeSocketConnection) {
    activeSocketConnection.close()
    activeSocketConnection = null
  }

  isSimulating.value = true
  simProgress.value = 0
  completedPaths.value = 0
  totalPaths.value = form.n_scenarios
  partialMetrics.value = null

  try {
    const detPayload = {
      product_type: form.product_type,
      issue_age: form.issue_age,
      term: form.product_type === 'whole_life' ? null : form.term,
      sum_assured: form.sum_assured,
      premium_paying_term: form.premium_paying_term,
      interest_rate: form.interest_rate,
      gross_premium: form.gross_premium,
      table_id: form.table_id,
      expense: form.expense,
      lapse: form.lapse,
    }

    const stochPayload = {
      product_type: form.product_type,
      issue_age: form.issue_age,
      term: form.product_type === 'whole_life' ? null : form.term,
      sum_assured: form.sum_assured,
      premium_paying_term: form.premium_paying_term,
      gross_premium: form.gross_premium,
      table_id: form.table_id,
      vasicek: form.vasicek,
      dynamic_lapse: form.enable_dynamic_lapse ? form.dynamic_lapse : null,
      expense: form.expense,
      n_scenarios: form.n_scenarios,
      seed: form.seed,
    }

    const ifrs17Payload = {
      ...detPayload,
      ra_ratio: form.ra_ratio,
    }

    const sensPayload = {
      ...detPayload,
    }

    const detPromise = runDeterministicValuation(detPayload)
    const ifrs17Promise = runIFRS17Valuation(ifrs17Payload)
    const sensPromise = runSensitivityAnalysis(sensPayload)

    const asyncJobPromise = new Promise(async (resolve, reject) => {
      try {
        const jobRes = await startAsyncStochasticValuation(stochPayload)
        const jobId = jobRes.job_id

        activeSocketConnection = connectSimulationSocket(jobId, {
          onProgress: (prog) => {
            simProgress.value = prog.percent
            completedPaths.value = prog.completed_paths
            totalPaths.value = prog.total_paths
            if (prog.partial_metrics) {
              partialMetrics.value = prog.partial_metrics
            }
          },
          onComplete: (data) => {
            simProgress.value = 100
            completedPaths.value = totalPaths.value
            isSimulating.value = false
            resolve(data)
          },
          onError: async (err) => {
            console.warn('WebSocket error, falling back to HTTP polling:', err)
            try {
              let attempts = 0
              while (attempts < 60) {
                await new Promise(r => setTimeout(r, 250))
                const statusRes = await getStochasticJobStatus(jobId)
                simProgress.value = statusRes.progress
                completedPaths.value = statusRes.completed_paths
                if (statusRes.status === 'COMPLETED' && statusRes.result) {
                  isSimulating.value = false
                  resolve(statusRes.result)
                  return
                } else if (statusRes.status === 'FAILED') {
                  throw new Error(statusRes.error || 'Async simulation failed')
                }
                attempts++
              }
              throw new Error('Simulation polling timed out')
            } catch (pollErr) {
              reject(pollErr)
            }
          },
        })
      } catch (err) {
        try {
          const syncRes = await runStochasticValuation(stochPayload)
          simProgress.value = 100
          completedPaths.value = form.n_scenarios
          isSimulating.value = false
          resolve(syncRes)
        } catch (syncErr) {
          reject(syncErr)
        }
      }
    })

    const [detRes, stochRes, ifrs17Res, sensRes] = await Promise.all([
      detPromise,
      asyncJobPromise,
      ifrs17Promise,
      sensPromise,
    ])

    deterministicData.value = detRes
    stochasticData.value = stochRes
    ifrs17Data.value = ifrs17Res
    sensitivityData.value = sensRes
    backendStatus.value = 'healthy'

    await nextTick()
    renderAllCharts()
  } catch (err) {
    console.error('Valuation execution error:', err)
    backendStatus.value = 'error'
    if (err instanceof ActuaryApiError) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = err.message || 'Failed to complete actuarial valuation.'
    }
  } finally {
    loading.value = false
    isSimulating.value = false
  }
}

// ────────────────────────────────────────────────────────────
// Custom Mortality Table Upload
// ────────────────────────────────────────────────────────────

function handleTableFileSelect(event) {
  uploadTableFile.value = event.target.files?.[0] || null
}

function handleTableFileDrop(event) {
  isTableDragging.value = false
  uploadTableFile.value = event.dataTransfer?.files?.[0] || null
}

async function submitCustomTable() {
  if (!uploadTableFile.value) {
    uploadTableError.value = 'Please select a mortality table file (.csv, .xml, .xtbml).'
    return
  }

  uploadTableLoading.value = true
  uploadTableError.value = null

  try {
    const formData = new FormData()
    formData.append('file', uploadTableFile.value)
    if (uploadTableName.value) formData.append('table_name', uploadTableName.value)
    if (uploadTableDesc.value) formData.append('table_description', uploadTableDesc.value)

    const res = await uploadMortalityTable(formData)
    await loadTableCatalogue()
    form.table_id = res.table_id

    showTableModal.value = false
    uploadTableFile.value = null
    uploadTableName.value = ''
    uploadTableDesc.value = ''

    await executeValuation()
  } catch (err) {
    console.error('Table upload error:', err)
    uploadTableError.value = err.message || 'Failed to upload mortality table.'
  } finally {
    uploadTableLoading.value = false
  }
}

// ────────────────────────────────────────────────────────────
// Portfolio Batch Upload & Processing
// ────────────────────────────────────────────────────────────

async function handlePortfolioFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  await processPortfolioFile(file)
}

function handlePortfolioDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  processPortfolioFile(file)
}

async function processPortfolioFile(file) {
  portfolioLoading.value = true
  portfolioError.value = null

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('interest_rate', portfolioInterestRate.value)
    formData.append('table_id', form.table_id)

    const res = await uploadPortfolioCSV(formData)
    portfolioData.value = res
    activeTab.value = 'portfolio'

    await nextTick()
    renderPortfolioCharts()
  } catch (err) {
    console.error('Portfolio valuation error:', err)
    portfolioError.value = err.message || 'Portfolio CSV valuation failed.'
  } finally {
    portfolioLoading.value = false
  }
}

async function runSamplePortfolioDemo(nPolicies = 1000) {
  portfolioLoading.value = true
  portfolioError.value = null

  try {
    const url = getSamplePortfolioCSVUrl(nPolicies)
    const fetchRes = await fetch(url)
    const blob = await fetchRes.blob()
    const file = new File([blob], `sample_portfolio_${nPolicies}.csv`, { type: 'text/csv' })
    await processPortfolioFile(file)
  } catch (err) {
    console.error('Demo portfolio error:', err)
    portfolioError.value = err.message || 'Failed to run demo portfolio.'
    portfolioLoading.value = false
  }
}

// ────────────────────────────────────────────────────────────
// ECharts Render Functions (Dark Neon Theme)
// ────────────────────────────────────────────────────────────

function renderHeroChart() {
  if (!heroChartRef.value || !deterministicData.value?.cash_flows) return
  if (!heroChart) heroChart = echarts.init(heroChartRef.value)

  const cfs = deterministicData.value.cash_flows
  const years = cfs.map(d => `Yr ${d.year + 1}`)
  const netCfs = cfs.map(d => d.net_liability_cf)

  let running = 0
  const cumLiability = cfs.map(d => {
    running += d.net_liability_cf
    return running
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11, 15, 25, 0.95)',
      borderColor: 'rgba(236, 72, 153, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
    },
    grid: { top: 30, left: 65, right: 25, bottom: 35 },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(years.length / 10)) },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
    series: [
      {
        name: 'Annual Net Liability CF',
        type: 'bar',
        data: netCfs,
        barWidth: '60%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#f43f5e' },
            { offset: 0.5, color: '#fb923c' },
            { offset: 1, color: '#ec4899' },
          ]),
          shadowColor: 'rgba(244, 63, 94, 0.4)',
          shadowBlur: 8,
        },
      },
      {
        name: 'Cumulative Liability',
        type: 'line',
        data: cumLiability,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.5, color: '#38bdf8', shadowColor: 'rgba(56, 189, 248, 0.5)', shadowBlur: 10 },
      },
    ],
  }
  heroChart.setOption(option, true)
}

function renderReserveChart() {
  if (!reserveChartRef.value || !deterministicData.value?.reserve_profile) return
  if (!reserveChart) reserveChart = echarts.init(reserveChartRef.value)

  const profile = deterministicData.value.reserve_profile
  const durations = profile.map(r => `t=${r.duration} (Age ${r.age})`)
  const prospective = profile.map(r => r.reserve_prospective)
  const retrospective = profile.map(r => r.reserve_retrospective)
  const gross = profile.map(r => r.gross_reserve)

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: 'rgba(56, 189, 248, 0.3)', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
    legend: { data: ['Prospective Reserve (_t V)', 'Retrospective Reserve (_t V_retro)', 'Gross GPV Reserve'], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 0, right: 10 },
    grid: { top: 40, left: 65, right: 25, bottom: 35 },
    xAxis: { type: 'category', data: durations, boundaryGap: false, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(durations.length / 8)) }, splitLine: { show: true, lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } } },
    series: [
      {
        name: 'Prospective Reserve (_t V)',
        type: 'line',
        data: prospective,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2.5, color: '#38bdf8', shadowColor: 'rgba(56, 189, 248, 0.5)', shadowBlur: 10 },
        itemStyle: { color: '#38bdf8' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(56, 189, 248, 0.28)' }, { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }]) },
      },
      { name: 'Retrospective Reserve (_t V_retro)', type: 'line', data: retrospective, smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: '#34d399', type: 'dashed' }, itemStyle: { color: '#34d399' } },
      { name: 'Gross GPV Reserve', type: 'line', data: gross, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#fb923c' }, itemStyle: { color: '#fb923c' } },
    ],
  }
  reserveChart.setOption(option, true)
}

function renderFanChart() {
  if (!fanChartRef.value || (!stochasticData.value?.quantiles && !stochasticData.value?.fan_chart_rates)) return
  if (!fanChart) fanChart = echarts.init(fanChartRef.value)

  let years = []
  let p5 = []
  let p25 = []
  let p50 = []
  let p75 = []
  let p95 = []
  let mean = []

  if (stochasticData.value.quantiles) {
    const q = stochasticData.value.quantiles
    const timesteps = stochasticData.value.timesteps || q.p50.map((_, i) => i)
    years = timesteps.map(t => `t=${t}`)
    p5 = q.p5.map(v => (v * 100).toFixed(2))
    p25 = q.p25.map(v => (v * 100).toFixed(2))
    p50 = q.p50.map(v => (v * 100).toFixed(2))
    p75 = q.p75.map(v => (v * 100).toFixed(2))
    p95 = q.p95.map(v => (v * 100).toFixed(2))
    mean = p50
  } else {
    const rates = stochasticData.value.fan_chart_rates
    years = rates.map(d => `t=${d.year}`)
    p5 = rates.map(d => (d.p5 * 100).toFixed(2))
    p25 = rates.map(d => (d.p25 * 100).toFixed(2))
    p50 = rates.map(d => (d.p50 * 100).toFixed(2))
    p75 = rates.map(d => (d.p75 * 100).toFixed(2))
    p95 = rates.map(d => (d.p95 * 100).toFixed(2))
    mean = rates.map(d => (d.mean * 100).toFixed(2))
  }

  const sampleSeries = (stochasticData.value.sample_paths || []).slice(0, 10).map((path, idx) => ({
    name: `Trace ${idx + 1}`,
    type: 'line',
    data: path.map(r => (r * 100).toFixed(2)),
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 0.8, color: 'rgba(255, 255, 255, 0.15)' },
    silent: true,
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: 'rgba(168, 85, 247, 0.3)', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
    legend: { data: ['95% Upper Bound', 'Median (p50)', '5% Lower Bound'], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 0, right: 10 },
    grid: { top: 40, left: 55, right: 25, bottom: 35 },
    xAxis: { type: 'category', data: years, boundaryGap: false, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(years.length / 8)) }, splitLine: { show: true, lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `${v}%` }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } } },
    series: [
      ...sampleSeries,
      { name: '95% Upper Bound', type: 'line', data: p95, smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: '#f43f5e' }, areaStyle: { color: 'rgba(244, 63, 94, 0.12)' } },
      { name: 'p75', type: 'line', data: p75, smooth: true, symbol: 'none', lineStyle: { width: 1, color: 'rgba(236, 72, 153, 0.5)' }, areaStyle: { color: 'rgba(236, 72, 153, 0.16)' } },
      { name: 'Median (p50)', type: 'line', data: p50, smooth: true, symbol: 'none', lineStyle: { width: 2.5, color: '#38bdf8', shadowColor: 'rgba(56, 189, 248, 0.6)', shadowBlur: 8 } },
      { name: 'p25', type: 'line', data: p25, smooth: true, symbol: 'none', lineStyle: { width: 1, color: 'rgba(236, 72, 153, 0.5)' } },
      { name: '5% Lower Bound', type: 'line', data: p5, smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: '#a855f7' } },
    ],
  }
  fanChart.setOption(option, true)
}

function renderCashFlowChart() {
  if (!cashFlowChartRef.value || !deterministicData.value?.cash_flows) return
  if (!cashFlowChart) cashFlowChart = echarts.init(cashFlowChartRef.value)

  const cfs = deterministicData.value.cash_flows
  const years = cfs.map(d => `Yr ${d.year + 1}`)
  const premiums = cfs.map(d => d.premium_income)
  const claims = cfs.map(d => d.death_claims + d.maturity_benefit)
  const expenses = cfs.map(d => d.total_expense)

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: '#334155', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
    legend: { data: ['Premium Income', 'Claims & Benefits', 'Expenses'], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 0, right: 10 },
    grid: { top: 40, left: 65, right: 25, bottom: 35 },
    xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(years.length / 8)) } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } } },
    series: [
      { name: 'Premium Income', type: 'bar', data: premiums, itemStyle: { color: '#34d399', borderRadius: [3, 3, 0, 0] } },
      { name: 'Claims & Benefits', type: 'bar', data: claims, itemStyle: { color: '#f43f5e', borderRadius: [3, 3, 0, 0] } },
      { name: 'Expenses', type: 'bar', data: expenses, itemStyle: { color: '#fb923c', borderRadius: [3, 3, 0, 0] } },
    ],
  }
  cashFlowChart.setOption(option, true)
}

function renderDistChart() {
  if (!distChartRef.value || (!stochasticData.value?.terminal_distribution && !stochasticData.value?.liability_histogram)) return
  if (!distChart) distChart = echarts.init(distChartRef.value)

  let bins = []
  let counts = []
  const var95 = stochasticData.value.var_95 || stochasticData.value.terminal_distribution?.var_95 || 0

  if (stochasticData.value.terminal_distribution) {
    const td = stochasticData.value.terminal_distribution
    const binEdges = td.bin_edges
    counts = td.counts.map((c, i) => {
      const mid = (binEdges[i] + binEdges[i + 1]) / 2.0
      return {
        value: c,
        itemStyle: {
          color: mid >= var95 ? '#f43f5e' : '#a855f7',
          shadowColor: mid >= var95 ? 'rgba(244, 63, 94, 0.4)' : 'rgba(168, 85, 247, 0.3)',
          shadowBlur: 6,
        },
      }
    })
    bins = td.counts.map((_, i) => `$${((binEdges[i] + binEdges[i + 1]) / 2000.0).toFixed(1)}k`)
  } else {
    const hist = stochasticData.value.liability_histogram
    bins = hist.map(d => `$${(d.bin_mid / 1000).toFixed(1)}k`)
    counts = hist.map(d => ({
      value: d.count,
      itemStyle: {
        color: d.bin_mid >= var95 ? '#f43f5e' : '#a855f7',
        shadowColor: d.bin_mid >= var95 ? 'rgba(244, 63, 94, 0.4)' : 'rgba(168, 85, 247, 0.3)',
        shadowBlur: 6,
      },
    }))
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: '#334155', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
    grid: { top: 30, left: 55, right: 25, bottom: 35 },
    xAxis: { type: 'category', data: bins, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(bins.length / 8)) } },
    yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } } },
    series: [{ name: 'Scenarios', type: 'bar', data: counts, barWidth: '85%', itemStyle: { borderRadius: [3, 3, 0, 0] } }],
  }
  distChart.setOption(option, true)
}

function renderPortfolioCharts() {
  if (!portfolioData.value) return

  // 1. Portfolio Aggregate Cash Flow Chart
  if (portfolioCfChartRef.value && portfolioData.value.annual_cash_flows) {
    if (!portfolioCfChart) portfolioCfChart = echarts.init(portfolioCfChartRef.value)
    const cfs = portfolioData.value.annual_cash_flows
    const years = cfs.map(d => `Yr ${d.year}`)
    const premiums = cfs.map(d => d.premium_income)
    const claims = cfs.map(d => d.death_claims + d.maturity_benefits)
    const expenses = cfs.map(d => d.total_expenses)
    const netLiability = cfs.map(d => d.net_liability_cf)

    const cfOption = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: '#334155', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
      legend: { data: ['Premium Inflows', 'Claims & Maturities', 'Expenses', 'Net Liability CF'], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 0, right: 10 },
      grid: { top: 40, left: 75, right: 25, bottom: 35 },
      xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(years.length / 10)) } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1_000_000).toFixed(1)}M` }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } } },
      series: [
        { name: 'Premium Inflows', type: 'bar', stack: 'inflow', data: premiums, itemStyle: { color: '#34d399', borderRadius: [2, 2, 0, 0] } },
        { name: 'Claims & Maturities', type: 'bar', stack: 'outflow', data: claims, itemStyle: { color: '#f43f5e', borderRadius: [2, 2, 0, 0] } },
        { name: 'Expenses', type: 'bar', stack: 'outflow', data: expenses, itemStyle: { color: '#fb923c', borderRadius: [2, 2, 0, 0] } },
        { name: 'Net Liability CF', type: 'line', data: netLiability, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#38bdf8' } },
      ],
    }
    portfolioCfChart.setOption(cfOption, true)
  }

  // 2. Product Breakdown Donut Chart
  if (portfolioProdChartRef.value && portfolioData.value.product_breakdown) {
    if (!portfolioProdChart) portfolioProdChart = echarts.init(portfolioProdChartRef.value)
    const prodEntries = Object.entries(portfolioData.value.product_breakdown).map(([k, v]) => ({
      name: k.replace('_', ' ').toUpperCase(),
      value: v.sum_assured,
    }))

    const prodOption = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: '#334155', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
      legend: { orient: 'vertical', left: 'left', top: 'middle', textStyle: { color: '#94a3b8', fontSize: 11 } },
      series: [
        {
          name: 'Face Amount Share',
          type: 'pie',
          radius: ['45%', '75%'],
          center: ['65%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 6, borderColor: '#0b0f19', borderWidth: 2 },
          label: { show: false },
          data: prodEntries,
          color: ['#38bdf8', '#ec4899', '#34d399', '#fb923c'],
        },
      ],
    }
    portfolioProdChart.setOption(prodOption, true)
  }

  // 3. Age Cohort Distribution Bar Chart
  if (portfolioAgeChartRef.value && portfolioData.value.age_breakdown) {
    if (!portfolioAgeChart) portfolioAgeChart = echarts.init(portfolioAgeChartRef.value)
    const ageEntries = Object.entries(portfolioData.value.age_breakdown)
    const categories = ageEntries.map(([k]) => k)
    const counts = ageEntries.map(([, v]) => v.count)
    const bels = ageEntries.map(([, v]) => v.bel)

    const ageOption = {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(11, 15, 25, 0.95)', borderColor: '#334155', textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' } },
      legend: { data: ['Policy Count', 'Net BEL'], textStyle: { color: '#94a3b8', fontSize: 11 }, top: 0, right: 10 },
      grid: { top: 40, left: 65, right: 55, bottom: 35 },
      xAxis: { type: 'category', data: categories, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 11, fontFamily: 'JetBrains Mono' } },
      yAxis: [
        { type: 'value', name: 'Count', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } } },
        { type: 'value', name: 'BEL ($)', axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: { show: false } },
      ],
      series: [
        { name: 'Policy Count', type: 'bar', data: counts, itemStyle: { color: '#a855f7', borderRadius: [4, 4, 0, 0] } },
        { name: 'Net BEL', type: 'line', yAxisIndex: 1, data: bels, smooth: true, itemStyle: { color: '#f43f5e' } },
      ],
    }
    portfolioAgeChart.setOption(ageOption, true)
  }
}

function renderIFRS17Charts() {
  if (!ifrs17Data.value) return

  // 1. Stacked Area Chart (LRC Transition: BEL + RA + CSM)
  if (ifrs17LrcChartRef.value && ifrs17Data.value.balance_sheet_schedule) {
    if (!ifrs17LrcChart) ifrs17LrcChart = echarts.init(ifrs17LrcChartRef.value)
    const schedule = ifrs17Data.value.balance_sheet_schedule
    const durations = schedule.map(d => `t=${d.duration}`)
    const bels = schedule.map(d => d.bel)
    const ras = schedule.map(d => d.risk_adjustment)
    const csms = schedule.map(d => d.csm)
    const lrcs = schedule.map(d => d.total_lrc)

    const lrcOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(11, 15, 25, 0.95)',
        borderColor: 'rgba(236, 72, 153, 0.3)',
        textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
      },
      legend: {
        data: ['Best Estimate Liability (BEL)', 'Risk Adjustment (RA)', 'Contractual Service Margin (CSM)', 'Total LRC'],
        textStyle: { color: '#94a3b8', fontSize: 11 },
        top: 0,
        right: 10,
      },
      grid: { top: 40, left: 65, right: 25, bottom: 35 },
      xAxis: {
        type: 'category',
        data: durations,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(durations.length / 8)) },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      },
      series: [
        {
          name: 'Best Estimate Liability (BEL)',
          type: 'line',
          stack: 'Total',
          data: bels,
          areaStyle: { color: 'rgba(56, 189, 248, 0.35)' },
          lineStyle: { width: 1.5, color: '#38bdf8' },
          itemStyle: { color: '#38bdf8' },
          symbol: 'none',
        },
        {
          name: 'Risk Adjustment (RA)',
          type: 'line',
          stack: 'Total',
          data: ras,
          areaStyle: { color: 'rgba(251, 146, 60, 0.45)' },
          lineStyle: { width: 1.5, color: '#fb923c' },
          itemStyle: { color: '#fb923c' },
          symbol: 'none',
        },
        {
          name: 'Contractual Service Margin (CSM)',
          type: 'line',
          stack: 'Total',
          data: csms,
          areaStyle: { color: 'rgba(236, 72, 153, 0.45)' },
          lineStyle: { width: 2, color: '#ec4899' },
          itemStyle: { color: '#ec4899' },
          symbol: 'none',
        },
        {
          name: 'Total LRC',
          type: 'line',
          data: lrcs,
          smooth: true,
          lineStyle: { width: 2.5, color: '#ffffff', type: 'dashed' },
          itemStyle: { color: '#ffffff' },
          symbol: 'none',
        },
      ],
    }
    ifrs17LrcChart.setOption(lrcOption, true)
  }

  // 2. Income Statement Waterfall Chart (Revenue vs Claims vs Expenses vs CSM Release)
  if (ifrs17PnlChartRef.value && ifrs17Data.value.income_statement_schedule) {
    if (!ifrs17PnlChart) ifrs17PnlChart = echarts.init(ifrs17PnlChartRef.value)
    const pnl = ifrs17Data.value.income_statement_schedule
    const years = pnl.map(d => `Yr ${d.year + 1}`)
    const revs = pnl.map(d => d.insurance_revenue)
    const claims = pnl.map(d => d.claims_incurred)
    const expenses = pnl.map(d => d.expenses_incurred)
    const csmAmort = pnl.map(d => d.csm_amortization)
    const pnlResult = pnl.map(d => d.insurance_service_result)

    const pnlOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(11, 15, 25, 0.95)',
        borderColor: '#334155',
        textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
      },
      legend: {
        data: ['Insurance Revenue', 'Claims Incurred', 'Service Expenses', 'CSM Release', 'Service Result'],
        textStyle: { color: '#94a3b8', fontSize: 11 },
        top: 0,
        right: 10,
      },
      grid: { top: 40, left: 65, right: 25, bottom: 35 },
      xAxis: {
        type: 'category',
        data: years,
        axisLine: { lineStyle: { color: '#334155' } },
        axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(years.length / 8)) },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      },
      series: [
        { name: 'Insurance Revenue', type: 'bar', data: revs, itemStyle: { color: '#34d399', borderRadius: [3, 3, 0, 0] } },
        { name: 'Claims Incurred', type: 'bar', data: claims, itemStyle: { color: '#f43f5e', borderRadius: [3, 3, 0, 0] } },
        { name: 'Service Expenses', type: 'bar', data: expenses, itemStyle: { color: '#fb923c', borderRadius: [3, 3, 0, 0] } },
        { name: 'CSM Release', type: 'line', data: csmAmort, smooth: true, lineStyle: { width: 2, color: '#ec4899' }, itemStyle: { color: '#ec4899' } },
        { name: 'Service Result', type: 'line', data: pnlResult, smooth: true, lineStyle: { width: 2, color: '#38bdf8' }, itemStyle: { color: '#38bdf8' } },
      ],
    }
    ifrs17PnlChart.setOption(pnlOption, true)
  }
}

function renderTornadoChart() {
  if (!tornadoChartRef.value || !sensitivityData.value?.tornado_items) return
  if (!tornadoChart) tornadoChart = echarts.init(tornadoChartRef.value)

  // Inverted so largest swing is at top of y-axis
  const items = [...sensitivityData.value.tornado_items].reverse()
  const factors = items.map(d => d.risk_factor)
  const lowDeltas = items.map(d => d.low_delta)
  const highDeltas = items.map(d => d.high_delta)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(11, 15, 25, 0.95)',
      borderColor: 'rgba(244, 63, 94, 0.3)',
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const idx = params[0].dataIndex
        const item = items[idx]
        return `
          <div class="font-bold text-white mb-1">${item.risk_factor}</div>
          <div class="text-xs text-slate-300 font-mono space-y-1">
            <div><span class="text-emerald-400">Low Shock (${item.low_label}):</span> ${formatCurrency(item.low_delta)} (${item.low_delta_pct > 0 ? '+' : ''}${item.low_delta_pct}%)</div>
            <div><span class="text-rose-400">High Shock (${item.high_label}):</span> ${formatCurrency(item.high_delta)} (${item.high_delta_pct > 0 ? '+' : ''}${item.high_delta_pct}%)</div>
            <div class="border-t border-white/10 pt-1 text-fuchsia-300 font-bold">Total Delta Swing: ${formatCurrency(item.swing)} (${item.swing_pct}%)</div>
          </div>
        `
      },
    },
    legend: {
      data: ['Low Shock Delta (Downside)', 'High Shock Delta (Upside)'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: { top: 40, left: 240, right: 35, bottom: 25 },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `$${(v / 1000).toFixed(0)}k` },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.06)' } },
    },
    yAxis: {
      type: 'category',
      data: factors,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#cbd5e1', fontSize: 11, fontFamily: 'JetBrains Mono' },
      splitLine: { show: false },
    },
    series: [
      {
        name: 'Low Shock Delta (Downside)',
        type: 'bar',
        data: lowDeltas,
        itemStyle: {
          borderRadius: [4, 4, 4, 4],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#38bdf8' },
            { offset: 1, color: '#34d399' },
          ]),
        },
      },
      {
        name: 'High Shock Delta (Upside)',
        type: 'bar',
        data: highDeltas,
        itemStyle: {
          borderRadius: [4, 4, 4, 4],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#fb923c' },
            { offset: 1, color: '#f43f5e' },
          ]),
        },
      },
    ],
  }
  tornadoChart.setOption(option, true)
}

function renderAllCharts() {
  renderHeroChart()
  renderReserveChart()
  renderFanChart()
  renderCashFlowChart()
  renderDistChart()
  renderPortfolioCharts()
  renderIFRS17Charts()
  renderTornadoChart()
}

// ────────────────────────────────────────────────────────────
// Lifecycle Hooks
// ────────────────────────────────────────────────────────────

onMounted(async () => {
  await checkBackendConnection()
  await executeValuation()

  resizeObserver = new ResizeObserver(() => {
    heroChart?.resize()
    reserveChart?.resize()
    fanChart?.resize()
    cashFlowChart?.resize()
    distChart?.resize()
    portfolioCfChart?.resize()
    portfolioProdChart?.resize()
    portfolioAgeChart?.resize()
    ifrs17LrcChart?.resize()
    ifrs17PnlChart?.resize()
    tornadoChart?.resize()
  })

  if (heroChartRef.value) resizeObserver.observe(heroChartRef.value)
  if (reserveChartRef.value) resizeObserver.observe(reserveChartRef.value)
  if (fanChartRef.value) resizeObserver.observe(fanChartRef.value)
  if (cashFlowChartRef.value) resizeObserver.observe(cashFlowChartRef.value)
  if (distChartRef.value) resizeObserver.observe(distChartRef.value)
  if (portfolioCfChartRef.value) resizeObserver.observe(portfolioCfChartRef.value)
  if (portfolioProdChartRef.value) resizeObserver.observe(portfolioProdChartRef.value)
  if (portfolioAgeChartRef.value) resizeObserver.observe(portfolioAgeChartRef.value)
  if (ifrs17LrcChartRef.value) resizeObserver.observe(ifrs17LrcChartRef.value)
  if (ifrs17PnlChartRef.value) resizeObserver.observe(ifrs17PnlChartRef.value)
  if (tornadoChartRef.value) resizeObserver.observe(tornadoChartRef.value)
})

onUnmounted(() => {
  if (activeSocketConnection) {
    activeSocketConnection.close()
    activeSocketConnection = null
  }
  if (resizeObserver) resizeObserver.disconnect()
  heroChart?.dispose()
  reserveChart?.dispose()
  fanChart?.dispose()
  cashFlowChart?.dispose()
  distChart?.dispose()
  portfolioCfChart?.dispose()
  portfolioProdChart?.dispose()
  portfolioAgeChart?.dispose()
  ifrs17LrcChart?.dispose()
  ifrs17PnlChart?.dispose()
  tornadoChart?.dispose()
})
</script>

<template>
  <div class="relative min-h-screen bg-[#030712] text-slate-100 overflow-x-hidden font-sans selection:bg-fuchsia-500/30 selection:text-fuchsia-200">
    <!-- Ambient Neon Blur Glows -->
    <div class="glow-blob-pink top-[-100px] left-[-150px] animate-glow-pulse"></div>
    <div class="glow-blob-orange top-[200px] right-[-150px]"></div>
    <div class="glow-blob-purple top-[650px] left-[15%]"></div>
    <div class="glow-blob-blue bottom-[-100px] right-[10%]"></div>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 1. Header Navigation Bar -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <header class="border-b border-white/[0.08] bg-[#030712]/80 backdrop-blur-xl sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Logo -->
        <div class="flex items-center space-x-3">
          <div class="h-9 w-9 rounded-xl bg-gradient-to-tr from-fuchsia-600 via-rose-500 to-amber-400 p-[1px] shadow-lg shadow-fuchsia-500/25">
            <div class="h-full w-full bg-[#070b14] rounded-xl flex items-center justify-center">
              <svg class="h-4 w-4 text-fuchsia-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-sm font-extrabold tracking-wider text-white">ACTUARY<span class="text-transparent bg-clip-text bg-gradient-to-r from-fuchsia-400 via-rose-400 to-amber-300">ENGINE</span></span>
              <span class="px-1.5 py-0.5 text-[9px] font-mono font-bold rounded-full bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20">
                PRO v0.3
              </span>
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="hidden md:flex items-center space-x-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06] backdrop-blur-md">
          <button
            v-for="tab in [
              { id: 'overview', label: 'Executive Overview' },
              { id: 'sensitivity', label: 'Stress & Tornado' },
              { id: 'ifrs17', label: 'IFRS 17 (BBA)' },
              { id: 'portfolio', label: 'Portfolio Batch (CSV)' },
              { id: 'reserves', label: 'Reserves (_t V)' },
              { id: 'stochastic', label: 'ESG & VaR' },
              { id: 'cashflows', label: 'Cashflows' },
              { id: 'table', label: 'Cohort Table' }
            ]"
            :key="tab.id"
            @click="activeTab = tab.id; nextTick(() => renderAllCharts())"
            :class="[
              'px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200',
              activeTab === tab.id
                ? 'bg-gradient-to-r from-fuchsia-600 to-rose-600 text-white shadow-md shadow-fuchsia-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            ]"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Right Side Health & Action -->
        <div class="flex items-center space-x-3">
          <div class="hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-mono">
            <span
              :class="[
                'h-2 w-2 rounded-full',
                backendStatus === 'healthy' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-rose-400 shadow-[0_0_8px_#f43f5e]'
              ]"
            ></span>
            <span class="text-slate-300 text-[11px] font-medium">
              {{ backendStatus === 'healthy' ? 'FastAPI Connected' : 'FastAPI Offline' }}
            </span>
          </div>

          <button
            @click="executeValuation"
            :disabled="loading"
            class="relative group overflow-hidden rounded-xl p-[1px] focus:outline-none"
          >
            <span class="absolute inset-0 bg-gradient-to-r from-fuchsia-500 via-rose-500 to-amber-400 rounded-xl"></span>
            <span class="relative block px-4 py-1.5 rounded-[11px] bg-[#070b14] transition-all duration-200 group-hover:bg-opacity-70 text-xs font-semibold text-white flex items-center space-x-2">
              <svg :class="['h-3.5 w-3.5 text-rose-400', loading ? 'animate-spin' : '']" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>{{ loading ? 'Simulating...' : 'Recalculate' }}</span>
            </span>
          </button>
        </div>
      </div>
    </header>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 2. Error Notification Banner -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <div v-if="errorMessage || backendStatus === 'error'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4 relative z-20">
      <div class="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs font-mono flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg shadow-rose-500/10">
        <div class="flex items-center space-x-2.5">
          <span class="h-2 w-2 rounded-full bg-rose-500 animate-ping"></span>
          <div>
            <span class="font-bold text-rose-400">Backend Connection Warning:</span>
            <span class="ml-1 text-slate-300">{{ errorMessage || 'FastAPI server not detected at http://127.0.0.1:8000.' }}</span>
          </div>
        </div>
        <div class="flex items-center space-x-3">
          <span class="px-2 py-1 rounded bg-black/40 text-[10px] text-slate-400 border border-white/10 font-mono">
            uvicorn actuary_engine.api.main:app --port 8000
          </span>
          <button
            @click="executeValuation"
            class="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 font-semibold rounded-lg transition border border-rose-500/40"
          >
            Retry
          </button>
        </div>
      </div>
    </div>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 3. Real-Time WebSocket Simulation Progress Bar -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <div v-if="isSimulating" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4 relative z-20">
      <div class="neon-glass rounded-2xl p-4 border border-fuchsia-500/30 shadow-lg shadow-fuchsia-500/10 space-y-2">
        <div class="flex items-center justify-between text-xs font-mono">
          <div class="flex items-center space-x-2">
            <span class="h-2.5 w-2.5 rounded-full bg-fuchsia-400 animate-ping"></span>
            <span class="font-bold text-white tracking-wide">
              Streaming Vectorized Monte Carlo Simulation
            </span>
            <span class="text-fuchsia-400 text-[11px]">
              ({{ completedPaths.toLocaleString() }} / {{ totalPaths.toLocaleString() }} paths)
            </span>
          </div>
          <div class="flex items-center space-x-3">
            <span v-if="partialMetrics" class="text-slate-400 text-[11px]">
              Interim Mean BEL: <strong class="text-emerald-400 font-mono">{{ formatCurrency(partialMetrics.mean_bel) }}</strong>
            </span>
            <span class="font-bold text-fuchsia-300 font-mono text-sm">
              {{ simProgress.toFixed(0) }}%
            </span>
          </div>
        </div>

        <div class="w-full bg-slate-900/80 rounded-full h-2.5 overflow-hidden border border-white/[0.08]">
          <div
            class="h-full bg-gradient-to-r from-fuchsia-500 via-rose-500 to-amber-400 rounded-full transition-all duration-150 shadow-[0_0_12px_rgba(236,72,153,0.6)]"
            :style="{ width: `${simProgress}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 4. Hero Headline Section & Feature Badges -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-4 text-center relative z-10">
      <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/[0.04] border border-fuchsia-500/20 backdrop-blur-xl mb-4 shadow-[0_0_20px_rgba(236,72,153,0.15)]">
        <span class="h-1.5 w-1.5 rounded-full bg-fuchsia-400 animate-pulse"></span>
        <span class="text-xs font-medium text-slate-300">Automated Multi-Dimensional Stress Testing</span>
        <span class="text-[10px] text-fuchsia-400 font-mono">🌪️ Tornado Risk Ranking</span>
      </div>

      <h1 class="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight">
        The fastest way to <span class="text-transparent bg-clip-text bg-gradient-to-r from-fuchsia-400 via-rose-400 to-amber-300">model, value & stress-test</span> actuarial liabilities.
      </h1>
      <p class="mt-3 text-sm text-slate-400 max-w-2xl mx-auto font-mono">
        Tornado sensitivity charts, effective liability duration & DV01, Hull-White/CIR ESG, IFRS 17 BBA, and seriatim batch portfolios.
      </p>

      <!-- Preset Quick Bar -->
      <div class="mt-6 flex flex-wrap items-center justify-center gap-2">
        <span class="text-xs font-mono text-slate-500 mr-1">Quick Presets:</span>
        <button
          @click="applyPreset('endowment_20')"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-fuchsia-500/20 border border-white/[0.08] hover:border-fuchsia-500/40 text-slate-300 transition"
        >
          🎯 20-Yr Endowment ($1M)
        </button>
        <button
          @click="applyPreset('term_30')"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-rose-500/20 border border-white/[0.08] hover:border-rose-500/40 text-slate-300 transition"
        >
          🛡️ 30-Yr Term ($750k)
        </button>
        <button
          @click="activeTab = 'sensitivity'; nextTick(() => renderAllCharts())"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-rose-500/20 border border-white/[0.08] hover:border-rose-500/40 text-rose-300 transition"
        >
          🌪️ Tornado Sensitivity
        </button>
        <button
          @click="activeTab = 'ifrs17'; nextTick(() => renderAllCharts())"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-amber-500/20 border border-white/[0.08] hover:border-amber-500/40 text-amber-300 transition"
        >
          📑 IFRS 17 (BBA)
        </button>
        <button
          @click="activeTab = 'portfolio'; runSamplePortfolioDemo(1000)"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-emerald-500/20 border border-white/[0.08] hover:border-emerald-500/40 text-emerald-300 transition"
        >
          📁 Batch Portfolio (1,000 Policies)
        </button>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 5. SENSITIVITY & STRESS TESTING WORKSPACE TAB -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section v-if="activeTab === 'sensitivity'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10 space-y-6">
      <!-- Sensitivity Baseline Indicators KPI Strip -->
      <div v-if="sensitivityData?.baseline" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <!-- Duration -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">LIABILITY DURATION</div>
          <div class="text-2xl font-bold font-mono text-sky-300 mt-1">
            {{ sensitivityData.baseline.effective_duration }} yrs
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Effective Modified Duration</div>
        </div>

        <!-- DV01 -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">DOLLAR DURATION (DV01)</div>
          <div class="text-2xl font-bold font-mono text-amber-300 mt-1">
            {{ formatCurrency(sensitivityData.baseline.dv01) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Dollar shift per 1 bp</div>
        </div>

        <!-- Convexity -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">LIABILITY CONVEXITY</div>
          <div class="text-2xl font-bold font-mono text-fuchsia-300 mt-1">
            {{ sensitivityData.baseline.effective_convexity }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Curvature sensitivity</div>
        </div>

        <!-- PV Benefits -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">PV FUTURE BENEFITS</div>
          <div class="text-2xl font-bold font-mono text-rose-300 mt-1">
            {{ formatCurrency(sensitivityData.baseline.pv_future_benefits) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Claims + Maturities</div>
        </div>

        <!-- Base BEL -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">BASE NET BEL</div>
          <div class="text-2xl font-bold font-mono text-emerald-300 mt-1">
            {{ formatCurrency(sensitivityData.baseline.base_reserve) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">PV(Outgo) - PV(Premiums)</div>
        </div>
      </div>

      <!-- Tornado Chart Visualizer Card -->
      <div v-if="sensitivityData" class="neon-glass rounded-2xl p-6 border border-white/[0.08] space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.08] pb-3">
          <div>
            <h3 class="text-base font-bold text-white tracking-wide flex items-center space-x-2">
              <span class="h-3 w-3 rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e]"></span>
              <span>Actuarial Tornado Sensitivity Chart (Ranked by Total Delta Swing)</span>
            </h3>
            <p class="text-xs text-slate-400 font-mono">
              Green/Cyan = Downside Shock Delta ($\Delta V_{\text{low}}$) | Orange/Red = Upside Shock Delta ($\Delta V_{\text{high}}$) relative to zero.
            </p>
          </div>
          <span class="px-2 py-0.5 text-xs font-mono rounded-full bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20">
            One-At-A-Time (OAT)
          </span>
        </div>
        <div ref="tornadoChartRef" class="w-full h-96"></div>
      </div>

      <!-- Compound Macro-Stress Scenario Matrix -->
      <div v-if="sensitivityData" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Table 1: Compound Scenarios -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                Compound Stress Scenarios (Solvency & Macro Shocks)
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Joint financial and demographic stress packages.
              </p>
            </div>
          </div>

          <div class="overflow-x-auto border border-white/[0.08] rounded-xl max-h-[380px]">
            <table class="min-w-full text-left text-xs divide-y divide-white/[0.08] font-mono">
              <thead class="bg-[#0b0f19] text-slate-300 sticky top-0 z-10">
                <tr>
                  <th class="px-3 py-2">Scenario</th>
                  <th class="px-3 py-2">Shocked Reserve</th>
                  <th class="px-3 py-2">Delta ($)</th>
                  <th class="px-3 py-2">Solvency Impact</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/[0.04] bg-[#070b14]/60 text-slate-300">
                <tr v-for="sc in sensitivityData.combined_scenarios" :key="sc.scenario_id" class="hover:bg-white/[0.04]">
                  <td class="px-3 py-2.5">
                    <div class="font-bold text-white">{{ sc.name }}</div>
                    <div class="text-[10px] text-slate-400">{{ sc.description }}</div>
                  </td>
                  <td class="px-3 py-2 text-sky-300 font-bold">{{ formatCurrency(sc.shocked_reserve) }}</td>
                  <td :class="['px-3 py-2 font-bold', sc.delta_reserve > 0 ? 'text-rose-400' : 'text-emerald-400']">
                    {{ sc.delta_reserve > 0 ? '+' : '' }}{{ formatCurrency(sc.delta_reserve) }}
                  </td>
                  <td class="px-3 py-2">
                    <span
                      :class="[
                        'px-2 py-0.5 text-[10px] font-bold font-mono rounded-full border',
                        sc.solvency_impact === 'HIGH RISK'
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                          : sc.solvency_impact === 'MODERATE RISK'
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      ]"
                    >
                      {{ sc.solvency_impact }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Table 2: One-At-A-Time Sensitivity Items -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                One-At-A-Time (OAT) Sensitivity Table
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Individual factor delta bounds and total swing magnitude.
              </p>
            </div>
          </div>

          <div class="overflow-x-auto border border-white/[0.08] rounded-xl max-h-[380px]">
            <table class="min-w-full text-left text-xs divide-y divide-white/[0.08] font-mono">
              <thead class="bg-[#0b0f19] text-slate-300 sticky top-0 z-10">
                <tr>
                  <th class="px-3 py-2">Risk Factor</th>
                  <th class="px-3 py-2">Low Shock</th>
                  <th class="px-3 py-2">High Shock</th>
                  <th class="px-3 py-2">Total Swing</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/[0.04] bg-[#070b14]/60 text-slate-300">
                <tr v-for="item in sensitivityData.tornado_items" :key="item.risk_factor" class="hover:bg-white/[0.04]">
                  <td class="px-3 py-2 text-white font-semibold">{{ item.risk_factor }}</td>
                  <td class="px-3 py-2 text-emerald-400">{{ formatCurrency(item.low_reserve) }}</td>
                  <td class="px-3 py-2 text-rose-400">{{ formatCurrency(item.high_reserve) }}</td>
                  <td class="px-3 py-2 text-fuchsia-300 font-bold">
                    {{ formatCurrency(item.swing) }}
                    <span class="text-[10px] text-slate-400">({{ item.swing_pct }}%)</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 6. IFRS 17 / PSAK 117 VALUATION WORKSPACE TAB -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section v-if="activeTab === 'ifrs17'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10 space-y-6">
      <!-- Top IFRS 17 Initial Recognition Cards -->
      <div v-if="ifrs17Data?.initial_balance" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <!-- Classification -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">COHORT GROUP</div>
          <div class="mt-2">
            <span
              :class="[
                'px-2.5 py-1 text-xs font-bold font-mono rounded-full border',
                ifrs17Data.initial_balance.classification === 'ONEROUS'
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              ]"
            >
              {{ ifrs17Data.initial_balance.classification }}
            </span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-2">
            Margin: {{ (ifrs17Data.initial_balance.profitability_margin * 100).toFixed(1) }}%
          </div>
        </div>

        <!-- BEL -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">BEST ESTIMATE (BEL)</div>
          <div class="text-2xl font-bold font-mono text-sky-300 mt-1">
            {{ formatCurrency(ifrs17Data.initial_balance.bel_0) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">PV(Outflows) - PV(Inflows)</div>
        </div>

        <!-- RA -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">RISK ADJUSTMENT (RA)</div>
          <div class="text-2xl font-bold font-mono text-amber-300 mt-1">
            {{ formatCurrency(ifrs17Data.initial_balance.ra_0) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Non-Financial Risk (6%)</div>
        </div>

        <!-- CSM -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">INITIAL CSM (PROFIT)</div>
          <div class="text-2xl font-bold font-mono text-fuchsia-300 mt-1">
            {{ formatCurrency(ifrs17Data.initial_balance.csm_0) }}
          </div>
          <div class="text-[11px] text-fuchsia-400 font-mono mt-1">Unearned Future Profit</div>
        </div>

        <!-- Loss Component -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">LOSS COMPONENT (LC)</div>
          <div class="text-2xl font-bold font-mono text-rose-400 mt-1">
            {{ formatCurrency(ifrs17Data.initial_balance.loss_component_0) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Day 1 P&L Impact</div>
        </div>
      </div>

      <!-- IFRS 17 Charts Workspace -->
      <div v-if="ifrs17Data" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 1. LRC Transition Stacked Area Chart -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                Liability for Remaining Coverage (LRC) Stacked Trajectory
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                $\text{LRC}_t = \text{BEL}_t$ (Cyan) + $\text{RA}_t$ (Orange) + $\text{CSM}_t$ (Pink).
              </p>
            </div>
            <span class="px-2 py-0.5 text-[10px] font-mono rounded-full bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20">
              GMM / BBA
            </span>
          </div>
          <div ref="ifrs17LrcChartRef" class="w-full h-80"></div>
        </div>

        <!-- 2. Income Statement Waterfall Chart -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                IFRS 17 Insurance Service Revenue & P&L Waterfall
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Revenue release (Green), Claims outgo (Red), Expenses (Orange), and CSM release (Pink).
              </p>
            </div>
          </div>
          <div ref="ifrs17PnlChartRef" class="w-full h-80"></div>
        </div>
      </div>

      <!-- IFRS 17 Balance Sheet & Income Statement Schedules -->
      <div v-if="ifrs17Data" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Schedule 1: Balance Sheet (LRC) -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                Balance Sheet Schedule (LRC Roll-Forward)
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Closing carrying amounts at each reporting period.
              </p>
            </div>
          </div>

          <div class="overflow-x-auto border border-white/[0.08] rounded-xl max-h-[380px]">
            <table class="min-w-full text-left text-xs divide-y divide-white/[0.08] font-mono">
              <thead class="bg-[#0b0f19] text-slate-300 sticky top-0 z-10">
                <tr>
                  <th class="px-3 py-2">Duration</th>
                  <th class="px-3 py-2">BEL</th>
                  <th class="px-3 py-2">Risk Adj (RA)</th>
                  <th class="px-3 py-2">CSM</th>
                  <th class="px-3 py-2">Total LRC</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/[0.04] bg-[#070b14]/60 text-slate-300">
                <tr v-for="row in ifrs17Data.balance_sheet_schedule" :key="row.duration" class="hover:bg-white/[0.04]">
                  <td class="px-3 py-2 text-fuchsia-400 font-bold">t={{ row.duration }}</td>
                  <td class="px-3 py-2 text-sky-300">{{ formatCurrency(row.bel) }}</td>
                  <td class="px-3 py-2 text-amber-300">{{ formatCurrency(row.risk_adjustment) }}</td>
                  <td class="px-3 py-2 text-rose-300 font-bold">{{ formatCurrency(row.csm) }}</td>
                  <td class="px-3 py-2 text-white font-bold">{{ formatCurrency(row.total_lrc) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Schedule 2: Income Statement (P&L) -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                Income Statement Schedule (P&L Recognition)
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Insurance revenue, claims, and CSM amortization.
              </p>
            </div>
          </div>

          <div class="overflow-x-auto border border-white/[0.08] rounded-xl max-h-[380px]">
            <table class="min-w-full text-left text-xs divide-y divide-white/[0.08] font-mono">
              <thead class="bg-[#0b0f19] text-slate-300 sticky top-0 z-10">
                <tr>
                  <th class="px-3 py-2">Year</th>
                  <th class="px-3 py-2">Insurance Revenue</th>
                  <th class="px-3 py-2">Service Expenses</th>
                  <th class="px-3 py-2">CSM Release</th>
                  <th class="px-3 py-2">Service Result</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/[0.04] bg-[#070b14]/60 text-slate-300">
                <tr v-for="row in ifrs17Data.income_statement_schedule" :key="row.year" class="hover:bg-white/[0.04]">
                  <td class="px-3 py-2 text-emerald-400 font-bold">Yr {{ row.year + 1 }}</td>
                  <td class="px-3 py-2 text-emerald-300">{{ formatCurrency(row.insurance_revenue) }}</td>
                  <td class="px-3 py-2 text-rose-300">{{ formatCurrency(row.insurance_service_expenses) }}</td>
                  <td class="px-3 py-2 text-fuchsia-300 font-bold">{{ formatCurrency(row.csm_amortization) }}</td>
                  <td :class="['px-3 py-2 font-bold', row.insurance_service_result >= 0 ? 'text-emerald-400' : 'text-rose-400']">
                    {{ formatCurrency(row.insurance_service_result) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 7. PORTFOLIO BATCH WORKSPACE TAB -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section v-if="activeTab === 'portfolio'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10 space-y-6">
      <!-- Upload & Configuration Banner -->
      <div class="neon-border-gradient shadow-2xl">
        <div class="p-6 space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
            <div>
              <h2 class="text-lg font-bold text-white tracking-wide flex items-center space-x-2">
                <span class="h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]"></span>
                <span>Seriatim Portfolio Batch Valuation</span>
              </h2>
              <p class="text-xs text-slate-400 font-mono">
                Upload CSV or run synthetic portfolios to calculate aggregate liabilities, cash flows & segment distributions.
              </p>
            </div>

            <div class="flex items-center space-x-3">
              <button
                @click="runSamplePortfolioDemo(1000)"
                :disabled="portfolioLoading"
                class="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:opacity-90 text-white rounded-xl text-xs font-mono font-semibold transition shadow-lg shadow-emerald-500/20 flex items-center space-x-2"
              >
                <svg class="h-4 w-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>{{ portfolioLoading ? 'Valuing Portfolio...' : '⚡ Quick Demo (1,000 Policies)' }}</span>
              </button>
            </div>
          </div>

          <!-- Drag and Drop Dropzone -->
          <div
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handlePortfolioDrop"
            :class="[
              'border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer',
              isDragging
                ? 'border-emerald-400 bg-emerald-500/10 shadow-[0_0_30px_rgba(52,211,153,0.2)]'
                : 'border-white/[0.15] bg-[#070b14]/50 hover:border-emerald-400/50 hover:bg-[#0b0f19]'
            ]"
            @click="$refs.fileInput.click()"
          >
            <input
              type="file"
              ref="fileInput"
              accept=".csv"
              class="hidden"
              @change="handlePortfolioFileUpload"
            />
            <div class="flex flex-col items-center space-y-2">
              <div class="h-12 w-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p class="text-sm font-semibold text-white">
                Drag and drop your Policy CSV here, or <span class="text-emerald-400 underline">browse files</span>
              </p>
              <p class="text-[11px] font-mono text-slate-500">
                Supported columns: policy_id, issue_age, term_years, sum_assured, gross_premium, product_type, policy_duration_years
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Portfolio Summary Cards -->
      <div v-if="portfolioData" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">TOTAL POLICIES</div>
          <div class="text-2xl font-bold font-mono text-white mt-1">
            {{ portfolioData.total_policies.toLocaleString() }}
          </div>
          <div class="text-[11px] text-emerald-400 font-mono mt-1">Seriatim In-Force</div>
        </div>

        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">TOTAL SUM ASSURED</div>
          <div class="text-2xl font-bold font-mono text-sky-300 mt-1">
            {{ formatCurrency(portfolioData.total_sum_assured) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Total Face Amount</div>
        </div>

        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">PV FUTURE BENEFITS</div>
          <div class="text-2xl font-bold font-mono text-rose-300 mt-1">
            {{ formatCurrency(portfolioData.total_pvfb) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Claims + Maturities</div>
        </div>

        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">PV FUTURE PREMIUMS</div>
          <div class="text-2xl font-bold font-mono text-emerald-300 mt-1">
            {{ formatCurrency(portfolioData.total_pvfp) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Expected Inflows</div>
        </div>

        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08]">
          <div class="text-xs font-mono text-slate-400">TOTAL PORTFOLIO BEL</div>
          <div class="text-2xl font-bold font-mono text-fuchsia-300 mt-1">
            {{ formatCurrency(portfolioData.total_bel) }}
          </div>
          <div class="text-[11px] text-fuchsia-400 font-mono mt-1">Net Liability Provision</div>
        </div>
      </div>

      <!-- Portfolio Charts Workspace -->
      <div v-if="portfolioData" class="space-y-6">
        <!-- 1. Portfolio Aggregate Cash Flow Waterfall -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                Aggregate Portfolio Multi-Year Cash Flow Projection
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Annual aggregate premium inflows (Green), death/maturity claims (Red), and expenses (Orange).
              </p>
            </div>
          </div>
          <div ref="portfolioCfChartRef" class="w-full h-80"></div>
        </div>

        <!-- 2. Breakdown Donut & Age Bar Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
            <h3 class="text-sm font-bold text-white tracking-wide mb-1">
              Portfolio Composition by Product Line
            </h3>
            <p class="text-xs text-slate-400 font-mono mb-2">Face amount exposure distribution</p>
            <div ref="portfolioProdChartRef" class="w-full h-72"></div>
          </div>

          <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
            <h3 class="text-sm font-bold text-white tracking-wide mb-1">
              Cohort Breakdown by Attained Age Bracket
            </h3>
            <p class="text-xs text-slate-400 font-mono mb-2">Policy count and net BEL by age cohort</p>
            <div ref="portfolioAgeChartRef" class="w-full h-72"></div>
          </div>
        </div>

        <!-- 3. Sample Seriatim Table -->
        <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-sm font-bold text-white tracking-wide">
                Sample Seriatim Valuation Output
              </h3>
              <p class="text-xs text-slate-400 font-mono">
                Individual contract records with discounted PVFB, PVFP, and Net BEL.
              </p>
            </div>
            <span class="text-xs font-mono text-slate-400">
              Displaying first {{ portfolioData.sample_seriatim.length }} records
            </span>
          </div>

          <div class="overflow-x-auto border border-white/[0.08] rounded-xl max-h-[420px]">
            <table class="min-w-full text-left text-xs divide-y divide-white/[0.08] font-mono">
              <thead class="bg-[#0b0f19] text-slate-300 sticky top-0 z-10">
                <tr>
                  <th class="px-3 py-2.5 font-semibold">Policy ID</th>
                  <th class="px-3 py-2.5 font-semibold">Product</th>
                  <th class="px-3 py-2.5 font-semibold">Age</th>
                  <th class="px-3 py-2.5 font-semibold">Term</th>
                  <th class="px-3 py-2.5 font-semibold">Face Amount</th>
                  <th class="px-3 py-2.5 font-semibold">Gross Premium</th>
                  <th class="px-3 py-2.5 font-semibold">PVFB</th>
                  <th class="px-3 py-2.5 font-semibold">PVFP</th>
                  <th class="px-3 py-2.5 font-semibold">Net BEL</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/[0.04] bg-[#070b14]/60 text-slate-300">
                <tr v-for="pol in portfolioData.sample_seriatim" :key="pol.policy_id" class="hover:bg-white/[0.04]">
                  <td class="px-3 py-2 text-emerald-400 font-bold">{{ pol.policy_id }}</td>
                  <td class="px-3 py-2 uppercase text-slate-300">{{ pol.product_type }}</td>
                  <td class="px-3 py-2">{{ pol.issue_age }}</td>
                  <td class="px-3 py-2">{{ pol.term_years }} yrs</td>
                  <td class="px-3 py-2 text-sky-300">{{ formatCurrency(pol.sum_assured) }}</td>
                  <td class="px-3 py-2 text-emerald-400">{{ formatCurrency(pol.gross_premium) }}</td>
                  <td class="px-3 py-2 text-rose-300">{{ formatCurrency(pol.pvfb) }}</td>
                  <td class="px-3 py-2 text-emerald-300">{{ formatCurrency(pol.pvfp) }}</td>
                  <td :class="['px-3 py-2 font-bold', pol.bel > 0 ? 'text-rose-400' : 'text-emerald-400']">
                    {{ formatCurrency(pol.bel) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 8. Hero Visualizer Card (Showcase Bar Chart for Single Contract) -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section v-if="activeTab !== 'portfolio' && activeTab !== 'ifrs17' && activeTab !== 'sensitivity'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 relative z-10">
      <div class="neon-border-gradient shadow-2xl">
        <div class="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
          <!-- Left: Big Neon Chart -->
          <div class="lg:col-span-2 space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="inline-block h-3 w-3 rounded-full bg-rose-500 shadow-[0_0_10px_#f43f5e]"></span>
                <h3 class="text-sm font-bold text-white tracking-wide">
                  Expected Liability Outgo Waterfall
                </h3>
              </div>
              <div class="text-[11px] font-mono text-slate-400">
                Annual Net Outgo (Coral) & Cumulative Path (Cyan)
              </div>
            </div>
            <div ref="heroChartRef" class="w-full h-64 sm:h-72"></div>
          </div>

          <!-- Right: Hero KPI Table -->
          <div class="bg-black/40 rounded-xl p-5 border border-white/[0.06] space-y-4 font-mono text-xs">
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-bold border-b border-slate-800 pb-2 flex items-center justify-between">
              <span>Valuation Summary</span>
              <span class="text-fuchsia-400">{{ deterministicData?.table_name || 'SOA ILT' }}</span>
            </div>

            <div class="space-y-3">
              <div class="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span class="text-slate-400">Product Contract:</span>
                <span class="text-white font-bold capitalize">{{ form.product_type.replace('_', ' ') }}</span>
              </div>
              <div class="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span class="text-slate-400">Net Single Premium (NSP):</span>
                <span class="text-sky-300 font-bold">{{ formatCurrency(deterministicData?.nsp) }}</span>
              </div>
              <div class="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span class="text-slate-400">Annual Net Premium (P):</span>
                <span class="text-emerald-400 font-bold">{{ formatCurrency(deterministicData?.annual_net_premium) }}</span>
              </div>
              <div class="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span class="text-slate-400">Mean Stochastic BEL:</span>
                <span class="text-fuchsia-300 font-bold">{{ formatCurrency(stochasticData?.mean_bel) }}</span>
              </div>
              <div class="flex justify-between items-center py-1 border-b border-white/[0.04]">
                <span class="text-slate-400">95% Value at Risk (VaR):</span>
                <span class="text-rose-400 font-bold">{{ formatCurrency(stochasticData?.var_95) }}</span>
              </div>
              <div class="flex justify-between items-center py-1">
                <span class="text-slate-400">95% Expected Shortfall:</span>
                <span class="text-amber-300 font-bold">{{ formatCurrency(stochasticData?.cvar_95) }}</span>
              </div>
            </div>

            <div class="pt-2">
              <button
                @click="activeTab = 'stochastic'; nextTick(() => renderAllCharts())"
                class="w-full py-2 bg-gradient-to-r from-fuchsia-500 to-rose-600 text-white rounded-lg font-sans font-semibold text-xs tracking-wider uppercase hover:opacity-90 transition shadow-lg shadow-fuchsia-500/20"
              >
                Inspect Monte Carlo Fan Chart →
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 9. Top KPI Metric Cards Strip -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section v-if="activeTab !== 'portfolio' && activeTab !== 'ifrs17' && activeTab !== 'sensitivity'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 relative z-10">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Metric 1 -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08] relative overflow-hidden group hover:border-sky-500/40 transition">
          <div class="flex justify-between items-center text-xs font-mono text-slate-400 mb-1">
            <span>ANNUAL NET PREMIUM (P)</span>
            <span class="text-sky-400">ä = {{ deterministicData?.annuity_factor?.toFixed(3) || '—' }}</span>
          </div>
          <div class="text-2xl font-bold font-mono text-white mt-1">
            <span v-if="loading" class="animate-pulse text-slate-500">...</span>
            <span v-else>{{ formatCurrency(deterministicData?.annual_net_premium) }}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Equivalence: P · ä = NSP</div>
        </div>

        <!-- Metric 2 -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08] relative overflow-hidden group hover:border-emerald-500/40 transition">
          <div class="flex justify-between items-center text-xs font-mono text-slate-400 mb-1">
            <span>ANNUAL GROSS PREMIUM</span>
            <span class="text-emerald-400">+20% Load</span>
          </div>
          <div class="text-2xl font-bold font-mono text-emerald-300 mt-1">
            <span v-if="loading" class="animate-pulse text-slate-500">...</span>
            <span v-else>{{ formatCurrency(deterministicData?.annual_gross_premium) }}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Acquisition & Maint. Loaded</div>
        </div>

        <!-- Metric 3 -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08] relative overflow-hidden group hover:border-fuchsia-500/40 transition">
          <div class="flex justify-between items-center text-xs font-mono text-slate-400 mb-1">
            <span>MEAN BEST ESTIMATE (BEL)</span>
            <span class="text-fuchsia-400">{{ (stochasticData?.mean_bel || 0) < 0 ? 'Surplus' : 'Deficit' }}</span>
          </div>
          <div class="text-2xl font-bold font-mono text-fuchsia-300 mt-1">
            <span v-if="loading" class="animate-pulse text-slate-500">...</span>
            <span v-else>{{ formatCurrency(stochasticData?.mean_bel ?? deterministicData?.bel) }}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">Std Dev: {{ formatCurrency(stochasticData?.std_bel) }}</div>
        </div>

        <!-- Metric 4 -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08] relative overflow-hidden group hover:border-rose-500/40 transition">
          <div class="flex justify-between items-center text-xs font-mono text-slate-400 mb-1">
            <span>95% TAIL RISK (VaR / CVaR)</span>
            <span class="text-rose-400">CTE 95</span>
          </div>
          <div class="text-2xl font-bold font-mono text-rose-300 mt-1">
            <span v-if="loading" class="animate-pulse text-slate-500">...</span>
            <span v-else>{{ formatCurrency(stochasticData?.var_95) }}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">CVaR 95%: {{ formatCurrency(stochasticData?.cvar_95) }}</div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 10. Main Workspace Layout (Sidebar Controls + Multi-Chart Workspace) -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section v-if="activeTab !== 'portfolio' && activeTab !== 'ifrs17' && activeTab !== 'sensitivity'" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Control Deck Sidebar (1/3) -->
        <div class="lg:col-span-1 space-y-6">
          <div class="neon-glass rounded-2xl p-5 border border-white/[0.08] space-y-5">
            <div class="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <h2 class="text-xs font-bold font-mono uppercase tracking-wider text-fuchsia-400 flex items-center space-x-2">
                <span>⚙️ Contract & ESG Controls</span>
              </h2>
              <span class="text-[10px] font-mono text-slate-400">Dynamic Tables</span>
            </div>

            <!-- Mortality Table Selection -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label class="block text-xs font-medium text-slate-300 font-mono">Mortality Life Table</label>
                <button
                  @click="showTableModal = true"
                  class="text-[11px] font-mono text-fuchsia-400 hover:text-fuchsia-300 flex items-center space-x-1"
                >
                  <span>➕ Upload Table</span>
                </button>
              </div>
              <select
                v-model="form.table_id"
                @change="executeValuation"
                class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition"
              >
                <option v-for="t in availableTables" :key="t.table_id" :value="t.table_id">
                  {{ t.name }} {{ t.is_builtin ? '(Built-in)' : '(Custom)' }}
                </option>
              </select>
            </div>

            <!-- Product Contract -->
            <div class="space-y-3 border-t border-white/[0.08] pt-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1 font-mono">Product Line</label>
                <select
                  v-model="form.product_type"
                  class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition"
                >
                  <option value="endowment">20-Year Endowment Insurance</option>
                  <option value="term">Term Life Insurance</option>
                  <option value="whole_life">Whole Life Insurance</option>
                  <option value="pure_endowment">Pure Endowment</option>
                </select>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-medium text-slate-300 mb-1 font-mono">Issue Age (x)</label>
                  <input
                    type="number"
                    v-model.number="form.issue_age"
                    min="0"
                    max="100"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition"
                  />
                </div>
                <div v-if="form.product_type !== 'whole_life'">
                  <label class="block text-xs font-medium text-slate-300 mb-1 font-mono">Term (n yrs)</label>
                  <input
                    type="number"
                    v-model.number="form.term"
                    min="1"
                    max="80"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition"
                  />
                </div>
              </div>

              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1 font-mono">Sum Assured (S)</label>
                <input
                  type="number"
                  v-model.number="form.sum_assured"
                  step="50000"
                  class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition"
                />
              </div>
            </div>

            <!-- Economics & Expenses -->
            <div class="space-y-3 border-t border-white/[0.08] pt-4">
              <h3 class="text-xs font-mono font-bold text-sky-400 uppercase tracking-wider">
                Economics & Expenses
              </h3>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[11px] text-slate-400 mb-1 font-mono">Base Rate (i)</label>
                  <input
                    type="number"
                    v-model.number="form.interest_rate"
                    step="0.005"
                    min="0.01"
                    max="0.20"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[11px] text-slate-400 mb-1 font-mono">Acquisition (α %)</label>
                  <input
                    type="number"
                    v-model.number="form.expense.percent_of_premium_first"
                    step="0.05"
                    min="0"
                    max="1.0"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  />
                </div>
              </div>
            </div>

            <!-- Vasicek ESG Parameters -->
            <div class="space-y-3 border-t border-white/[0.08] pt-4">
              <h3 class="text-xs font-mono font-bold text-rose-400 uppercase tracking-wider">
                Vasicek ESG Parameters
              </h3>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[11px] text-slate-400 mb-1 font-mono">Reversion (κ)</label>
                  <input
                    type="number"
                    v-model.number="form.vasicek.kappa"
                    step="0.05"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[11px] text-slate-400 mb-1 font-mono">Long-term (θ)</label>
                  <input
                    type="number"
                    v-model.number="form.vasicek.theta"
                    step="0.005"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[11px] text-slate-400 mb-1 font-mono">Volatility (σ)</label>
                  <input
                    type="number"
                    v-model.number="form.vasicek.sigma"
                    step="0.005"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label class="block text-[11px] text-slate-400 mb-1 font-mono">Paths (N)</label>
                  <select
                    v-model.number="form.n_scenarios"
                    class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-1.5 text-xs text-white font-mono"
                  >
                    <option :value="1000">1,000</option>
                    <option :value="2500">2,500</option>
                    <option :value="5000">5,000</option>
                    <option :value="10000">10,000 (Async Stream)</option>
                    <option :value="25000">25,000 (Large Scale)</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Dynamic Policyholder Lapse -->
            <div class="border-t border-white/[0.08] pt-4 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-xs font-mono font-medium text-slate-200">Dynamic S-Curve Lapse</div>
                  <div class="text-[10px] text-slate-400 font-mono">Disintermediation risk</div>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="form.enable_dynamic_lapse" class="sr-only peer" />
                  <div class="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-fuchsia-500"></div>
                </label>
              </div>
            </div>

            <!-- Submit CTA -->
            <button
              @click="executeValuation"
              :disabled="loading"
              class="w-full py-3 rounded-xl font-mono font-bold text-xs uppercase tracking-wider text-white bg-gradient-to-r from-fuchsia-600 via-rose-500 to-amber-500 hover:opacity-90 transition shadow-lg shadow-fuchsia-600/30 flex items-center justify-center space-x-2"
            >
              <svg v-if="loading" class="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              <span>{{ loading ? `Streaming Paths (${simProgress.toFixed(0)}%)...` : 'Run Valuation Engine' }}</span>
            </button>
          </div>
        </div>

        <!-- Center/Right Multi-Chart Display Workspace (2/3) -->
        <div class="lg:col-span-2 space-y-6">
          <!-- View 1: Overview & Reserves -->
          <div v-show="activeTab === 'overview' || activeTab === 'reserves'" class="space-y-6">
            <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
              <div class="flex items-center justify-between mb-2">
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide">
                    Policy Reserve Profiles (${}_t V_{\text{pro}}$ vs ${}_t V_{\text{retro}}$ vs GPV)
                  </h3>
                  <p class="text-xs text-slate-400 font-mono">
                    Net prospective reserve verified equivalent to retrospective accumulation at all durations.
                  </p>
                </div>
                <span class="px-2 py-0.5 text-[10px] font-mono rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ${}_t V_{\text{pro}} \equiv {}_t V_{\text{retro}}$
                </span>
              </div>
              <div ref="reserveChartRef" class="w-full h-80"></div>
            </div>
          </div>

          <!-- View 2: Stochastic Fan Chart + Distribution -->
          <div v-show="activeTab === 'overview' || activeTab === 'stochastic'" class="space-y-6">
            <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
              <div class="flex items-center justify-between mb-2">
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide">
                    Vasicek Short-Rate ESG Fan Chart & Quantiles
                  </h3>
                  <p class="text-xs text-slate-400 font-mono">
                    5th, 25th, 50th, 75th, 95th percentiles across {{ form.n_scenarios.toLocaleString() }} simulated paths.
                  </p>
                </div>
                <span class="px-2 py-0.5 text-[10px] font-mono rounded-full bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20">
                  $dr_t = \kappa(\theta - r_t)dt + \sigma dW_t$
                </span>
              </div>
              <div ref="fanChartRef" class="w-full h-80"></div>
            </div>

            <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
              <div class="flex items-center justify-between mb-2">
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide">
                    Stochastic Liability Distribution & 95% Tail Region
                  </h3>
                  <p class="text-xs text-slate-400 font-mono">
                    Empirical BEL density showing Value at Risk ($\text{VaR}_{95}$) and Expected Shortfall ($\text{CVaR}_{95}$).
                  </p>
                </div>
              </div>
              <div ref="distChartRef" class="w-full h-80"></div>
            </div>
          </div>

          <!-- View 3: Cashflow Inflow vs Outflow -->
          <div v-show="activeTab === 'cashflows'" class="space-y-6">
            <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
              <div class="flex items-center justify-between mb-2">
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide">
                    Annual Premium Inflow vs. Claims Outflow
                  </h3>
                  <p class="text-xs text-slate-400 font-mono">
                    Green = Premium Inflows | Red = Mortality & Maturity Outgo | Orange = Expenses
                  </p>
                </div>
              </div>
              <div ref="cashFlowChartRef" class="w-full h-80"></div>
            </div>
          </div>

          <!-- View 4: Detailed Cohort Rollout Table -->
          <div v-show="activeTab === 'table'" class="space-y-6">
            <div class="neon-glass rounded-2xl p-5 border border-white/[0.08]">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h3 class="text-sm font-bold text-white tracking-wide">
                    Multi-Decrement Cohort Rollout Table
                  </h3>
                  <p class="text-xs text-slate-400 font-mono">
                    Detailed probability-weighted cashflows and discounted liabilities from FastAPI backend.
                  </p>
                </div>
                <span class="text-xs font-mono text-slate-400">
                  {{ deterministicData?.cash_flows?.length || 0 }} durations
                </span>
              </div>

              <div class="overflow-x-auto border border-white/[0.08] rounded-xl max-h-[500px]">
                <table class="min-w-full text-left text-xs divide-y divide-white/[0.08] font-mono">
                  <thead class="bg-[#0b0f19] text-slate-300 sticky top-0 z-10">
                    <tr>
                      <th class="px-3 py-2.5 font-semibold">Year</th>
                      <th class="px-3 py-2.5 font-semibold">Age</th>
                      <th class="px-3 py-2.5 font-semibold">Inforce</th>
                      <th class="px-3 py-2.5 font-semibold">Premium</th>
                      <th class="px-3 py-2.5 font-semibold">Death Claims</th>
                      <th class="px-3 py-2.5 font-semibold">Expenses</th>
                      <th class="px-3 py-2.5 font-semibold">Net CF</th>
                      <th class="px-3 py-2.5 font-semibold">PV Net</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-white/[0.04] bg-[#070b14]/60 text-slate-300">
                    <tr v-for="row in deterministicData?.cash_flows || []" :key="row.year" class="hover:bg-white/[0.04]">
                      <td class="px-3 py-2 text-fuchsia-400 font-bold">t={{ row.year }}</td>
                      <td class="px-3 py-2">{{ row.age }}</td>
                      <td class="px-3 py-2 text-slate-400">{{ (row.inforce_boy * 100).toFixed(2) }}%</td>
                      <td class="px-3 py-2 text-emerald-400">{{ formatCurrency(row.premium_income) }}</td>
                      <td class="px-3 py-2 text-rose-400">{{ formatCurrency(row.death_claims + row.maturity_benefit) }}</td>
                      <td class="px-3 py-2 text-amber-300">{{ formatCurrency(row.total_expense) }}</td>
                      <td :class="['px-3 py-2 font-bold', row.net_liability_cf > 0 ? 'text-rose-400' : 'text-emerald-400']">
                        {{ formatCurrency(row.net_liability_cf) }}
                      </td>
                      <td :class="['px-3 py-2 font-bold', row.pv_net_liability > 0 ? 'text-rose-400' : 'text-emerald-400']">
                        {{ formatCurrency(row.pv_net_liability) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 11. Custom Mortality Table Upload Modal -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <div v-if="showTableModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div class="neon-glass border border-white/[0.15] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.08] pb-3">
          <div class="flex items-center space-x-2">
            <span class="h-3 w-3 rounded-full bg-fuchsia-500 shadow-[0_0_8px_#ec4899]"></span>
            <h3 class="text-sm font-bold text-white tracking-wide">Upload Custom Mortality Table</h3>
          </div>
          <button @click="showTableModal = false" class="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        <div v-if="uploadTableError" class="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs font-mono">
          {{ uploadTableError }}
        </div>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1">Table Name (Optional)</label>
            <input
              type="text"
              v-model="uploadTableName"
              placeholder="e.g. 2024 Corporate Experience Table"
              class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-fuchsia-500"
            />
          </div>

          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1">Description / Citation</label>
            <input
              type="text"
              v-model="uploadTableDesc"
              placeholder="e.g. Experience mortality rates for insured lives"
              class="w-full bg-[#070b14] border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-white font-mono focus:border-fuchsia-500"
            />
          </div>

          <!-- Drag and Drop Zone -->
          <div
            @dragover.prevent="isTableDragging = true"
            @dragleave.prevent="isTableDragging = false"
            @drop.prevent="handleTableFileDrop"
            :class="[
              'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition',
              isTableDragging
                ? 'border-fuchsia-400 bg-fuchsia-500/10'
                : 'border-white/[0.15] bg-[#070b14]/50 hover:border-fuchsia-500/50'
            ]"
            @click="$refs.tableFileInput.click()"
          >
            <input
              type="file"
              ref="tableFileInput"
              accept=".csv,.tsv,.txt,.xml,.xtbml"
              class="hidden"
              @change="handleTableFileSelect"
            />
            <div class="flex flex-col items-center space-y-1">
              <span class="text-2xl">📄</span>
              <p class="text-xs font-semibold text-white">
                {{ uploadTableFile ? uploadTableFile.name : 'Drag and drop your table file here, or browse' }}
              </p>
              <p class="text-[10px] font-mono text-slate-500">
                Formats: CSV/TSV (`age,qx` or `age,px` or `age,lx`) or SOA XTbML (XML)
              </p>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end space-x-3 pt-2">
          <button
            @click="showTableModal = false"
            class="px-4 py-2 bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 rounded-xl text-xs font-mono"
          >
            Cancel
          </button>
          <button
            @click="submitCustomTable"
            :disabled="uploadTableLoading"
            class="px-4 py-2 bg-gradient-to-r from-fuchsia-600 to-rose-600 text-white font-bold rounded-xl text-xs font-mono shadow-lg shadow-fuchsia-600/25 flex items-center space-x-2"
          >
            <span>{{ uploadTableLoading ? 'Uploading...' : 'Upload & Use Table' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 12. Footer -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <footer class="border-t border-white/[0.08] bg-[#030712] py-6 mt-12 relative z-10">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs font-mono text-slate-500 gap-2">
        <div class="flex items-center space-x-2">
          <span class="text-fuchsia-400">ACTUARY ENGINE</span>
          <span>•</span>
          <span>Stress Testing & Tornado</span>
          <span>•</span>
          <span>IFRS 17 / PSAK 117</span>
          <span>•</span>
          <span>Portfolio Batch Engine</span>
        </div>
        <div>FastAPI • Vue 3 • Apache ECharts • TailwindCSS</div>
      </div>
    </footer>
  </div>
</template>
