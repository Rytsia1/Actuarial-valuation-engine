<script setup>
import { ref, shallowRef, reactive, onMounted, onUnmounted, nextTick, markRaw } from 'vue'
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
import StressTestDashboard from './components/StressTestDashboard.vue'
import ContractBuilderView from './views/ContractBuilderView.vue'

// ────────────────────────────────────────────────────────────
// Reactive Dashboard State
// ────────────────────────────────────────────────────────────

const activeTab = ref('overview')
const backendStatus = ref('checking')
const loading = ref(false)
const errorMessage = ref(null)
const backendDetails = ref(null)
const sidebarOpen = ref(false)

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
const portfolioData = shallowRef(null)
const portfolioInterestRate = ref(0.05)
const isDragging = ref(false)

// IFRS 17 State
const ifrs17Data = shallowRef(null)
const ifrs17Loading = ref(false)

// Sensitivity & Stress State
const sensitivityData = shallowRef(null)
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

// Valuation Results from FastAPI (shallowRef prevents recursive reactivity overload)
const deterministicData = shallowRef(null)
const stochasticData = shallowRef(null)

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
const stressTestDashboardRef = ref(null)

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

// Navigation definition
const navItems = [
  { id: 'overview', label: 'Overview', icon: 'chart' },
  { id: 'builder', label: 'Logic Builder', icon: 'blueprint' },
  { id: 'stochastic', label: 'ESG & Risk', icon: 'risk' },
  { id: 'sensitivity', label: 'Stress Testing', icon: 'tornado' },
  { id: 'ifrs17', label: 'IFRS 17', icon: 'balance' },
  { id: 'reserves', label: 'Reserves', icon: 'reserve' },
  { id: 'cashflows', label: 'Cash Flows', icon: 'cashflow' },
  { id: 'table', label: 'Cohort Data', icon: 'table' },
  { id: 'portfolio', label: 'Portfolio Batch', icon: 'portfolio' },
]

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

function formatPercent(val, decimals = 1) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  const sign = val > 0 ? '+' : ''
  return `${sign}${Number(val).toFixed(decimals)}%`
}

function renderTabCharts(tabId) {
  switch (tabId) {
    case 'overview':
      renderHeroChart()
      renderReserveChart()
      renderFanChart()
      renderDistChart()
      break
    case 'reserves':
      renderHeroChart()
      renderReserveChart()
      break
    case 'stochastic':
      renderHeroChart()
      renderFanChart()
      renderDistChart()
      break
    case 'cashflows':
      renderHeroChart()
      renderCashFlowChart()
      break
    case 'table':
      renderHeroChart()
      break
    case 'ifrs17':
      renderIFRS17Charts()
      break
    case 'portfolio':
      renderPortfolioCharts()
      break
    case 'sensitivity':
      stressTestDashboardRef.value?.resizeCharts?.()
      break
    case 'builder':
      break
  }
}

function switchTab(tabId) {
  activeTab.value = tabId
  sidebarOpen.value = false
  nextTick(() => {
    renderTabCharts(tabId)
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
    renderTabCharts(activeTab.value)
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
    renderTabCharts('portfolio')
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
// Shared ECharts Theme Constants (Mercury Palette)
// ────────────────────────────────────────────────────────────

const chartTooltip = {
  backgroundColor: 'rgba(15, 23, 42, 0.96)',
  borderColor: 'rgba(255, 255, 255, 0.08)',
  borderWidth: 1,
  textStyle: { color: '#E2E8F0', fontSize: 12, fontFamily: 'Inter, system-ui' },
}

const chartGrid = { top: 35, left: 60, right: 20, bottom: 30 }

const chartAxisLabel = { color: '#64748B', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }

const chartSplitLine = { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } }

const chartAxisLine = { lineStyle: { color: '#1E293B' } }

// Mercury accent palette
const ACCENT = {
  blue: '#38BDF8',
  indigo: '#6366F1',
  emerald: '#34D399',
  amber: '#FBBF24',
  rose: '#F43F5E',
  sky: '#0EA5E9',
  violet: '#8B5CF6',
  white: '#F8FAFC',
  slate: '#94A3B8',
}

// ────────────────────────────────────────────────────────────
// ECharts Render Functions (Mercury Institutional Theme)
// ────────────────────────────────────────────────────────────

function getOrCreateChart(domRef) {
  if (!domRef) return null
  if (domRef.clientWidth === 0 || domRef.clientHeight === 0) return null
  let chart = echarts.getInstanceByDom(domRef)
  if (!chart) {
    chart = markRaw(echarts.init(domRef))
    if (resizeObserver) {
      resizeObserver.observe(domRef)
    }
  }
  return chart
}

function renderHeroChart() {
  if (!heroChartRef.value || !deterministicData.value?.cash_flows) return
  heroChart = getOrCreateChart(heroChartRef.value)
  if (!heroChart) return

  const cfs = deterministicData.value.cash_flows
  const years = cfs.map(d => `Yr ${d.year + 1}`)

  let running = 0
  const cumLiability = cfs.map(d => {
    running += d.net_liability_cf
    return running
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    grid: { top: 30, left: 55, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: years, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 10)) }, splitLine: { show: false } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: chartSplitLine },
    series: [
      {
        name: 'Cumulative Liability',
        type: 'line',
        data: cumLiability,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.5, color: ACCENT.blue },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.25)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0.0)' },
          ]),
        },
      },
    ],
  }
  heroChart.setOption(option, true)
  heroChart.resize()
}

function renderReserveChart() {
  if (!reserveChartRef.value || !deterministicData.value?.reserve_profile) return
  reserveChart = getOrCreateChart(reserveChartRef.value)
  if (!reserveChart) return

  const profile = deterministicData.value.reserve_profile
  const durations = profile.map(r => `t=${r.duration}`)
  const prospective = profile.map(r => r.reserve_prospective)
  const retrospective = profile.map(r => r.reserve_retrospective)
  const gross = profile.map(r => r.gross_reserve)

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['Prospective', 'Retrospective', 'Gross GPV'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
    grid: chartGrid,
    xAxis: { type: 'category', data: durations, boundaryGap: false, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(durations.length / 8)) }, splitLine: { show: true, ...chartSplitLine } },
    yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: chartSplitLine },
    series: [
      {
        name: 'Prospective',
        type: 'line', data: prospective, smooth: true, symbol: 'circle', symbolSize: 3,
        lineStyle: { width: 2, color: ACCENT.blue },
        itemStyle: { color: ACCENT.blue },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(56, 189, 248, 0.18)' }, { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }]) },
      },
      { name: 'Retrospective', type: 'line', data: retrospective, smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: ACCENT.emerald, type: 'dashed' } },
      { name: 'Gross GPV', type: 'line', data: gross, smooth: true, symbol: 'none', lineStyle: { width: 1.5, color: ACCENT.amber } },
    ],
  }
  reserveChart.setOption(option, true)
  reserveChart.resize()
}

