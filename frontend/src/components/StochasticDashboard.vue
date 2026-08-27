<script setup>
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

const props = defineProps({
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
  error: {
    type: String,
    default: null,
  },
  isActive: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['run-valuation'])

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

const fanChartOption = computed(() => {
  const stoch = props.stochasticData
  if (!stoch || (!stoch.quantiles && !stoch.fan_chart_rates)) return null

  let years = [], p5 = [], p25 = [], p50 = [], p75 = [], p95 = []

  if (stoch.quantiles) {
    const q = stoch.quantiles
    const timesteps = stoch.timesteps || q.p50.map((_, i) => i)
    years = timesteps.map(t => `t=${t}`)
    p5 = q.p5.map(v => (v * 100).toFixed(2))
    p25 = q.p25.map(v => (v * 100).toFixed(2))
    p50 = q.p50.map(v => (v * 100).toFixed(2))
    p75 = q.p75.map(v => (v * 100).toFixed(2))
    p95 = q.p95.map(v => (v * 100).toFixed(2))
  } else {
    const rates = stoch.fan_chart_rates
    years = rates.map(d => `t=${d.year}`)
    p5 = rates.map(d => (d.p5 * 100).toFixed(2))
    p25 = rates.map(d => (d.p25 * 100).toFixed(2))
    p50 = rates.map(d => (d.p50 * 100).toFixed(2))
    p75 = rates.map(d => (d.p75 * 100).toFixed(2))
    p95 = rates.map(d => (d.p95 * 100).toFixed(2))
  }

  return {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: {
      data: ['p95', 'p75', 'Median (p50)', 'p25', 'p5'],
      textStyle: { color: ACCENT.slate, fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: chartGrid,
    xAxis: {
      type: 'category',
      data: years,
      boundaryGap: false,
      axisLine: chartAxisLine,
      axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 8)) },
      splitLine: { show: true, ...chartSplitLine },
    },
    yAxis: {
      type: 'value',
      axisLabel: { ...chartAxisLabel, formatter: v => `${v}%` },
      splitLine: chartSplitLine,
    },
    series: [
      {
        name: 'p95',
        type: 'line',
        data: p95,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: 'rgba(99, 102, 241, 0.5)' },
        areaStyle: { color: 'rgba(99, 102, 241, 0.08)' },
      },
      {
        name: 'p75',
        type: 'line',
        data: p75,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 0.8, color: 'rgba(99, 102, 241, 0.3)' },
        areaStyle: { color: 'rgba(99, 102, 241, 0.1)' },
      },
      {
        name: 'Median (p50)',
        type: 'line',
        data: p50,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: ACCENT.blue },
      },
      {
        name: 'p25',
        type: 'line',
        data: p25,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 0.8, color: 'rgba(99, 102, 241, 0.3)' },
      },
      {
        name: 'p5',
        type: 'line',
        data: p5,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: 'rgba(99, 102, 241, 0.5)' },
      },
    ],
  }
})

const distChartOption = computed(() => {
  const stoch = props.stochasticData
  if (!stoch || (!stoch.terminal_distribution && !stoch.liability_histogram)) return null

  let bins = [], counts = []
  const var95 = stoch.var_95 || stoch.terminal_distribution?.var_95 || 0

  if (stoch.terminal_distribution) {
    const td = stoch.terminal_distribution
    const binEdges = td.bin_edges
    counts = td.counts.map((c, i) => {
      const mid = (binEdges[i] + binEdges[i + 1]) / 2.0
      return { value: c, itemStyle: { color: mid >= var95 ? ACCENT.rose : ACCENT.indigo, borderRadius: [2, 2, 0, 0] } }
    })
    bins = td.counts.map((_, i) => `$${((binEdges[i] + binEdges[i + 1]) / 2000.0).toFixed(1)}k`)
  } else {
    const hist = stoch.liability_histogram
    bins = hist.map(d => `$${(d.bin_mid / 1000).toFixed(1)}k`)
    counts = hist.map(d => ({
      value: d.count,
      itemStyle: { color: d.bin_mid >= var95 ? ACCENT.rose : ACCENT.indigo, borderRadius: [2, 2, 0, 0] },
    }))
  }

  return {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    grid: { top: 25, left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: bins, axisLine: chartAxisLine, axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(bins.length / 8)) } },
    yAxis: { type: 'value', axisLabel: chartAxisLabel, splitLine: chartSplitLine },
    series: [{ name: 'Scenarios', type: 'bar', data: counts, barWidth: '85%' }],
  }
})
</script>

