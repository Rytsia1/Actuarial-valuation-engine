<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick, markRaw } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  deterministicData: {
    type: Object,
    default: null,
  },
  stochasticData: {
    type: Object,
    default: null,
  },
  form: {
    type: Object,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  isActive: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['run-valuation'])

// Chart refs
const heroChartRef = ref(null)
const miniReserveChartRef = ref(null)
const miniFanChartRef = ref(null)
const miniDistChartRef = ref(null)

let heroChart = null
let miniReserveChart = null
let miniFanChart = null
let miniDistChart = null
let resizeObserver = null

// Palette & constants
const ACCENT = {
  blue: '#38BDF8',
  indigo: '#6366F1',
  emerald: '#34D399',
  amber: '#FBBF24',
  rose: '#F43F5E',
  slate: '#94A3B8',
}

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

function formatCurrency(val) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val)
}

function getOrCreateChart(domRef) {
  if (!domRef || domRef.clientWidth === 0 || domRef.clientHeight === 0) return null
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
  if (!heroChartRef.value || !props.deterministicData?.cash_flows) return
  heroChart = getOrCreateChart(heroChartRef.value)
  if (!heroChart) return

  const cfs = props.deterministicData.cash_flows
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
    xAxis: {
      type: 'category',
      data: years,
      axisLine: chartAxisLine,
      axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 10)) },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` },
      splitLine: chartSplitLine,
    },
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

function renderMiniReserveChart() {
  if (!miniReserveChartRef.value || !props.deterministicData?.reserve_profile) return
  miniReserveChart = getOrCreateChart(miniReserveChartRef.value)
  if (!miniReserveChart) return

  const profile = props.deterministicData.reserve_profile
  const durations = profile.map(r => `t=${r.duration}`)
  const prospective = profile.map(r => r.reserve_prospective)
  const retrospective = profile.map(r => r.reserve_retrospective)
  const gross = profile.map(r => r.gross_reserve)

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: {
      data: ['Prospective', 'Retrospective', 'Gross GPV'],
      textStyle: { color: ACCENT.slate, fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: chartGrid,
    xAxis: {
      type: 'category',
      data: durations,
      boundaryGap: false,
      axisLine: chartAxisLine,
      axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(durations.length / 8)) },
      splitLine: { show: true, ...chartSplitLine },
    },
    yAxis: {
      type: 'value',
      axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` },
      splitLine: chartSplitLine,
    },
    series: [
      {
        name: 'Prospective',
        type: 'line',
        data: prospective,
        smooth: true,
        symbol: 'circle',
        symbolSize: 3,
        lineStyle: { width: 2, color: ACCENT.blue },
        itemStyle: { color: ACCENT.blue },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.18)' },
            { offset: 1, color: 'rgba(56, 189, 248, 0.0)' },
          ]),
        },
      },
      {
        name: 'Retrospective',
        type: 'line',
        data: retrospective,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: ACCENT.emerald, type: 'dashed' },
      },
      {
        name: 'Gross GPV',
        type: 'line',
        data: gross,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: ACCENT.amber },
      },
    ],
  }
  miniReserveChart.setOption(option, true)
  miniReserveChart.resize()
}

function renderMiniFanChart() {
  if (!miniFanChartRef.value || (!props.stochasticData?.quantiles && !props.stochasticData?.fan_chart_rates)) return
  miniFanChart = getOrCreateChart(miniFanChartRef.value)
  if (!miniFanChart) return

  let years = [], p5 = [], p25 = [], p50 = [], p75 = [], p95 = []

  if (props.stochasticData.quantiles) {
    const q = props.stochasticData.quantiles
    const timesteps = props.stochasticData.timesteps || q.p50.map((_, i) => i)
    years = timesteps.map(t => `t=${t}`)
    p5 = q.p5.map(v => (v * 100).toFixed(2))
    p25 = q.p25.map(v => (v * 100).toFixed(2))
    p50 = q.p50.map(v => (v * 100).toFixed(2))
    p75 = q.p75.map(v => (v * 100).toFixed(2))
    p95 = q.p95.map(v => (v * 100).toFixed(2))
  } else {
    const rates = props.stochasticData.fan_chart_rates
    years = rates.map(d => `t=${d.year}`)
    p5 = rates.map(d => (d.p5 * 100).toFixed(2))
    p25 = rates.map(d => (d.p25 * 100).toFixed(2))
    p50 = rates.map(d => (d.p50 * 100).toFixed(2))
    p75 = rates.map(d => (d.p75 * 100).toFixed(2))
    p95 = rates.map(d => (d.p95 * 100).toFixed(2))
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: { data: ['p95', 'Median', 'p5'], textStyle: { color: ACCENT.slate, fontSize: 11 }, top: 0, right: 10 },
    grid: chartGrid,
    xAxis: {
      type: 'category',
      data: years,
      boundaryGap: false,
      axisLine: chartAxisLine,
      axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 8)) },
      splitLine: { show: true, ...chartSplitLine },
    },
    yAxis: { type: 'value', axisLabel: { ...chartAxisLabel, formatter: v => `${v}%` }, splitLine: chartSplitLine },
    series: [
      { name: 'p95', type: 'line', data: p95, smooth: true, symbol: 'none', lineStyle: { width: 1, color: 'rgba(99, 102, 241, 0.5)' }, areaStyle: { color: 'rgba(99, 102, 241, 0.08)' } },
      { name: 'p75', type: 'line', data: p75, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: 'rgba(99, 102, 241, 0.3)' }, areaStyle: { color: 'rgba(99, 102, 241, 0.1)' } },
      { name: 'Median', type: 'line', data: p50, smooth: true, symbol: 'none', lineStyle: { width: 2, color: ACCENT.blue } },
      { name: 'p25', type: 'line', data: p25, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: 'rgba(99, 102, 241, 0.3)' } },
      { name: 'p5', type: 'line', data: p5, smooth: true, symbol: 'none', lineStyle: { width: 1, color: 'rgba(99, 102, 241, 0.5)' } },
    ],
  }
  miniFanChart.setOption(option, true)
  miniFanChart.resize()
}