function renderFanChart() {
  if (!fanChartRef.value || (!stochasticData.value?.quantiles && !stochasticData.value?.fan_chart_rates)) return
  fanChart = getOrCreateChart(fanChartRef.value)
  if (!fanChart) return

  let years = [], p5 = [], p25 = [], p50 = [], p75 = [], p95 = []

  if (stochasticData.value.quantiles) {
    const q = stochasticData.value.quantiles
    const timesteps = stochasticData.value.timesteps || q.p50.map((_, i) => i)
    years = timesteps.map(t => `t=${t}`)
    p5 = q.p5.map(v => (v * 100).toFixed(2))
    p25 = q.p25.map(v => (v * 100).toFixed(2))
    p50 = q.p50.map(v => (v * 100).toFixed(2))
    p75 = q.p75.map(v => (v * 100).toFixed(2))
    p95 = q.p95.map(v => (v * 100).toFixed(2))
  } else {
    const rates = stochasticData.value.fan_chart_rates
    years = rates.map(d => `t=${d.year}`)
    p5 = rates.map(d => (d.p5 * 100).toFixed(2))
    p25 = rates.map(d => (d.p25 * 100).toFixed(2))
    p50 = rates.map(d => (d.p50 * 100).toFixed(2))
    p75 = rates.map(d => (d.p75 * 100).toFixed(2))
    p95 = rates.map(d => (d.p95 * 100).toFixed(2))
  }

  const sampleSeries = (stochasticData.value.sample_paths || []).slice(0, 10).map((path, idx) => ({
    name: `Trace ${idx + 1}`, type: 'line', data: path.map(r => (r * 100).toFixed(2)),
    smooth: true, symbol: 'none', lineStyle: { width: 0.7, color: 'rgba(148, 163, 184, 0.12)' }, silent: true,
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['p95', 'Median', 'p5'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
    grid: chartGrid,
    xAxis: { type: 'category', data: years, boundaryGap: false, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 8)) }, splitLine: { show: true, ...chartSplitLine } },
    yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `${v}%` }, splitLine: chartSplitLine },
    series: [
      ...sampleSeries,
      { name: 'p95', type: 'line', data: p95, smooth: true, symbol: 'none', lineStyle: { width: 1, color: 'rgba(99, 102, 241, 0.5)' }, areaStyle: { color: 'rgba(99, 102, 241, 0.08)' } },
      { name: 'p75', type: 'line', data: p75, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: 'rgba(99, 102, 241, 0.3)' }, areaStyle: { color: 'rgba(99, 102, 241, 0.1)' } },
      { name: 'Median', type: 'line', data: p50, smooth: true, symbol: 'none', lineStyle: { width: 2, color: ACCENT.blue } },
      { name: 'p25', type: 'line', data: p25, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: 'rgba(99, 102, 241, 0.3)' } },
      { name: 'p5', type: 'line', data: p5, smooth: true, symbol: 'none', lineStyle: { width: 1, color: 'rgba(99, 102, 241, 0.5)' } },
    ],
  }
  fanChart.setOption(option, true)
  fanChart.resize()
}

function renderCashFlowChart() {
  if (!cashFlowChartRef.value || !deterministicData.value?.cash_flows) return
  cashFlowChart = getOrCreateChart(cashFlowChartRef.value)
  if (!cashFlowChart) return

  const cfs = deterministicData.value.cash_flows
  const years = cfs.map(d => `Yr ${d.year + 1}`)
  const premiums = cfs.map(d => d.premium_income)
  const claims = cfs.map(d => d.death_claims + d.maturity_benefit)
  const expenses = cfs.map(d => d.total_expense)

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['Premiums', 'Claims', 'Expenses'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
    grid: chartGrid,
    xAxis: { type: 'category', data: years, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 8)) } },
    yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: chartSplitLine },
    series: [
      { name: 'Premiums', type: 'bar', data: premiums, itemStyle: { color: ACCENT.emerald, borderRadius: [3, 3, 0, 0] } },
      { name: 'Claims', type: 'bar', data: claims, itemStyle: { color: ACCENT.rose, borderRadius: [3, 3, 0, 0] } },
      { name: 'Expenses', type: 'bar', data: expenses, itemStyle: { color: ACCENT.amber, borderRadius: [3, 3, 0, 0] } },
    ],
  }
  cashFlowChart.setOption(option, true)
  cashFlowChart.resize()
}

function renderDistChart() {
  if (!distChartRef.value || (!stochasticData.value?.terminal_distribution && !stochasticData.value?.liability_histogram)) return
  distChart = getOrCreateChart(distChartRef.value)
  if (!distChart) return

  let bins = [], counts = []
  const var95 = stochasticData.value.var_95 || stochasticData.value.terminal_distribution?.var_95 || 0

  if (stochasticData.value.terminal_distribution) {
    const td = stochasticData.value.terminal_distribution
    const binEdges = td.bin_edges
    counts = td.counts.map((c, i) => {
      const mid = (binEdges[i] + binEdges[i + 1]) / 2.0
      return { value: c, itemStyle: { color: mid >= var95 ? ACCENT.rose : ACCENT.indigo, borderRadius: [2, 2, 0, 0] } }
    })
    bins = td.counts.map((_, i) => `$${((binEdges[i] + binEdges[i + 1]) / 2000.0).toFixed(1)}k`)
  } else {
    const hist = stochasticData.value.liability_histogram
    bins = hist.map(d => `$${(d.bin_mid / 1000).toFixed(1)}k`)
    counts = hist.map(d => ({ value: d.count, itemStyle: { color: d.bin_mid >= var95 ? ACCENT.rose : ACCENT.indigo, borderRadius: [2, 2, 0, 0] } }))
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    grid: { top: 25, left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: bins, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(bins.length / 8)) } },
    yAxis: { type: 'value', axisLabel: chartAxisLabel, splitLine: chartSplitLine },
    series: [{ name: 'Scenarios', type: 'bar', data: counts, barWidth: '85%' }],
  }
  distChart.setOption(option, true)
  distChart.resize()
}

