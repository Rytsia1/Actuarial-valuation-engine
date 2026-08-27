<script setup>
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

const props = defineProps({
  ifrs17Data: {
    type: Object,
    default: null,
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
  white: '#F8FAFC',
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

const lrcChartOption = computed(() => {
  const schedule = props.ifrs17Data?.balance_sheet_schedule
  if (!schedule || !schedule.length) return null

  const durations = schedule.map(d => `t=${d.duration}`)
  const bels = schedule.map(d => d.bel)
  const ras = schedule.map(d => d.risk_adjustment)
  const csms = schedule.map(d => d.csm)
  const lrcs = schedule.map(d => d.total_lrc)

  return {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: {
      data: ['BEL', 'Risk Adjustment', 'CSM', 'Total LRC'],
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
      { name: 'BEL', type: 'line', stack: 'lrc', areaStyle: { color: 'rgba(56, 189, 248, 0.4)' }, lineStyle: { width: 1.5, color: ACCENT.blue }, data: bels, smooth: true, symbol: 'none' },
      { name: 'Risk Adjustment', type: 'line', stack: 'lrc', areaStyle: { color: 'rgba(251, 191, 36, 0.4)' }, lineStyle: { width: 1.5, color: ACCENT.amber }, data: ras, smooth: true, symbol: 'none' },
      { name: 'CSM', type: 'line', stack: 'lrc', areaStyle: { color: 'rgba(99, 102, 241, 0.4)' }, lineStyle: { width: 1.5, color: ACCENT.indigo }, data: csms, smooth: true, symbol: 'none' },
      { name: 'Total LRC', type: 'line', lineStyle: { width: 2.5, color: ACCENT.white }, data: lrcs, smooth: true, symbol: 'circle', symbolSize: 3, itemStyle: { color: ACCENT.white } },
    ],
  }
})

const pnlChartOption = computed(() => {
  const pnl = props.ifrs17Data?.income_statement_schedule
  if (!pnl || !pnl.length) return null

  const years = pnl.map(d => `Yr ${d.year + 1}`)
  const revenues = pnl.map(d => d.insurance_revenue)
  const expenses = pnl.map(d => d.insurance_service_expenses)
  const csms = pnl.map(d => d.csm_amortization)
  const results = pnl.map(d => d.insurance_service_result)

  return {
    backgroundColor: 'transparent',
    tooltip: { ...chartTooltip, trigger: 'axis' },
    legend: {
      data: ['Insurance Revenue', 'Service Expenses', 'CSM Release', 'Net Result'],
      textStyle: { color: ACCENT.slate, fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: chartGrid,
    xAxis: {
      type: 'category',
      data: years,
      axisLine: chartAxisLine,
      axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 8)) },
    },
    yAxis: {
      type: 'value',
      axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` },
      splitLine: chartSplitLine,
    },
    series: [
      { name: 'Insurance Revenue', type: 'bar', data: revenues, itemStyle: { color: ACCENT.emerald, borderRadius: [2, 2, 0, 0] } },
      { name: 'Service Expenses', type: 'bar', data: expenses, itemStyle: { color: ACCENT.rose, borderRadius: [2, 2, 0, 0] } },
      { name: 'CSM Release', type: 'line', data: csms, lineStyle: { width: 2, color: ACCENT.indigo }, itemStyle: { color: ACCENT.indigo }, smooth: true },
      { name: 'Net Result', type: 'line', data: results, lineStyle: { width: 2, color: ACCENT.blue }, itemStyle: { color: ACCENT.blue }, smooth: true },
    ],
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
          <strong class="font-semibold text-rose-200">IFRS 17 Valuation Error:</strong>
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

    <!-- Empty State -->
    <div v-if="!ifrs17Data && !loading && !error" class="card p-12 text-center space-y-3">
      <div class="h-12 w-12 mx-auto rounded-full bg-sky-500/10 flex items-center justify-center text-sky-400">
        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
      </div>
      <h3 class="text-base font-semibold text-white">IFRS 17 General Measurement Model (GMM)</h3>
      <p class="text-xs text-slate-400 max-w-md mx-auto">
        Compute initial contract recognition, Liability for Remaining Coverage (LRC), Contractual Service Margin (CSM), and systematic P&amp;L release schedule.
      </p>
      <button @click="emit('run-valuation')" type="button" class="btn-primary text-xs px-4 py-2 rounded-md">
        Run IFRS 17 Valuation
      </button>
    </div>

    <!-- Initial Recognition Balance Sheet KPI Cards -->
    <div v-if="ifrs17Data" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Initial LRC (L_0)</div>
        <div class="text-xl font-semibold text-white mt-1 font-mono">{{ formatCurrency(ifrs17Data.initial_balance.total_lrc_0) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">Total Liability</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Fulfillment Cash Flows</div>
        <div class="text-xl font-semibold text-sky-400 mt-1 font-mono">{{ formatCurrency(ifrs17Data.initial_balance.fcf_0) }}</div>
        <div class="text-[10px] text-slate-500 mt-1">BEL + RA</div>
      </div>
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Risk Adjustment</div>
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
        <div class="w-full h-72">
          <BaseChart :option="lrcChartOption" :loading="loading" />
        </div>
      </div>
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-white mb-1">Insurance Service P&amp;L</h3>
        <p class="text-[11px] text-slate-500 mb-3">Revenue, claims, expenses, CSM release</p>
        <div class="w-full h-72">
          <BaseChart :option="pnlChartOption" :loading="loading" />
        </div>
      </div>
    </div>

    <!-- Schedules -->
    <div v-if="ifrs17Data" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div class="card p-5">
        <h3 class="text-sm font-semibold text-white mb-1">Balance Sheet Schedule</h3>
        <p class="text-[11px] text-slate-500 mb-3">LRC roll-forward</p>
        <div class="overflow-x-auto card-inset rounded-lg max-h-[380px]">
          <table class="data-table">
            <thead class="sticky top-0 bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 z-10"><tr><th>Duration</th><th>BEL</th><th>RA</th><th>CSM</th><th>Total LRC</th></tr></thead>
            <tbody class="text-slate-300">
              <tr v-for="row in ifrs17Data.balance_sheet_schedule" :key="row.duration">
                <td class="text-sky-400 font-semibold font-mono">t={{ row.duration }}</td>
                <td class="font-mono">{{ formatCurrency(row.bel) }}</td>
                <td class="text-amber-400 font-mono">{{ formatCurrency(row.risk_adjustment) }}</td>
                <td class="text-indigo-400 font-semibold font-mono">{{ formatCurrency(row.csm) }}</td>
                <td class="text-white font-semibold font-mono">{{ formatCurrency(row.total_lrc) }}</td>
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
            <thead class="sticky top-0 bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 z-10"><tr><th>Year</th><th>Revenue</th><th>Expenses</th><th>CSM Release</th><th>Result</th></tr></thead>
            <tbody class="text-slate-300">
              <tr v-for="row in ifrs17Data.income_statement_schedule" :key="row.year">
                <td class="text-emerald-400 font-semibold font-mono">Yr {{ row.year + 1 }}</td>
                <td class="text-emerald-400 font-mono">{{ formatCurrency(row.insurance_revenue) }}</td>
                <td class="text-rose-400 font-mono">{{ formatCurrency(row.insurance_service_expenses) }}</td>
                <td class="text-indigo-400 font-semibold font-mono">{{ formatCurrency(row.csm_amortization) }}</td>
                <td :class="['font-mono font-semibold', row.insurance_service_result >= 0 ? 'text-emerald-400' : 'text-rose-400']">
                  {{ formatCurrency(row.insurance_service_result) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