<template>
  <div class="space-y-5">
    <!-- Error Alert Banner -->
    <div
      v-if="error"
      class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between shadow-lg"
    >
      <div class="flex items-center space-x-2.5">
        <span class="h-2 w-2 rounded-full bg-rose-400"></span>
        <div>
          <strong class="font-semibold text-rose-200">Stochastic Simulation Error:</strong>
          <span class="ml-1 text-rose-300/90">{{ error }}</span>
        </div>
      </div>
      <button
        @click="emit('run-valuation')"
        type="button"
        class="btn-secondary text-[11px] px-3 py-1 rounded-md border-rose-500/30 text-rose-200 hover:bg-rose-500/20 transition"
      >
        Retry
      </button>
    </div>

    <!-- Tail Risk Metrics Header Row -->
    <div v-if="stochasticData" class="grid grid-cols-2 lg:grid-cols-6 gap-4">
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Mean BEL</div>
        <div class="text-xl font-semibold text-white mt-1 font-mono">{{ formatCurrency(stochasticData.mean_bel) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">Expected Path Value</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Volatility (σ)</div>
        <div class="text-xl font-semibold text-sky-400 mt-1 font-mono">{{ formatCurrency(stochasticData.std_bel) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">Standard Deviation</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">VaR 95%</div>
        <div class="text-xl font-semibold text-rose-400 mt-1 font-mono">{{ formatCurrency(stochasticData.var_95) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">95th Percentile</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">CVaR / CTE 95</div>
        <div class="text-xl font-semibold text-amber-400 mt-1 font-mono">{{ formatCurrency(stochasticData.cvar_95) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">Tail Conditional Expectation</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">VaR 99%</div>
        <div class="text-xl font-semibold text-rose-500 mt-1 font-mono">{{ formatCurrency(stochasticData.var_99) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">Extreme Solvency Level</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Skewness</div>
        <div class="text-xl font-semibold text-indigo-400 mt-1 font-mono">
          {{ stochasticData.terminal_distribution?.skewness?.toFixed(2) ?? '—' }}
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Distribution Asymmetry</div>
      </div>
    </div>

    <!-- Empty State Prompt -->
    <div v-if="!stochasticData && !loading && !error" class="card p-12 text-center space-y-3">
      <div class="h-12 w-12 mx-auto rounded-full bg-sky-500/10 flex items-center justify-center text-sky-400">
        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
        </svg>
      </div>
      <h3 class="text-base font-semibold text-white">Stochastic ESG &amp; Risk Simulation</h3>
      <p class="text-xs text-slate-400 max-w-md mx-auto">
        Run Monte Carlo simulations with mean-reverting Vasicek interest rate diffusion and dynamic S-curve surrender behavior.
      </p>
      <button @click="emit('run-valuation')" type="button" class="btn-primary text-xs px-4 py-2 rounded-md">
        Run Monte Carlo Simulation
      </button>
    </div>

    <!-- Fan Chart & Distribution Grid -->
    <div v-show="stochasticData || loading" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- Fan Chart -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-semibold text-white">Short-Rate Quantile Fan Chart</h3>
            <p class="text-[11px] text-slate-500">{{ form.n_scenarios.toLocaleString() }} simulated paths — p5 through p95</p>
          </div>

        </div>
        <div class="w-full h-80">
          <BaseChart :option="fanChartOption" :loading="loading" />
        </div>
      </div>

      <!-- Empirical Density Distribution -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-semibold text-white">Terminal Liability Distribution</h3>
            <p class="text-[11px] text-slate-500">Empirical BEL density with VaR 95% tail highlighted in red</p>
          </div>

        </div>
        <div class="w-full h-80">
          <BaseChart :option="distChartOption" :loading="loading" />
        </div>
      </div>
    </div>
  </div>
</template>