function renderPortfolioCharts() {
  if (!portfolioData.value) return

  if (portfolioCfChartRef.value && portfolioData.value.annual_cash_flows) {
    portfolioCfChart = getOrCreateChart(portfolioCfChartRef.value)
    if (portfolioCfChart) {
      const cfs = portfolioData.value.annual_cash_flows
      const years = cfs.map(d => `Yr ${d.year}`)
      const premiums = cfs.map(d => d.premium_income)
      const claims = cfs.map(d => d.death_claims + d.maturity_benefits)
      const expenses = cfs.map(d => d.total_expenses)
      const netLiability = cfs.map(d => d.net_liability_cf)

      portfolioCfChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'axis' },
        legend: { data: ['Premiums', 'Claims', 'Expenses', 'Net Liability'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
        grid: { top: 40, left: 70, right: 20, bottom: 30 },
        xAxis: { type: 'category', data: years, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 10)) } },
        yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1_000_000).toFixed(1)}M` }, splitLine: chartSplitLine },
        series: [
          { name: 'Premiums', type: 'bar', stack: 'inflow', data: premiums, itemStyle: { color: ACCENT.emerald, borderRadius: [2, 2, 0, 0] } },
          { name: 'Claims', type: 'bar', stack: 'outflow', data: claims, itemStyle: { color: ACCENT.rose, borderRadius: [2, 2, 0, 0] } },
          { name: 'Expenses', type: 'bar', stack: 'outflow', data: expenses, itemStyle: { color: ACCENT.amber, borderRadius: [2, 2, 0, 0] } },
          { name: 'Net Liability', type: 'line', data: netLiability, smooth: true, symbol: 'none', lineStyle: { width: 2, color: ACCENT.blue } },
        ],
      }, true)
      portfolioCfChart.resize()
    }
  }

  if (portfolioProdChartRef.value && portfolioData.value.product_breakdown) {
    portfolioProdChart = getOrCreateChart(portfolioProdChartRef.value)
    if (portfolioProdChart) {
      const prodEntries = Object.entries(portfolioData.value.product_breakdown).map(([k, v]) => ({
        name: k.replace('_', ' ').toUpperCase(), value: v.sum_assured,
      }))
      portfolioProdChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'item' },
        legend: { orient: 'vertical', left: 'left', top: 'middle', textStyle: { color: ACCENT.slate, fontSize: 11 } },
        series: [{
          name: 'Face Amount', type: 'pie', radius: ['45%', '75%'], center: ['65%', '50%'],
          avoidLabelOverlap: false, itemStyle: { borderRadius: 4, borderColor: '#0F172A', borderWidth: 2 },
          label: { show: false }, data: prodEntries, color: [ACCENT.blue, ACCENT.indigo, ACCENT.emerald, ACCENT.amber],
        }],
      }, true)
      portfolioProdChart.resize()
    }
  }

  if (portfolioAgeChartRef.value && portfolioData.value.age_breakdown) {
    portfolioAgeChart = getOrCreateChart(portfolioAgeChartRef.value)
    if (portfolioAgeChart) {
      const ageEntries = Object.entries(portfolioData.value.age_breakdown)
      const categories = ageEntries.map(([k]) => k)
      const counts = ageEntries.map(([, v]) => v.count)
      const bels = ageEntries.map(([, v]) => v.bel)
      portfolioAgeChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'axis' },
        legend: { data: ['Count', 'BEL'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
        grid: { top: 40, left: 60, right: 55, bottom: 30 },
        xAxis: { type: 'category', data: categories, axisLine: chartAxisLine, axisLabel: chartAxisLabel },
        yAxis: [
          { type: 'value', name: 'Count', axisLabel: chartAxisLabel, splitLine: chartSplitLine },
          { type: 'value', name: 'BEL', axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: { show: false } },
        ],
        series: [
          { name: 'Count', type: 'bar', data: counts, itemStyle: { color: ACCENT.indigo, borderRadius: [3, 3, 0, 0] } },
          { name: 'BEL', type: 'line', yAxisIndex: 1, data: bels, smooth: true, itemStyle: { color: ACCENT.rose } },
        ],
      }, true)
      portfolioAgeChart.resize()
    }
  }
}

function renderIFRS17Charts() {
  if (!ifrs17Data.value) return

  if (ifrs17LrcChartRef.value && ifrs17Data.value.balance_sheet_schedule) {
    ifrs17LrcChart = getOrCreateChart(ifrs17LrcChartRef.value)
    if (ifrs17LrcChart) {
      const schedule = ifrs17Data.value.balance_sheet_schedule
      const durations = schedule.map(d => `t=${d.duration}`)
      const bels = schedule.map(d => d.bel)
      const ras = schedule.map(d => d.risk_adjustment)
      const csms = schedule.map(d => d.csm)
      const lrcs = schedule.map(d => d.total_lrc)

      ifrs17LrcChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'axis' },
        legend: { data: ['BEL', 'RA', 'CSM', 'Total LRC'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
        grid: chartGrid,
        xAxis: { type: 'category', data: durations, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(durations.length / 8)) } },
        yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: chartSplitLine },
        series: [
          { name: 'BEL', type: 'line', stack: 'Total', data: bels, areaStyle: { color: 'rgba(56, 189, 248, 0.25)' }, lineStyle: { width: 1.5, color: ACCENT.blue }, itemStyle: { color: ACCENT.blue }, symbol: 'none' },
          { name: 'RA', type: 'line', stack: 'Total', data: ras, areaStyle: { color: 'rgba(251, 191, 36, 0.3)' }, lineStyle: { width: 1.5, color: ACCENT.amber }, itemStyle: { color: ACCENT.amber }, symbol: 'none' },
          { name: 'CSM', type: 'line', stack: 'Total', data: csms, areaStyle: { color: 'rgba(99, 102, 241, 0.3)' }, lineStyle: { width: 1.5, color: ACCENT.indigo }, itemStyle: { color: ACCENT.indigo }, symbol: 'none' },
          { name: 'Total LRC', type: 'line', data: lrcs, smooth: true, lineStyle: { width: 2, color: ACCENT.white, type: 'dashed' }, itemStyle: { color: ACCENT.white }, symbol: 'none' },
        ],
      }, true)
      ifrs17LrcChart.resize()
    }
  }

  if (ifrs17PnlChartRef.value && ifrs17Data.value.income_statement_schedule) {
    ifrs17PnlChart = getOrCreateChart(ifrs17PnlChartRef.value)
    if (ifrs17PnlChart) {
      const pnl = ifrs17Data.value.income_statement_schedule
      const years = pnl.map(d => `Yr ${d.year + 1}`)

      ifrs17PnlChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'axis' },
        legend: { data: ['Revenue', 'Claims', 'Expenses', 'CSM Release', 'Service Result'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
        grid: chartGrid,
        xAxis: { type: 'category', data: years, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 8)) } },
        yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: chartSplitLine },
        series: [
          { name: 'Revenue', type: 'bar', data: pnl.map(d => d.insurance_revenue), itemStyle: { color: ACCENT.emerald, borderRadius: [3, 3, 0, 0] } },
          { name: 'Claims', type: 'bar', data: pnl.map(d => d.claims_incurred), itemStyle: { color: ACCENT.rose, borderRadius: [3, 3, 0, 0] } },
          { name: 'Expenses', type: 'bar', data: pnl.map(d => d.expenses_incurred), itemStyle: { color: ACCENT.amber, borderRadius: [3, 3, 0, 0] } },
          { name: 'CSM Release', type: 'line', data: pnl.map(d => d.csm_amortization), smooth: true, lineStyle: { width: 2, color: ACCENT.indigo }, itemStyle: { color: ACCENT.indigo } },
          { name: 'Service Result', type: 'line', data: pnl.map(d => d.insurance_service_result), smooth: true, lineStyle: { width: 2, color: ACCENT.blue }, itemStyle: { color: ACCENT.blue } },
        ],
      }, true)
      ifrs17PnlChart.resize()
    }
  }
}

function renderTornadoChart() {
  if (!tornadoChartRef.value || !sensitivityData.value?.tornado_items) return
  tornadoChart = getOrCreateChart(tornadoChartRef.value)
  if (!tornadoChart) return

  const items = [...sensitivityData.value.tornado_items].reverse()
  const factors = items.map(d => d.risk_factor)
  const lowDeltas = items.map(d => d.low_delta)
  const highDeltas = items.map(d => d.high_delta)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      ...chartTooltip, trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const idx = params[0].dataIndex
        const item = items[idx]
        return `<div style="font-weight:600;color:#F8FAFC;margin-bottom:4px">${item.risk_factor}</div>
          <div style="font-size:11px;color:#CBD5E1">
            <div><span style="color:${ACCENT.emerald}">Low (${item.low_label}):</span> ${formatCurrency(item.low_delta)} (${item.low_delta_pct > 0 ? '+' : ''}${item.low_delta_pct}%)</div>
            <div><span style="color:${ACCENT.rose}">High (${item.high_label}):</span> ${formatCurrency(item.high_delta)} (${item.high_delta_pct > 0 ? '+' : ''}${item.high_delta_pct}%)</div>
            <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:4px;margin-top:4px;color:${ACCENT.blue};font-weight:600">Swing: ${formatCurrency(item.swing)} (${item.swing_pct}%)</div>
          </div>`
      },
    },
    legend: { data: ['Downside', 'Upside'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
    grid: { top: 35, left: 220, right: 30, bottom: 20 },
    xAxis: { type: 'value', axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` }, splitLine: chartSplitLine },
    yAxis: { type: 'category', data: factors, axisLine: chartAxisLine, axisLabel: { color: '#CBD5E1', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }, splitLine: { show: false } },
    series: [
      { name: 'Downside', type: 'bar', data: lowDeltas, itemStyle: { borderRadius: [3, 3, 3, 3], color: ACCENT.blue } },
      { name: 'Upside', type: 'bar', data: highDeltas, itemStyle: { borderRadius: [3, 3, 3, 3], color: ACCENT.rose } },
    ],
  }
  tornadoChart.setOption(option, true)
  tornadoChart.resize()
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
  resizeObserver = new ResizeObserver(() => {
    const tab = activeTab.value
    if (['overview', 'reserves', 'stochastic', 'cashflows', 'table'].includes(tab)) {
      heroChart?.resize()
    }
    if (['overview', 'reserves'].includes(tab)) {
      reserveChart?.resize()
    }
    if (['overview', 'stochastic'].includes(tab)) {
      fanChart?.resize()
      distChart?.resize()
    }
    if (tab === 'cashflows') {
      cashFlowChart?.resize()
    }
    if (tab === 'ifrs17') {
      ifrs17LrcChart?.resize()
      ifrs17PnlChart?.resize()
    }
    if (tab === 'portfolio') {
      portfolioCfChart?.resize()
      portfolioProdChart?.resize()
      portfolioAgeChart?.resize()
    }
  })

  await checkBackendConnection()
  await executeValuation()
})

