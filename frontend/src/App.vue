<script setup>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  fetchHealth,
  runDeterministicValuation,
  runStochasticValuation,
} from './api/client'

// ────────────────────────────────────────────────────────────
// State Management
// ────────────────────────────────────────────────────────────

const activeTab = ref('overview') // 'overview', 'reserves', 'stochastic', 'cashflows', 'table'
const backendStatus = ref('checking') // 'healthy', 'error', 'checking'
const loading = ref(false)
const errorMessage = ref(null)

// Form Parameters with standard actuarial defaults
const form = reactive({
  product_type: 'endowment',
  issue_age: 30,
  term: 20,
  sum_assured: 1000000,
  premium_paying_term: null,
  interest_rate: 0.05,
  gross_premium: null,
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
  n_scenarios: 2500,
  seed: 42,
})

// Valuation Results
const deterministicData = ref(null)
const stochasticData = ref(null)

// Chart DOM refs & instances
const heroChartRef = ref(null)
const reserveChartRef = ref(null)
const fanChartRef = ref(null)
const cashFlowChartRef = ref(null)
const distChartRef = ref(null)

let heroChart = null
let reserveChart = null
let fanChart = null
let cashFlowChart = null
let distChart = null
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
  } else if (type === 'high_volatility') {
    form.product_type = 'endowment'
    form.issue_age = 25
    form.term = 20
    form.sum_assured = 1000000
    form.vasicek.sigma = 0.035
    form.vasicek.kappa = 0.35
    form.enable_dynamic_lapse = true
  }
  executeValuation()
}

// ────────────────────────────────────────────────────────────
// API Communication & Valuation Orchestrator
// ────────────────────────────────────────────────────────────

async function checkBackend() {
  try {
    const health = await fetchHealth()
    backendStatus.value = health.status === 'healthy' ? 'healthy' : 'error'
  } catch (err) {
    console.warn('Backend connection failed:', err)
    backendStatus.value = 'error'
  }
}

async function executeValuation() {
  loading.value = true
  errorMessage.value = null

  try {
    const detPayload = {
      product_type: form.product_type,
      issue_age: form.issue_age,
      term: form.product_type === 'whole_life' ? null : form.term,
      sum_assured: form.sum_assured,
      premium_paying_term: form.premium_paying_term,
      interest_rate: form.interest_rate,
      gross_premium: form.gross_premium,
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
      vasicek: form.vasicek,
      dynamic_lapse: form.enable_dynamic_lapse ? form.dynamic_lapse : null,
      expense: form.expense,
      n_scenarios: form.n_scenarios,
      seed: form.seed,
    }

    const [detRes, stochRes] = await Promise.all([
      runDeterministicValuation(detPayload),
      runStochasticValuation(stochPayload),
    ])

    deterministicData.value = detRes
    stochasticData.value = stochRes
    backendStatus.value = 'healthy'

    await nextTick()
    renderAllCharts()
  } catch (err) {
    console.error('Valuation error:', err)
    errorMessage.value = err.message || 'Valuation failed. Please ensure FastAPI is running on port 8000.'
  } finally {
    loading.value = false
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

  // Compute cumulative net liability
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
      formatter: params => {
        const item = params[0]
        const dataPoint = cfs[item.dataIndex]
        return `
          <div class="font-bold text-fuchsia-400 pb-1 mb-1 border-b border-slate-700">${item.axisValue} (Age ${dataPoint.age})</div>
          <div class="flex justify-between space-x-4 py-0.5 text-xs">
            <span class="text-slate-400">Premium Inflow:</span>
            <span class="text-emerald-400 font-mono font-semibold">${formatCurrency(dataPoint.premium_income)}</span>
          </div>
          <div class="flex justify-between space-x-4 py-0.5 text-xs">
            <span class="text-slate-400">Claims & Exp Outgo:</span>
            <span class="text-rose-400 font-mono font-semibold">${formatCurrency(dataPoint.death_claims + dataPoint.total_expense + dataPoint.maturity_benefit)}</span>
          </div>
          <div class="flex justify-between space-x-4 py-0.5 text-xs border-t border-slate-800 mt-1 pt-1 font-bold">
            <span class="text-sky-300">Net Annual CF:</span>
            <span class="${dataPoint.net_liability_cf > 0 ? 'text-rose-400' : 'text-emerald-400'} font-mono">${formatCurrency(dataPoint.net_liability_cf)}</span>
          </div>
        `
      },
    },
    grid: {
      top: 30,
      left: 65,
      right: 25,
      bottom: 35,
    },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        interval: Math.max(1, Math.floor(years.length / 10)),
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        formatter: v => `$${(v / 1000).toFixed(0)}k`,
      },
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
        lineStyle: {
          width: 2.5,
          color: '#38bdf8',
          shadowColor: 'rgba(56, 189, 248, 0.5)',
          shadowBlur: 10,
        },
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
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11, 15, 25, 0.95)',
      borderColor: 'rgba(56, 189, 248, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
    },
    legend: {
      data: ['Prospective Reserve (_t V)', 'Retrospective Reserve (_t V_retro)', 'Gross GPV Reserve'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: { top: 40, left: 65, right: 25, bottom: 35 },
    xAxis: {
      type: 'category',
      data: durations,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        interval: Math.max(1, Math.floor(durations.length / 8)),
      },
      splitLine: { show: true, lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        formatter: v => `$${(v / 1000).toFixed(0)}k`,
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
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
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.28)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0.0)' },
          ]),
        },
      },
      {
        name: 'Retrospective Reserve (_t V_retro)',
        type: 'line',
        data: retrospective,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#34d399', type: 'dashed' },
        itemStyle: { color: '#34d399' },
      },
      {
        name: 'Gross GPV Reserve',
        type: 'line',
        data: gross,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#fb923c' },
        itemStyle: { color: '#fb923c' },
      },
    ],
  }
  reserveChart.setOption(option, true)
}

