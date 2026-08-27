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
  isActive: {
    type: Boolean,
    default: true,
  },
})

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
  }
})

const pnlChartOption = computed(() => {
  const pnl = props.ifrs17Data?.income_statement_schedule
  if (!pnl || !pnl.length) return null

  const years = pnl.map(d => `Yr ${d.year + 1}`)

  return {
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
  }
})
</script>

<template>
  <div class="space-y-5">
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
            <thead><tr><th>Duration</th><th>BEL</th><th>RA</th><th>CSM</th><th>Total LRC</th></tr></thead>
            <tbody>
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
            <thead><tr><th>Year</th><th>Revenue</th><th>Expenses</th><th>CSM Release</th><th>Result</th></tr></thead>
            <tbody>
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