onUnmounted(() => {
  if (activeSocketConnection) {
    activeSocketConnection.close()
    activeSocketConnection = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
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
  heroChart = null
  reserveChart = null
  fanChart = null
  cashFlowChart = null
  distChart = null
  portfolioCfChart = null
  portfolioProdChart = null
  portfolioAgeChart = null
  ifrs17LrcChart = null
  ifrs17PnlChart = null
  tornadoChart = null
})
</script>

<template>
  <div class="min-h-screen bg-[#0B0F19] text-slate-100 font-sans selection:bg-sky-500/20">

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- SIDEBAR NAVIGATION                                     -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <aside :class="['sidebar', sidebarOpen ? 'open' : '']">
      <!-- Brand -->
      <div class="px-5 py-5 flex items-center space-x-3 border-b border-white/[0.06]">
        <div class="h-8 w-8 rounded-lg bg-sky-600 flex items-center justify-center flex-shrink-0">
          <svg class="h-4 w-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        </div>
        <div>
          <div class="text-sm font-semibold text-white tracking-tight">ValuaEngine</div>
          <div class="text-[10px] text-slate-500 font-medium">Actuarial Platform</div>
        </div>
      </div>

      <!-- Nav Items -->
      <nav class="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <button
          v-for="item in navItems"
          :key="item.id"
          @click="switchTab(item.id)"
          :class="['sidebar-nav-item w-full text-left', activeTab === item.id ? 'active' : '']"
        >
          <!-- Icons -->
          <svg v-if="item.icon === 'blueprint'" class="h-4 w-4 flex-shrink-0 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
          </svg>
          <svg v-else-if="item.icon === 'chart'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
          <svg v-else-if="item.icon === 'risk'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
          </svg>
          <svg v-else-if="item.icon === 'tornado'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <svg v-else-if="item.icon === 'balance'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0012 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 01-2.031.352 5.988 5.988 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.971zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0l2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 01-2.031.352 5.989 5.989 0 01-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.971z" />
          </svg>
          <svg v-else-if="item.icon === 'portfolio'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
          </svg>
          <svg v-else-if="item.icon === 'reserve'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
          </svg>
          <svg v-else-if="item.icon === 'cashflow'" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
          </svg>
          <svg v-else class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0112 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M10.875 12c-.621 0-1.125.504-1.125 1.125M12 12c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125m0-3.75c-.621 0-1.125.504-1.125 1.125" />
          </svg>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <!-- Sidebar Footer -->
      <div class="px-4 py-4 border-t border-white/[0.06]">
        <div class="flex items-center space-x-2.5">
          <div class="h-7 w-7 rounded-full bg-slate-700 flex items-center justify-center text-xs font-semibold text-white">A</div>
          <div>
            <div class="text-xs font-medium text-slate-300">Actuary</div>
            <div class="text-[10px] text-slate-500">Pro License</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- MAIN CONTENT AREA (offset by sidebar)                  -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div class="lg:ml-[240px]">

      <!-- ─── Top Header Bar ─── -->
      <header class="header-bar sticky top-0 z-30 px-6 h-14 flex items-center justify-between">
        <!-- Mobile hamburger -->
        <button @click="sidebarOpen = !sidebarOpen" class="lg:hidden mr-3 text-slate-400 hover:text-white">
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>

        <!-- Search Bar -->
        <div class="hidden sm:flex items-center flex-1 max-w-md">
          <div class="relative w-full">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input type="text" placeholder="Search policies, tables, runs..." class="input-field pl-9 pr-14 py-2 text-[13px]" readonly />
            <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded font-mono">⌘K</span>
          </div>
        </div>

        <!-- Right Actions -->
        <div class="flex items-center space-x-2.5">
          <button @click="executeValuation" :disabled="loading" class="btn-primary flex items-center space-x-1.5 text-[13px]">
            <svg :class="['h-3.5 w-3.5', loading ? 'animate-spin' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
            </svg>
            <span>{{ loading ? 'Running...' : 'Run Valuation' }}</span>
          </button>
          <button @click="showTableModal = true" class="btn-secondary flex items-center space-x-1.5 text-[13px]">
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            <span>Upload</span>
          </button>

          <!-- Status -->
          <div class="hidden md:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-[11px]">
            <span :class="['h-1.5 w-1.5 rounded-full', backendStatus === 'healthy' ? 'bg-emerald-400' : 'bg-rose-400']"></span>
            <span class="text-slate-400 font-medium">{{ backendStatus === 'healthy' ? 'Online' : 'Offline' }}</span>
          </div>
        </div>
      </header>

      <!-- ─── Mobile Sidebar Overlay ─── -->
      <div v-if="sidebarOpen" @click="sidebarOpen = false" class="fixed inset-0 bg-black/50 z-30 lg:hidden"></div>

      <!-- ─── Error Banner ─── -->
      <div v-if="errorMessage || backendStatus === 'error'" class="mx-6 mt-4">
        <div class="card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-rose-500/20">
          <div class="flex items-center space-x-2.5 text-sm">
            <span class="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
            <div>
              <span class="font-medium text-rose-400">Connection Error: </span>
              <span class="text-slate-400 text-xs">{{ errorMessage || 'FastAPI server unreachable at http://127.0.0.1:8000' }}</span>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <code class="text-[10px] text-slate-500 bg-black/30 px-2 py-1 rounded font-mono">uvicorn actuary_engine.api.main:app --port 8000</code>
            <button @click="executeValuation" class="btn-primary text-[11px] px-3 py-1">Retry</button>
          </div>
        </div>
      </div>

      <!-- ─── Simulation Progress Bar ─── -->
      <div v-if="isSimulating" class="mx-6 mt-4">
        <div class="card p-4 space-y-2">
          <div class="flex items-center justify-between text-xs">
            <div class="flex items-center space-x-2">
              <span class="h-2 w-2 rounded-full bg-sky-400 animate-pulse"></span>
              <span class="font-medium text-slate-200">Monte Carlo Simulation</span>
              <span class="text-slate-500 font-mono text-[11px]">({{ completedPaths.toLocaleString() }} / {{ totalPaths.toLocaleString() }} paths)</span>
            </div>
            <div class="flex items-center space-x-3">
              <span v-if="partialMetrics" class="text-slate-400 text-[11px]">
                Mean BEL: <strong class="text-emerald-400 font-mono">{{ formatCurrency(partialMetrics.mean_bel) }}</strong>
              </span>
              <span class="font-semibold text-sky-400 font-mono">{{ simProgress.toFixed(0) }}%</span>
            </div>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${simProgress}%` }"></div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- WELCOME HEADER + QUICK ACTIONS                         -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <div class="px-6 pt-6 pb-2">
        <h1 class="text-2xl font-semibold text-white tracking-tight">Dashboard</h1>
        <p class="text-sm text-slate-500 mt-1">Actuarial valuation, risk analytics, and regulatory reporting</p>

        <div class="mt-4 flex flex-wrap gap-2">
          <button @click="applyPreset('endowment_20')" class="btn-secondary text-[12px] px-3 py-1.5 rounded-md">20-Yr Endowment</button>
          <button @click="applyPreset('term_30')" class="btn-secondary text-[12px] px-3 py-1.5 rounded-md">30-Yr Term</button>
          <button @click="applyPreset('large_scale_10k')" class="btn-secondary text-[12px] px-3 py-1.5 rounded-md">10K Monte Carlo</button>
          <button @click="switchTab('sensitivity')" class="btn-secondary text-[12px] px-3 py-1.5 rounded-md">Sensitivity Shock</button>
          <button @click="switchTab('portfolio'); runSamplePortfolioDemo(1000)" class="btn-secondary text-[12px] px-3 py-1.5 rounded-md">Batch Portfolio</button>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- OVERVIEW TAB                                            -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <section v-show="['overview', 'reserves', 'stochastic', 'cashflows', 'table'].includes(activeTab)" class="px-6 py-4 space-y-5">

        <!-- Hero Card Row -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <!-- Primary Hero: Big KPI + Chart -->
          <div class="lg:col-span-2 card p-5">
            <div class="flex items-center justify-between mb-1">
              <div>
                <div class="text-xs text-slate-500 font-medium uppercase tracking-wider">Total Portfolio BEL</div>
                <div class="text-3xl font-semibold text-white mt-1 font-mono tracking-tight">
                  <span v-if="loading" class="skeleton inline-block w-40 h-8"></span>
                  <span v-else>{{ formatCurrency(stochasticData?.mean_bel ?? deterministicData?.bel) }}</span>
                </div>
                <div class="text-xs text-slate-500 mt-1 font-mono" v-if="stochasticData?.std_bel">
                  σ = {{ formatCurrency(stochasticData.std_bel) }}
                </div>
              </div>
              <div class="text-right space-y-1">
                <div class="badge badge-info">{{ deterministicData?.table_name || 'SOA ILT' }}</div>
                <div class="text-[11px] text-slate-500 font-mono capitalize">{{ form.product_type.replace('_', ' ') }}</div>
              </div>
            </div>
            <div ref="heroChartRef" class="w-full h-52 mt-2"></div>
          </div>

          <!-- Summary Cards Column -->
          <div class="space-y-4">
            <div class="card p-4">
              <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Annual Net Premium</div>
              <div class="text-xl font-semibold text-white mt-1 font-mono">
                <span v-if="loading" class="skeleton inline-block w-28 h-6"></span>
                <span v-else>{{ formatCurrency(deterministicData?.annual_net_premium) }}</span>
              </div>
              <div class="text-[11px] text-slate-500 mt-1">ä = {{ deterministicData?.annuity_factor?.toFixed(3) || '—' }}</div>
            </div>

            <div class="card p-4">
              <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">95% Value at Risk</div>
              <div class="text-xl font-semibold text-rose-400 mt-1 font-mono">
                <span v-if="loading" class="skeleton inline-block w-28 h-6"></span>
                <span v-else>{{ formatCurrency(stochasticData?.var_95) }}</span>
              </div>
              <div class="text-[11px] text-slate-500 mt-1">CVaR 95%: {{ formatCurrency(stochasticData?.cvar_95) }}</div>
            </div>

            <div class="card p-4">
              <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Gross Premium</div>
              <div class="text-xl font-semibold text-emerald-400 mt-1 font-mono">
                <span v-if="loading" class="skeleton inline-block w-28 h-6"></span>
                <span v-else>{{ formatCurrency(deterministicData?.annual_gross_premium) }}</span>
              </div>
              <div class="text-[11px] text-slate-500 mt-1">Acquisition &amp; Renewal Loaded</div>
            </div>
          </div>
        </div>

        <!-- Controls + Charts Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <!-- Control Sidebar (1/3) -->
          <div class="space-y-4">
            <div class="card p-5 space-y-4">
              <div class="text-xs font-semibold text-slate-300 uppercase tracking-wider pb-2 border-b border-white/[0.06]">Contract Parameters</div>

              <!-- Table Selection -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="text-[11px] text-slate-400 font-medium">Mortality Table</label>
                  <button @click="showTableModal = true" class="text-[11px] text-sky-400 hover:text-sky-300">+ Upload</button>
                </div>
                <select v-model="form.table_id" @change="executeValuation" class="input-field">
                  <option v-for="t in availableTables" :key="t.table_id" :value="t.table_id">
                    {{ t.name }} {{ t.is_builtin ? '(Built-in)' : '(Custom)' }}
                  </option>
                </select>
              </div>

              <!-- Product -->
              <div>
                <label class="text-[11px] text-slate-400 font-medium mb-1 block">Product Line</label>
                <select v-model="form.product_type" class="input-field">
                  <option value="endowment">Endowment Insurance</option>
                  <option value="term">Term Life Insurance</option>
                  <option value="whole_life">Whole Life Insurance</option>
                  <option value="pure_endowment">Pure Endowment</option>
                </select>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="text-[11px] text-slate-400 font-medium mb-1 block">Issue Age</label>
                  <input type="number" v-model.number="form.issue_age" min="0" max="100" class="input-field" />
                </div>
                <div v-if="form.product_type !== 'whole_life'">
                  <label class="text-[11px] text-slate-400 font-medium mb-1 block">Term (yrs)</label>
                  <input type="number" v-model.number="form.term" min="1" max="80" class="input-field" />
                </div>
              </div>

              <div>
                <label class="text-[11px] text-slate-400 font-medium mb-1 block">Sum Assured</label>
                <input type="number" v-model.number="form.sum_assured" step="50000" class="input-field" />
              </div>

              <!-- Economics -->
              <div class="pt-3 border-t border-white/[0.06] space-y-3">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Economics</div>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="text-[10px] text-slate-500 mb-1 block">Base Rate (i)</label>
                    <input type="number" v-model.number="form.interest_rate" step="0.005" min="0.01" max="0.20" class="input-field" />
                  </div>
                  <div>
                    <label class="text-[10px] text-slate-500 mb-1 block">Acquisition (α)</label>
                    <input type="number" v-model.number="form.expense.percent_of_premium_first" step="0.05" min="0" max="1.0" class="input-field" />
                  </div>
                </div>
              </div>

              <!-- Vasicek ESG -->
              <div class="pt-3 border-t border-white/[0.06] space-y-3">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Vasicek ESG</div>
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="text-[10px] text-slate-500 mb-1 block">κ (reversion)</label>
                    <input type="number" v-model.number="form.vasicek.kappa" step="0.05" class="input-field" />
                  </div>
                  <div>
                    <label class="text-[10px] text-slate-500 mb-1 block">θ (long-term)</label>
                    <input type="number" v-model.number="form.vasicek.theta" step="0.005" class="input-field" />
                  </div>
                  <div>
                    <label class="text-[10px] text-slate-500 mb-1 block">σ (volatility)</label>
                    <input type="number" v-model.number="form.vasicek.sigma" step="0.005" class="input-field" />
                  </div>
                  <div>
                    <label class="text-[10px] text-slate-500 mb-1 block">Paths (N)</label>
                    <select v-model.number="form.n_scenarios" class="input-field">
                      <option :value="1000">1,000</option>
                      <option :value="2500">2,500</option>
                      <option :value="5000">5,000</option>
                      <option :value="10000">10,000</option>
                      <option :value="25000">25,000</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- Dynamic Lapse Toggle -->
              <div class="pt-3 border-t border-white/[0.06] flex items-center justify-between">
                <div>
                  <div class="text-xs text-slate-300 font-medium">Dynamic Lapse</div>
                  <div class="text-[10px] text-slate-500">S-Curve Disintermediation</div>
                </div>
                <div @click="form.enable_dynamic_lapse = !form.enable_dynamic_lapse" :class="['toggle-track', form.enable_dynamic_lapse ? 'active' : '']">
                  <div class="toggle-thumb"></div>
                </div>
              </div>

              <!-- Run Button -->
              <button @click="executeValuation" :disabled="loading" class="btn-primary w-full py-2.5 flex items-center justify-center space-x-2 text-[13px] mt-2">
                <svg v-if="loading" class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                <span>{{ loading ? `Simulating (${simProgress.toFixed(0)}%)` : 'Run Valuation Engine' }}</span>
              </button>
            </div>
          </div>

          <!-- Charts Area (2/3) -->
          <div class="lg:col-span-2 space-y-5">
            <!-- Reserve Profile -->
            <div v-show="activeTab === 'overview' || activeTab === 'reserves'" class="card p-5">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <h3 class="text-sm font-semibold text-white">Reserve Profiles</h3>
                  <p class="text-[11px] text-slate-500">Prospective vs Retrospective vs Gross GPV</p>
                </div>
                <span class="badge badge-success">Verified</span>
              </div>
              <div ref="reserveChartRef" class="w-full h-72"></div>
            </div>

            <!-- Fan Chart -->
            <div v-show="activeTab === 'overview' || activeTab === 'stochastic'" class="card p-5">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <h3 class="text-sm font-semibold text-white">Short-Rate Fan Chart &amp; Quantile Bands</h3>
                  <p class="text-[11px] text-slate-500">{{ form.n_scenarios.toLocaleString() }} simulated paths — p5 through p95</p>
                </div>
                <span class="badge badge-info">Vasicek ESG</span>
              </div>
              <div v-if="!stochasticData && !loading" class="h-72 flex flex-col items-center justify-center text-center space-y-2.5 card-inset rounded-lg">
                <p class="text-slate-400 text-xs">No stochastic simulation data available.</p>
                <button @click="executeValuation" class="btn-primary text-xs px-3.5 py-1.5 rounded-md">
                  Run Valuation Engine
                </button>
              </div>
              <div v-show="stochasticData || loading" ref="fanChartRef" class="w-full h-72"></div>
            </div>

            <!-- Distribution -->
            <div v-show="activeTab === 'overview' || activeTab === 'stochastic'" class="card p-5">
              <div class="mb-3">
                <h3 class="text-sm font-semibold text-white">Liability Distribution &amp; Tail Risk</h3>
                <p class="text-[11px] text-slate-500">Empirical BEL density — VaR 95% threshold</p>
              </div>
              <div v-if="!stochasticData && !loading" class="h-72 flex flex-col items-center justify-center text-center space-y-2.5 card-inset rounded-lg">
                <p class="text-slate-400 text-xs">Empirical VaR/CVaR distribution will appear after valuation run.</p>
              </div>
              <div v-show="stochasticData || loading" ref="distChartRef" class="w-full h-72"></div>
            </div>

            <!-- Cash Flow -->
            <div v-show="activeTab === 'cashflows'" class="card p-5">
              <div class="mb-3">
                <h3 class="text-sm font-semibold text-white">Annual Cash Flow Breakdown</h3>
                <p class="text-[11px] text-slate-500">Premium inflows vs claims &amp; expense outflows</p>
              </div>
              <div ref="cashFlowChartRef" class="w-full h-72"></div>
            </div>

            <!-- Cohort Table -->
            <div v-show="activeTab === 'table'" class="card p-5">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h3 class="text-sm font-semibold text-white">Multi-Decrement Cohort Table</h3>
                  <p class="text-[11px] text-slate-500">{{ deterministicData?.cash_flows?.length || 0 }} projection periods</p>
                </div>
              </div>
              <div class="overflow-x-auto card-inset rounded-lg max-h-[500px]">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Year</th><th>Age</th><th>Inforce</th><th>Premium</th><th>Claims</th><th>Expenses</th><th>Net CF</th><th>PV Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in deterministicData?.cash_flows || []" :key="row.year">
                      <td class="text-sky-400 font-semibold">t={{ row.year }}</td>
                      <td>{{ row.age }}</td>
                      <td class="text-slate-500">{{ (row.inforce_boy * 100).toFixed(2) }}%</td>
                      <td class="text-emerald-400">{{ formatCurrency(row.premium_income) }}</td>
                      <td class="text-rose-400">{{ formatCurrency(row.death_claims + row.maturity_benefit) }}</td>
                      <td class="text-amber-400">{{ formatCurrency(row.total_expense) }}</td>
                      <td :class="row.net_liability_cf > 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'">{{ formatCurrency(row.net_liability_cf) }}</td>
                      <td :class="row.pv_net_liability > 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'">{{ formatCurrency(row.pv_net_liability) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- SENSITIVITY & STRESS TESTING TAB                       -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <section v-show="activeTab === 'sensitivity'" class="px-6 py-4 space-y-6">
        <!-- Interactive Real-Time Stress Testing Sliders & Trajectory -->
        <StressTestDashboard :contract-form="form" :is-active="activeTab === 'sensitivity'" ref="stressTestDashboardRef" />

        <!-- Compound Macro-Scenarios -->
        <div v-if="sensitivityData && sensitivityData.combined_scenarios && sensitivityData.combined_scenarios.length" class="card p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div>
              <h3 class="text-sm font-semibold text-white">Standard Compound Regulatory & Macro Stress Scenarios</h3>
              <p class="text-[11px] text-slate-500">Joint shocks evaluating severe economic & demographic downturns</p>
            </div>
            <span class="badge badge-warning">ERM Matrix</span>
          </div>
          <div class="overflow-x-auto card-inset rounded-lg max-h-[380px]">
            <table class="data-table">
              <thead>
                <tr><th>Scenario</th><th>Rate Shift</th><th>Mortality</th><th>Lapse</th><th>Expense</th><th>Shocked Reserve</th><th>Delta ($)</th><th>Solvency Risk</th></tr>
              </thead>
              <tbody>
                <tr v-for="sc in sensitivityData.combined_scenarios" :key="sc.scenario_id">
                  <td>
                    <div class="font-semibold text-white text-[11px]">{{ sc.name }}</div>
                    <div class="text-[10px] text-slate-500">{{ sc.description }}</div>
                  </td>
                  <td class="font-mono text-sky-400">{{ sc.rate_shift_bps > 0 ? '+' : '' }}{{ sc.rate_shift_bps }} bps</td>
                  <td class="font-mono text-slate-300">{{ (sc.mortality_multiplier * 100).toFixed(0) }}%</td>
                  <td class="font-mono text-slate-300">{{ (sc.lapse_multiplier * 100).toFixed(0) }}%</td>
                  <td class="font-mono text-slate-300">{{ (sc.expense_multiplier * 100).toFixed(0) }}%</td>
                  <td class="text-sky-400 font-semibold font-mono">{{ formatCurrency(sc.shocked_reserve) }}</td>
                  <td :class="['font-mono font-semibold', sc.delta_reserve > 0 ? 'text-rose-400' : 'text-emerald-400']">
                    {{ sc.delta_reserve > 0 ? '+' : '' }}{{ formatCurrency(sc.delta_reserve) }} ({{ formatPercent(sc.delta_pct) }})
                  </td>
                  <td>
                    <span :class="['badge', sc.solvency_impact === 'HIGH RISK' ? 'badge-danger' : sc.solvency_impact === 'MODERATE RISK' ? 'badge-warning' : 'badge-success']">
                      {{ sc.solvency_impact }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- IFRS 17 TAB                                            -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <section v-show="activeTab === 'ifrs17'" class="px-6 py-4 space-y-5">
        <!-- Initial Recognition KPIs -->
        <div v-if="ifrs17Data?.initial_balance" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Classification</div>
            <div class="mt-2">
              <span :class="['badge', ifrs17Data.initial_balance.classification === 'ONEROUS' ? 'badge-danger' : 'badge-success']">
                {{ ifrs17Data.initial_balance.classification }}
              </span>
            </div>
            <div class="text-[10px] text-slate-500 mt-2">Margin: {{ (ifrs17Data.initial_balance.profitability_margin * 100).toFixed(1) }}%</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">BEL</div>
            <div class="text-xl font-semibold text-sky-400 mt-1 font-mono">{{ formatCurrency(ifrs17Data.initial_balance.bel_0) }}</div>
            <div class="text-[10px] text-slate-500 mt-1">Best Estimate</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Risk Adj (RA)</div>
            <div class="text-xl font-semibold text-amber-400 mt-1 font-mono">{{ formatCurrency(ifrs17Data.initial_balance.ra_0) }}</div>
            <div class="text-[10px] text-slate-500 mt-1">Non-Financial Risk</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">CSM</div>
            <div class="text-xl font-semibold text-indigo-400 mt-1 font-mono">{{ formatCurrency(ifrs17Data.initial_balance.csm_0) }}</div>
            <div class="text-[10px] text-slate-500 mt-1">Unearned Profit</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Loss Component</div>
            <div class="text-xl font-semibold text-rose-400 mt-1 font-mono">{{ formatCurrency(ifrs17Data.initial_balance.loss_component_0) }}</div>
            <div class="text-[10px] text-slate-500 mt-1">Day 1 P&amp;L</div>
          </div>
        </div>

        <!-- Charts -->
        <div v-if="ifrs17Data" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div class="card p-5">
            <h3 class="text-sm font-semibold text-white mb-1">LRC Stacked Trajectory</h3>
            <p class="text-[11px] text-slate-500 mb-3">BEL + RA + CSM decomposition</p>
            <div ref="ifrs17LrcChartRef" class="w-full h-72"></div>
          </div>
          <div class="card p-5">
            <h3 class="text-sm font-semibold text-white mb-1">Insurance Service P&amp;L</h3>
            <p class="text-[11px] text-slate-500 mb-3">Revenue, claims, expenses, CSM release</p>
            <div ref="ifrs17PnlChartRef" class="w-full h-72"></div>
          </div>
        </div>

        <!-- Schedules -->
        <div v-if="ifrs17Data" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div class="card p-5">
            <h3 class="text-sm font-semibold text-white mb-1">Balance Sheet Schedule</h3>
            <p class="text-[11px] text-slate-500 mb-3">LRC roll-forward</p>
            <div class="overflow-x-auto card-inset rounded-lg max-h-[380px]">
              <table class="data-table">
                <thead><tr><th>Duration</th><th>BEL</th><th>RA</th><th>CSM</th><th>Total LRC</th></tr></thead>
                <tbody>
                  <tr v-for="row in ifrs17Data.balance_sheet_schedule" :key="row.duration">
                    <td class="text-sky-400 font-semibold">t={{ row.duration }}</td>
                    <td>{{ formatCurrency(row.bel) }}</td>
                    <td class="text-amber-400">{{ formatCurrency(row.risk_adjustment) }}</td>
                    <td class="text-indigo-400 font-semibold">{{ formatCurrency(row.csm) }}</td>
                    <td class="text-white font-semibold">{{ formatCurrency(row.total_lrc) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="card p-5">
            <h3 class="text-sm font-semibold text-white mb-1">Income Statement Schedule</h3>
            <p class="text-[11px] text-slate-500 mb-3">P&amp;L recognition</p>
            <div class="overflow-x-auto card-inset rounded-lg max-h-[380px]">
              <table class="data-table">
                <thead><tr><th>Year</th><th>Revenue</th><th>Expenses</th><th>CSM Release</th><th>Result</th></tr></thead>
                <tbody>
                  <tr v-for="row in ifrs17Data.income_statement_schedule" :key="row.year">
                    <td class="text-emerald-400 font-semibold">Yr {{ row.year + 1 }}</td>
                    <td class="text-emerald-400">{{ formatCurrency(row.insurance_revenue) }}</td>
                    <td class="text-rose-400">{{ formatCurrency(row.insurance_service_expenses) }}</td>
                    <td class="text-indigo-400 font-semibold">{{ formatCurrency(row.csm_amortization) }}</td>
                    <td :class="row.insurance_service_result >= 0 ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'">{{ formatCurrency(row.insurance_service_result) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- PORTFOLIO BATCH TAB                                     -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <section v-show="activeTab === 'portfolio'" class="px-6 py-4 space-y-5">
        <!-- Upload Card -->
        <div class="card p-5 space-y-4">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
            <div>
              <h2 class="text-base font-semibold text-white">Seriatim Portfolio Batch Valuation</h2>
              <p class="text-[11px] text-slate-500">Upload CSV or generate synthetic portfolios</p>
            </div>
            <button @click="runSamplePortfolioDemo(1000)" :disabled="portfolioLoading" class="btn-primary flex items-center space-x-1.5">
              <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
              </svg>
              <span>{{ portfolioLoading ? 'Processing...' : 'Quick Demo (1,000)' }}</span>
            </button>
          </div>

          <!-- Dropzone -->
          <div
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handlePortfolioDrop"
            :class="['border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition', isDragging ? 'border-sky-400 bg-sky-500/5' : 'border-white/[0.1] hover:border-sky-400/40 bg-[#0F172A]']"
            @click="$refs.fileInput.click()"
          >
            <input type="file" ref="fileInput" accept=".csv" class="hidden" @change="handlePortfolioFileUpload" />
            <div class="flex flex-col items-center space-y-2">
              <div class="h-10 w-10 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
              </div>
              <p class="text-sm text-slate-300">Drop your CSV here or <span class="text-sky-400">browse files</span></p>
              <p class="text-[10px] text-slate-500 font-mono">policy_id, issue_age, term_years, sum_assured, gross_premium, product_type</p>
            </div>
          </div>

          <div v-if="portfolioError" class="p-3 card-inset border-rose-500/20 text-rose-400 text-xs">{{ portfolioError }}</div>
        </div>

        <!-- Portfolio Summary -->
        <div v-if="portfolioData" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Policies</div>
            <div class="text-xl font-semibold text-white mt-1 font-mono">{{ portfolioData.total_policies.toLocaleString() }}</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Sum Assured</div>
            <div class="text-xl font-semibold text-sky-400 mt-1 font-mono">{{ formatCurrency(portfolioData.total_sum_assured) }}</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">PV Benefits</div>
            <div class="text-xl font-semibold text-rose-400 mt-1 font-mono">{{ formatCurrency(portfolioData.total_pvfb) }}</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">PV Premiums</div>
            <div class="text-xl font-semibold text-emerald-400 mt-1 font-mono">{{ formatCurrency(portfolioData.total_pvfp) }}</div>
          </div>
          <div class="card p-4">
            <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Total BEL</div>
            <div class="text-xl font-semibold text-indigo-400 mt-1 font-mono">{{ formatCurrency(portfolioData.total_bel) }}</div>
          </div>
        </div>

        <!-- Portfolio Charts -->
        <div v-if="portfolioData" class="space-y-5">
          <div class="card p-5">
            <h3 class="text-sm font-semibold text-white mb-1">Aggregate Cash Flow Projection</h3>
            <p class="text-[11px] text-slate-500 mb-3">Multi-year premium inflows, claims &amp; expenses</p>
            <div ref="portfolioCfChartRef" class="w-full h-72"></div>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div class="card p-5">
              <h3 class="text-sm font-semibold text-white mb-1">Product Composition</h3>
              <p class="text-[11px] text-slate-500 mb-2">Face amount distribution</p>
              <div ref="portfolioProdChartRef" class="w-full h-64"></div>
            </div>
            <div class="card p-5">
              <h3 class="text-sm font-semibold text-white mb-1">Age Cohort Breakdown</h3>
              <p class="text-[11px] text-slate-500 mb-2">Count &amp; BEL by age bracket</p>
              <div ref="portfolioAgeChartRef" class="w-full h-64"></div>
            </div>
          </div>
          <!-- Seriatim Table -->
          <div class="card p-5">
            <div class="flex items-center justify-between mb-4">
              <div>
                <h3 class="text-sm font-semibold text-white">Sample Seriatim Output</h3>
                <p class="text-[11px] text-slate-500">First {{ portfolioData.sample_seriatim?.length || 0 }} records</p>
              </div>
            </div>
            <div class="overflow-x-auto card-inset rounded-lg max-h-[420px]">
              <table class="data-table">
                <thead>
                  <tr><th>Policy ID</th><th>Product</th><th>Age</th><th>Term</th><th>Face Amount</th><th>Premium</th><th>PVFB</th><th>PVFP</th><th>Net BEL</th></tr>
                </thead>
                <tbody>
                  <tr v-for="pol in portfolioData.sample_seriatim" :key="pol.policy_id">
                    <td class="text-sky-400 font-semibold">{{ pol.policy_id }}</td>
                    <td class="uppercase text-[11px]">{{ pol.product_type }}</td>
                    <td>{{ pol.issue_age }}</td>
                    <td>{{ pol.term_years }} yrs</td>
                    <td>{{ formatCurrency(pol.sum_assured) }}</td>
                    <td class="text-emerald-400">{{ formatCurrency(pol.gross_premium) }}</td>
                    <td class="text-rose-400">{{ formatCurrency(pol.pvfb) }}</td>
                    <td class="text-emerald-400">{{ formatCurrency(pol.pvfp) }}</td>
                    <td :class="pol.bel > 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'">{{ formatCurrency(pol.bel) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- CONTRACT LOGIC BUILDER TAB                              -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <section v-show="activeTab === 'builder'" class="p-0">
        <ContractBuilderView />
      </section>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- UPLOAD TABLE MODAL                                      -->
      <!-- ═══════════════════════════════════════════════════════ -->
      <div v-if="showTableModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
        <div class="card max-w-lg w-full p-6 space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <h3 class="text-sm font-semibold text-white">Upload Mortality Table</h3>
            <button @click="showTableModal = false" class="text-slate-400 hover:text-white text-lg">✕</button>
          </div>

          <div v-if="uploadTableError" class="p-3 card-inset border-rose-500/20 text-rose-400 text-xs">{{ uploadTableError }}</div>

          <div class="space-y-3">
            <div>
              <label class="text-[11px] text-slate-400 font-medium mb-1 block">Table Name (Optional)</label>
              <input type="text" v-model="uploadTableName" placeholder="e.g. 2024 Experience Table" class="input-field" />
            </div>
            <div>
              <label class="text-[11px] text-slate-400 font-medium mb-1 block">Description</label>
              <input type="text" v-model="uploadTableDesc" placeholder="e.g. Corporate insured lives" class="input-field" />
            </div>

            <div
              @dragover.prevent="isTableDragging = true"
              @dragleave.prevent="isTableDragging = false"
              @drop.prevent="handleTableFileDrop"
              :class="['border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition', isTableDragging ? 'border-sky-400 bg-sky-500/5' : 'border-white/[0.1] bg-[#0F172A] hover:border-sky-400/40']"
              @click="$refs.tableFileInput.click()"
            >
              <input type="file" ref="tableFileInput" accept=".csv,.tsv,.txt,.xml,.xtbml" class="hidden" @change="handleTableFileSelect" />
              <div class="flex flex-col items-center space-y-1">
                <svg class="h-6 w-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <p class="text-xs text-slate-300">{{ uploadTableFile ? uploadTableFile.name : 'Drop file here or browse' }}</p>
                <p class="text-[10px] text-slate-500 font-mono">CSV (age,qx) or SOA XTbML (XML)</p>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-end space-x-2.5 pt-2">
            <button @click="showTableModal = false" class="btn-secondary">Cancel</button>
            <button @click="submitCustomTable" :disabled="uploadTableLoading" class="btn-primary">
              {{ uploadTableLoading ? 'Uploading...' : 'Upload & Use' }}
            </button>
          </div>
        </div>
      </div>

      <!-- ─── Footer ─── -->
      <footer class="border-t border-white/[0.06] py-5 mt-8">
        <div class="px-6 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-600 gap-2">
          <div class="flex items-center space-x-1.5">
            <span class="text-slate-400 font-medium">ValuaEngine</span>
            <span>·</span><span>IFRS 17</span><span>·</span><span>Monte Carlo ESG</span><span>·</span><span>Batch Portfolio</span>
          </div>
          <div>FastAPI · Vue 3 · ECharts · TailwindCSS</div>
        </div>
      </footer>
    </div>
  </div>
</template>