function renderFanChart() {
  if (!fanChartRef.value || !stochasticData.value?.fan_chart_rates) return
  if (!fanChart) fanChart = echarts.init(fanChartRef.value)

  const rates = stochasticData.value.fan_chart_rates
  const years = rates.map(d => `t=${d.year}`)
  const p5 = rates.map(d => (d.p5 * 100).toFixed(2))
  const p25 = rates.map(d => (d.p25 * 100).toFixed(2))
  const p50 = rates.map(d => (d.p50 * 100).toFixed(2))
  const p75 = rates.map(d => (d.p75 * 100).toFixed(2))
  const p95 = rates.map(d => (d.p95 * 100).toFixed(2))
  const mean = rates.map(d => (d.mean * 100).toFixed(2))

  const sampleSeries = (stochasticData.value.sample_paths || []).slice(0, 8).map((path, idx) => ({
    name: `Sample ${idx + 1}`,
    type: 'line',
    data: path.map(r => (r * 100).toFixed(2)),
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 0.8, color: 'rgba(255, 255, 255, 0.15)' },
    silent: true,
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11, 15, 25, 0.95)',
      borderColor: 'rgba(168, 85, 247, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
    },
    legend: {
      data: ['95% Upper Bound', 'Median (p50)', 'Mean Rate', '5% Lower Bound'],
      textStyle: { color: '#94a3b8', fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: { top: 40, left: 55, right: 25, bottom: 35 },
    xAxis: {
      type: 'category',
      data: years,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(years.length / 8)) },
      splitLine: { show: true, lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', formatter: v => `${v}%` },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
    series: [
      ...sampleSeries,
      {
        name: '95% Upper Bound',
        type: 'line',
        data: p95,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#f43f5e' },
        areaStyle: { color: 'rgba(244, 63, 94, 0.12)' },
      },
      {
        name: 'p75',
        type: 'line',
        data: p75,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: 'rgba(236, 72, 153, 0.5)' },
        areaStyle: { color: 'rgba(236, 72, 153, 0.16)' },
      },
      {
        name: 'Median (p50)',
        type: 'line',
        data: p50,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.5, color: '#38bdf8', shadowColor: 'rgba(56, 189, 248, 0.6)', shadowBlur: 8 },
      },
      {
        name: 'Mean Rate',
        type: 'line',
        data: mean,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#fbbf24', type: 'dashed' },
      },
      {
        name: 'p25',
        type: 'line',
        data: p25,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: 'rgba(236, 72, 153, 0.5)' },
      },
      {
        name: '5% Lower Bound',
        type: 'line',
        data: p5,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#a855f7' },
      },
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
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11, 15, 25, 0.95)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
    },
    legend: {
      data: ['Premium Income', 'Claims & Benefits', 'Expenses'],
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
      {
        name: 'Premium Income',
        type: 'bar',
        data: premiums,
        itemStyle: { color: '#34d399', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: 'Claims & Benefits',
        type: 'bar',
        data: claims,
        itemStyle: { color: '#f43f5e', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: 'Expenses',
        type: 'bar',
        data: expenses,
        itemStyle: { color: '#fb923c', borderRadius: [3, 3, 0, 0] },
      },
    ],
  }
  cashFlowChart.setOption(option, true)
}