function renderMiniDistChart() {
  if (!miniDistChartRef.value || (!props.stochasticData?.terminal_distribution && !props.stochasticData?.liability_histogram)) return
  miniDistChart = getOrCreateChart(miniDistChartRef.value)
  if (!miniDistChart) return

  let bins = [], counts = []
  const var95 = props.stochasticData.var_95 || props.stochasticData.terminal_distribution?.var_95 || 0

  if (props.stochasticData.terminal_distribution) {
    const td = props.stochasticData.terminal_distribution
    const binEdges = td.bin_edges
    counts = td.counts.map((c, i) => {
      const mid = (binEdges[i] + binEdges[i + 1]) / 2.0
      return { value: c, itemStyle: { color: mid >= var95 ? ACCENT.rose : ACCENT.indigo, borderRadius: [2, 2, 0, 0] } }
    })
    bins = td.counts.map((_, i) => `$${((binEdges[i] + binEdges[i + 1]) / 2000.0).toFixed(1)}k`)
  } else {
    const hist = props.stochasticData.liability_histogram
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
  miniDistChart.setOption(option, true)
  miniDistChart.resize()
}

function renderAllCharts() {
  if (!props.isActive) return
  renderHeroChart()
  renderMiniReserveChart()
  renderMiniFanChart()
  renderMiniDistChart()
}

watch(
  () => [props.deterministicData, props.stochasticData, props.isActive],
  () => {
    if (props.isActive) {
      nextTick(() => {
        renderAllCharts()
      })
    }
  },
  { deep: true }
)

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    if (props.isActive) {
      heroChart?.resize()
      miniReserveChart?.resize()
      miniFanChart?.resize()
      miniDistChart?.resize()
    }
  })
  if (props.isActive) {
    nextTick(renderAllCharts)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  heroChart?.dispose()
  miniReserveChart?.dispose()
  miniFanChart?.dispose()
  miniDistChart?.dispose()
})
</script>

<template>
  <div class="space-y-5">
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

    <!-- Secondary Charts Overview -->
    <div class="space-y-5">
      <!-- Reserve Profile Card -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-semibold text-white">Reserve Profiles</h3>
            <p class="text-[11px] text-slate-500">Prospective vs Retrospective vs Gross GPV</p>
          </div>
          <span class="badge badge-success">Verified</span>
        </div>
        <div ref="miniReserveChartRef" class="w-full h-64"></div>
      </div>

      <!-- Fan Chart Card -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-semibold text-white">Short-Rate Fan Chart &amp; Quantile Bands</h3>
            <p class="text-[11px] text-slate-500">{{ form.n_scenarios.toLocaleString() }} simulated paths — p5 through p95</p>
          </div>
          <span class="badge badge-info">Vasicek ESG</span>
        </div>
        <div v-if="!stochasticData && !loading" class="h-64 flex flex-col items-center justify-center text-center space-y-2.5 card-inset rounded-lg">
          <p class="text-slate-400 text-xs">No stochastic simulation data available.</p>
          <button @click="emit('run-valuation')" type="button" class="btn-primary text-xs px-3.5 py-1.5 rounded-md">
            Run Valuation Engine
          </button>
        </div>
        <div v-show="stochasticData || loading" ref="miniFanChartRef" class="w-full h-64"></div>
      </div>

      <!-- Distribution Card -->
      <div class="card p-5">
        <div class="mb-3">
          <h3 class="text-sm font-semibold text-white">Liability Distribution &amp; Tail Risk</h3>
          <p class="text-[11px] text-slate-500">Empirical BEL density — VaR 95% threshold</p>
        </div>
        <div v-if="!stochasticData && !loading" class="h-64 flex flex-col items-center justify-center text-center space-y-2.5 card-inset rounded-lg">
          <p class="text-slate-400 text-xs">Empirical VaR/CVaR distribution will appear after valuation run.</p>
        </div>
        <div v-show="stochasticData || loading" ref="miniDistChartRef" class="w-full h-64"></div>
      </div>
    </div>
  </div>
</template>