function renderDistChart() {
  if (!distChartRef.value || !stochasticData.value?.liability_histogram) return
  if (!distChart) distChart = echarts.init(distChartRef.value)

  const hist = stochasticData.value.liability_histogram
  const var95 = stochasticData.value.var_95
  const bins = hist.map(d => `$${(d.bin_mid / 1000).toFixed(1)}k`)
  const counts = hist.map(d => ({
    value: d.count,
    itemStyle: {
      color: d.bin_mid >= var95 ? '#f43f5e' : '#a855f7',
      shadowColor: d.bin_mid >= var95 ? 'rgba(244, 63, 94, 0.4)' : 'rgba(168, 85, 247, 0.3)',
      shadowBlur: 6,
    },
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(11, 15, 25, 0.95)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12, fontFamily: 'JetBrains Mono' },
    },
    grid: { top: 30, left: 55, right: 25, bottom: 35 },
    xAxis: {
      type: 'category',
      data: bins,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono', interval: Math.max(1, Math.floor(bins.length / 8)) },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8', fontSize: 10, fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
    series: [
      {
        name: 'Scenarios',
        type: 'bar',
        data: counts,
        barWidth: '85%',
        itemStyle: { borderRadius: [3, 3, 0, 0] },
      },
    ],
  }
  distChart.setOption(option, true)
}

function renderAllCharts() {
  renderHeroChart()
  renderReserveChart()
  renderFanChart()
  renderCashFlowChart()
  renderDistChart()
}

// ────────────────────────────────────────────────────────────
// Lifecycle Hooks
// ────────────────────────────────────────────────────────────

onMounted(async () => {
  await checkBackend()
  await executeValuation()

  resizeObserver = new ResizeObserver(() => {
    heroChart?.resize()
    reserveChart?.resize()
    fanChart?.resize()
    cashFlowChart?.resize()
    distChart?.resize()
  })

  if (heroChartRef.value) resizeObserver.observe(heroChartRef.value)
  if (reserveChartRef.value) resizeObserver.observe(reserveChartRef.value)
  if (fanChartRef.value) resizeObserver.observe(fanChartRef.value)
  if (cashFlowChartRef.value) resizeObserver.observe(cashFlowChartRef.value)
  if (distChartRef.value) resizeObserver.observe(distChartRef.value)
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
  heroChart?.dispose()
  reserveChart?.dispose()
  fanChart?.dispose()
  cashFlowChart?.dispose()
  distChart?.dispose()
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
              { id: 'reserves', label: 'Policy Reserves (_t V)' },
              { id: 'stochastic', label: 'Vasicek ESG & VaR' },
              { id: 'cashflows', label: 'Cashflow Waterfall' },
              { id: 'table', label: 'Cohort Table' }
            ]"
            :key="tab.id"
            @click="activeTab = tab.id; nextTick(() => renderAllCharts())"
            :class="[
              'px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-200',
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
                backendStatus === 'healthy' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-rose-400'
              ]"
            ></span>
            <span class="text-slate-300 text-[11px]">SOA ILT (ω=110)</span>
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
              <span>{{ loading ? 'Computing...' : 'Recalculate' }}</span>
            </span>
          </button>
        </div>
      </div>
    </header>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 2. Hero Headline Section & Feature Badges -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-4 text-center relative z-10">
      <!-- Feature Pills -->
      <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/[0.04] border border-fuchsia-500/20 backdrop-blur-xl mb-4 shadow-[0_0_20px_rgba(236,72,153,0.15)]">
        <span class="h-1.5 w-1.5 rounded-full bg-fuchsia-400 animate-pulse"></span>
        <span class="text-xs font-medium text-slate-300">Deterministic & Stochastic Valuation Engine</span>
        <span class="text-[10px] text-fuchsia-400 font-mono">⚡ Vectorized NumPy</span>
      </div>

      <!-- Main Headline -->
      <h1 class="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight">
        The fastest way to <span class="text-transparent bg-clip-text bg-gradient-to-r from-fuchsia-400 via-rose-400 to-amber-300">model, value & stress-test</span> actuarial liabilities.
      </h1>
      <p class="mt-3 text-sm text-slate-400 max-w-2xl mx-auto font-mono">
        Prospective reserves ${_t V}$, Fackler recurrence, multi-decrement GPV, and Vasicek Monte Carlo risk simulation.
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
          @click="applyPreset('whole_life')"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-sky-500/20 border border-white/[0.08] hover:border-sky-500/40 text-slate-300 transition"
        >
          ♾️ Whole Life ($500k)
        </button>
        <button
          @click="applyPreset('high_volatility')"
          class="px-3 py-1 rounded-lg text-xs font-mono font-medium bg-white/[0.04] hover:bg-amber-500/20 border border-white/[0.08] hover:border-amber-500/40 text-slate-300 transition"
        >
          🔥 High Volatility Stress
        </button>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 3. Hero Visualizer Card (Showcase Bar Chart) -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 relative z-10">
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

          <!-- Right: Hero KPI Table (Inspired by Reference UI Right Panel) -->
          <div class="bg-black/40 rounded-xl p-5 border border-white/[0.06] space-y-4 font-mono text-xs">
            <div class="text-[11px] uppercase tracking-wider text-slate-400 font-bold border-b border-slate-800 pb-2 flex items-center justify-between">
              <span>Valuation Summary</span>
              <span class="text-fuchsia-400">Live Solvency</span>
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
    <!-- 4. Top KPI Metric Cards Strip -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 relative z-10">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Metric 1 -->
        <div class="neon-glass rounded-2xl p-4 border border-white/[0.08] relative overflow-hidden group hover:border-sky-500/40 transition">
          <div class="flex justify-between items-center text-xs font-mono text-slate-400 mb-1">
            <span>ANNUAL NET PREMIUM (P)</span>
            <span class="text-sky-400">ä = {{ deterministicData?.annuity_factor?.toFixed(3) || '—' }}</span>
          </div>
          <div class="text-2xl font-bold font-mono text-white mt-1">
            {{ formatCurrency(deterministicData?.annual_net_premium) }}
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
            {{ formatCurrency(deterministicData?.annual_gross_premium) }}
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
            {{ formatCurrency(stochasticData?.mean_bel ?? deterministicData?.bel) }}
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
            {{ formatCurrency(stochasticData?.var_95) }}
          </div>
          <div class="text-[11px] text-slate-400 font-mono mt-1">CVaR 95%: {{ formatCurrency(stochasticData?.cvar_95) }}</div>
        </div>
      </div>
    </section>

    <!-- ──────────────────────────────────────────────────────────── -->
    <!-- 5. Main Workspace Layout (Sidebar Controls + Multi-Chart Workspace) -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 relative z-10">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Control Deck Sidebar (1/3) -->
        <div class="lg:col-span-1 space-y-6">
          <div class="neon-glass rounded-2xl p-5 border border-white/[0.08] space-y-5">
            <div class="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <h2 class="text-xs font-bold font-mono uppercase tracking-wider text-fuchsia-400 flex items-center space-x-2">
                <span>⚙️ Contract & ESG Controls</span>
              </h2>
              <span class="text-[10px] font-mono text-slate-400">Interactive</span>
            </div>

            <!-- Product Contract -->
            <div class="space-y-3">
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

            <!-- Vasicek ESG Parameters -->
            <div class="space-y-3 border-t border-white/[0.08] pt-4">
              <h3 class="text-xs font-mono font-bold text-rose-400 uppercase tracking-wider">
                Vasicek ESG Model
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
              <span>{{ loading ? 'Running Simulation...' : 'Simulate & Value' }}</span>
            </button>
          </div>
        </div>

        <!-- Center/Right Multi-Chart Display Workspace (2/3) -->
        <div class="lg:col-span-2 space-y-6">
          <!-- View 1: Overview (Reserves + Fan Chart) -->
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
                    Detailed probability-weighted cashflows and discounted liabilities.
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
    <!-- 6. Footer -->
    <!-- ──────────────────────────────────────────────────────────── -->
    <footer class="border-t border-white/[0.08] bg-[#030712] py-6 mt-12 relative z-10">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs font-mono text-slate-500 gap-2">
        <div class="flex items-center space-x-2">
          <span class="text-fuchsia-400">ACTUARY ENGINE</span>
          <span>•</span>
          <span>SOA Illustrative Life Table (ω=110)</span>
          <span>•</span>
          <span>Vasicek ESG</span>
        </div>
        <div>FastAPI • Vue 3 • Apache ECharts • TailwindCSS</div>
      </div>
    </footer>
  </div>
</template>
