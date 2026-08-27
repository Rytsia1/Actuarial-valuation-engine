<script setup>
import { ref, shallowRef, reactive, watch, onMounted, onUnmounted, nextTick, markRaw } from 'vue'
import * as echarts from 'echarts'
import {
  Scale,
  TrendingUp,
  Activity,
  TrendingDown,
  AlertTriangle,
  RotateCcw,
  Sliders,
} from 'lucide-vue-next'
import { runStressTest } from '../services/actuaryApi'

const props = defineProps({
  contractForm: {
    type: Object,
    default: () => ({
      product_type: 'endowment',
      issue_age: 30,
      term: 20,
      sum_assured: 1000000,
      interest_rate: 0.05,
      table_id: 'soa_ilt',
      gross_premium: null,
    }),
  },
  isActive: {
    type: Boolean,
    default: false,
  },
})

// ────────────────────────────────────────────────────────────
// Reactive State
// ────────────────────────────────────────────────────────────

const shocks = reactive({
  interest_rate_bps: 0.0,     // -200 to +200 bps
  mortality_multiplier: 1.0,  // 0.5 to 2.0 (50% to 200%)
  lapse_multiplier: 1.0,      // 0.5 to 2.0 (50% to 200%)
  expense_inflation_pct: 0.0, // 0.0% to 15.0%
})

const loading = ref(false)
const error = ref(null)
const stressData = shallowRef(null)
let needsUpdate = false

import BaseChart from './BaseChart.vue'

const tornadoChartRef = ref(null)
const trajectoryChartRef = ref(null)
let debounceTimer = null

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

function formatPercent(val, decimals = 1) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  const sign = val > 0 ? '+' : ''
  return `${sign}${Number(val).toFixed(decimals)}%`
}

// ────────────────────────────────────────────────────────────
// Preset Shocks
// ────────────────────────────────────────────────────────────

const presets = [
  {
    id: 'baseline',
    label: 'Baseline (0 Shocks)',
    icon: markRaw(Scale),
    shocks: { interest_rate_bps: 0.0, mortality_multiplier: 1.0, lapse_multiplier: 1.0, expense_inflation_pct: 0.0 },
  },
  {
    id: 'rising_rates',
    label: 'Rising Rates (+150 bps)',
    icon: markRaw(TrendingUp),
    shocks: { interest_rate_bps: 150.0, mortality_multiplier: 1.0, lapse_multiplier: 1.40, expense_inflation_pct: 4.0 },
  },
  {
    id: 'pandemic',
    label: 'Pandemic Crisis',
    icon: markRaw(Activity),
    shocks: { interest_rate_bps: -100.0, mortality_multiplier: 1.60, lapse_multiplier: 1.20, expense_inflation_pct: 6.0 },
  },
  {
    id: 'stagflation',
    label: 'Stagflation Shock',
    icon: markRaw(TrendingDown),
    shocks: { interest_rate_bps: -150.0, mortality_multiplier: 1.0, lapse_multiplier: 0.70, expense_inflation_pct: 10.0 },
  },
  {
    id: 'extreme_downside',
    label: 'Extreme Tail Shock',
    icon: markRaw(AlertTriangle),
    shocks: { interest_rate_bps: -200.0, mortality_multiplier: 2.0, lapse_multiplier: 2.0, expense_inflation_pct: 15.0 },
  },
]

function applyPreset(preset) {
  shocks.interest_rate_bps = preset.shocks.interest_rate_bps
  shocks.mortality_multiplier = preset.shocks.mortality_multiplier
  shocks.lapse_multiplier = preset.shocks.lapse_multiplier
  shocks.expense_inflation_pct = preset.shocks.expense_inflation_pct
  triggerValuation(true)
}

function resetToBaseline() {
  shocks.interest_rate_bps = 0.0
  shocks.mortality_multiplier = 1.0
  shocks.lapse_multiplier = 1.0
  shocks.expense_inflation_pct = 0.0
  triggerValuation(true)
}

// ────────────────────────────────────────────────────────────
// API Fetch & Debounce Orchestration (~120ms-150ms)
// ────────────────────────────────────────────────────────────

async function fetchStressTest() {
  loading.value = true
  error.value = null

  try {
    const form = props.contractForm || {}
    const isWholeLife = form?.product_type === 'whole_life'
    const payload = {
      product_type: form?.product_type || 'endowment',
      issue_age: Number(form?.issue_age ?? 30),
      term: isWholeLife ? null : Number(form?.term ?? 20),
      sum_assured: Number(form?.sum_assured ?? 1000000),
      premium_paying_term: form?.premium_paying_term ? Number(form.premium_paying_term) : null,
      interest_rate: Number(form?.interest_rate ?? 0.05),
      gross_premium: form?.gross_premium ? Number(form.gross_premium) : null,
      table_id: form?.table_id || 'soa_ilt',
      expense: form?.expense || null,
      lapse: form?.lapse || null,
      shocks: {
        interest_rate_bps: Number(shocks.interest_rate_bps || 0),
        mortality_multiplier: Number(shocks.mortality_multiplier || 1.0),
        lapse_multiplier: Number(shocks.lapse_multiplier || 1.0),
        expense_inflation_pct: Number(shocks.expense_inflation_pct || 0),
      },
    }

    const res = await runStressTest(payload)
    stressData.value = res
  } catch (err) {
    console.error('Stress test valuation failed:', err)
    error.value = err?.message || 'Failed to calculate stress test.'
  } finally {
    loading.value = false
  }
}

function triggerValuation(immediate = false) {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }

  if (immediate) {
    fetchStressTest()
  } else {
    debounceTimer = setTimeout(() => {
      fetchStressTest()
    }, 130)
  }
}

// Watch sliders and contractForm
watch(
  () => [
    shocks.interest_rate_bps,
    shocks.mortality_multiplier,
    shocks.lapse_multiplier,
    shocks.expense_inflation_pct,
    props.contractForm?.product_type,
    props.contractForm?.issue_age,
    props.contractForm?.term,
    props.contractForm?.sum_assured,
    props.contractForm?.interest_rate,
    props.contractForm?.table_id,
  ],
  () => {
    if (props.isActive) {
      triggerValuation(false)
    } else {
      needsUpdate = true
    }
  },
  { deep: true }
)

// Watch isActive prop for on-demand fetch
watch(
  () => props.isActive,
  async (active) => {
    if (active) {
      if (!stressData.value || needsUpdate) {
        needsUpdate = false
        await fetchStressTest()
      }
    }
  },
  { immediate: true }
)

// ────────────────────────────────────────────────────────────
// ECharts Computed Options
// ────────────────────────────────────────────────────────────

const chartTooltip = {
  backgroundColor: 'rgba(15, 23, 42, 0.96)',
  borderColor: 'rgba(255, 255, 255, 0.08)',
  borderWidth: 1,
  textStyle: { color: '#E2E8F0', fontSize: 12, fontFamily: 'Inter, system-ui' },
}

const chartAxisLabel = { color: '#64748B', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }
const chartSplitLine = { lineStyle: { color: 'rgba(255, 255, 255, 0.04)' } }
const chartAxisLine = { lineStyle: { color: '#1E293B' } }

const tornadoChartOption = computed(() => {
  if (!Array.isArray(stressData.value?.tornado_data) || stressData.value.tornado_data.length === 0) return null

  const items = [...stressData.value.tornado_data].reverse()
  const factors = items.map(d => d?.risk_factor ?? 'Factor')
  const lowDeltas = items.map(d => Number(d?.low_delta ?? 0))
  const highDeltas = items.map(d => Number(d?.high_delta ?? 0))
  const currentDeltas = items.map(d => Number(d?.current_delta ?? 0))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      ...chartTooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const idx = params[0].dataIndex
        const item = items[idx]
        if (!item) return ''
        return `
          <div style="font-weight:600;color:#F8FAFC;margin-bottom:4px">${item.risk_factor || ''}</div>
          <div style="font-size:11px;color:#CBD5E1;line-height:1.6">
            <div><span style="color:#38BDF8">Downside (${item.low_label || 'Low'}):</span> ${formatCurrency(item.low_delta)} (${formatPercent(item.low_delta_pct)})</div>
            <div><span style="color:#F43F5E">Upside (${item.high_label || 'High'}):</span> ${formatCurrency(item.high_delta)} (${formatPercent(item.high_delta_pct)})</div>
            <div style="border-top:1px solid rgba(255,255,255,0.08);margin-top:4px;padding-top:4px"><span style="color:#FBBF24">Current Slider (${item.current_label || 'Current'}):</span> <strong>${formatCurrency(item.current_delta)}</strong> (${formatPercent(item.current_delta_pct)})</div>
            <div style="color:#818CF8;font-weight:600">Total Factor Swing: ${formatCurrency(item.swing)} (${Number(item.swing_pct ?? 0).toFixed(1)}%)</div>
          </div>`
      },
    },
    legend: {
      data: ['Downside Shock', 'Upside Shock', 'Current Slider Shock'],
      textStyle: { color: '#94A3B8', fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: { top: 35, left: 160, right: 30, bottom: 20 },
    xAxis: {
      type: 'value',
      axisLine: chartAxisLine,
      axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1000).toFixed(0)}k` },
      splitLine: chartSplitLine,
    },
    yAxis: {
      type: 'category',
      data: factors,
      axisLine: chartAxisLine,
      axisLabel: { color: '#CBD5E1', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" },
      splitLine: { show: false },
    },
    animationDurationUpdate: 300,
    series: [
      {
        name: 'Downside Shock',
        type: 'bar',
        data: lowDeltas,
        itemStyle: { borderRadius: [3, 3, 3, 3], color: '#38BDF8' },
      },
      {
        name: 'Upside Shock',
        type: 'bar',
        data: highDeltas,
        itemStyle: { borderRadius: [3, 3, 3, 3], color: '#F43F5E' },
      },
      {
        name: 'Current Slider Shock',
        type: 'bar',
        data: currentDeltas,
        itemStyle: {
          borderRadius: [3, 3, 3, 3],
          color: '#FBBF24',
          borderColor: '#FFFFFF',
          borderWidth: 1,
        },
      },
    ],
  }
})

const trajectoryChartOption = computed(() => {
  if (!Array.isArray(stressData.value?.reserve_trajectory) || stressData.value.reserve_trajectory.length === 0) return null

  const traj = stressData.value.reserve_trajectory
  const durations = traj.map(d => `t=${d?.duration ?? 0}`)
  const baseReserves = traj.map(d => Number(d?.baseline_reserve ?? 0))
  const stressedReserves = traj.map(d => Number(d?.stressed_reserve ?? 0))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      ...chartTooltip,
      trigger: 'axis',
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const idx = params[0].dataIndex
        const item = traj[idx]
        if (!item) return ''
        const delta = (item.stressed_reserve ?? 0) - (item.baseline_reserve ?? 0)
        const deltaPct = item.baseline_reserve && item.baseline_reserve !== 0 ? (delta / Math.abs(item.baseline_reserve)) * 100 : 0
        return `
          <div style="font-weight:600;color:#F8FAFC;margin-bottom:4px">Duration t=${item.duration ?? 0} (Age ${item.age ?? 0})</div>
          <div style="font-size:11px;color:#CBD5E1;line-height:1.6">
            <div><span style="color:#38BDF8">Baseline Reserve:</span> ${formatCurrency(item.baseline_reserve)}</div>
            <div><span style="color:#F43F5E">Stressed Reserve:</span> <strong>${formatCurrency(item.stressed_reserve)}</strong></div>
            <div style="border-top:1px solid rgba(255,255,255,0.08);margin-top:4px;padding-top:4px;color:${delta >= 0 ? '#F43F5E' : '#34D399'}">
              Liability Shift: <strong>${delta >= 0 ? '+' : ''}${formatCurrency(delta)}</strong> (${formatPercent(deltaPct)})
            </div>
          </div>`
      },
    },
    legend: {
      data: ['Baseline Reserve Profile', 'Stressed Reserve Profile'],
      textStyle: { color: '#94A3B8', fontSize: 11 },
      top: 0,
      right: 10,
    },
    grid: { top: 35, left: 65, right: 20, bottom: 25 },
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
    animationDurationUpdate: 300,
    series: [
      {
        name: 'Baseline Reserve Profile',
        type: 'line',
        data: baseReserves,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#38BDF8', type: 'dashed' },
        itemStyle: { color: '#38BDF8' },
      },
      {
        name: 'Stressed Reserve Profile',
        type: 'line',
        data: stressedReserves,
        smooth: true,
        symbol: 'circle',
        symbolSize: 3,
        lineStyle: { width: 2.5, color: '#F43F5E' },
        itemStyle: { color: '#F43F5E' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(244, 63, 94, 0.25)' },
            { offset: 1, color: 'rgba(244, 63, 94, 0.0)' },
          ]),
        },
      },
    ],
  }
})

onMounted(() => {
  if (props.isActive && !stressData.value) {
    fetchStressTest()
  }
})

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})

function resizeCharts() {
  tornadoChartRef.value?.resize?.()
  trajectoryChartRef.value?.resize?.()
}

defineExpose({
  resizeCharts,
  fetchStressTest,
})
</script>

<template>
  <div class="space-y-6">

    <!-- Error Alert Banner -->
    <div v-if="error" class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between shadow-lg">
      <div class="flex items-center space-x-2.5">
        <AlertTriangle class="w-4 h-4 text-rose-400 flex-shrink-0" />
        <div>
          <strong class="font-semibold text-rose-200">Stress Test Calculation Error:</strong>
          <span class="ml-1 text-rose-300/90">{{ error }}</span>
        </div>
      </div>
      <button @click="fetchStressTest" class="btn-secondary text-[11px] px-3 py-1 rounded-md border-rose-500/30 text-rose-200 hover:bg-rose-500/20 transition">
        Retry
      </button>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- 1. TOP CONTROL DECK: INTERACTIVE SHOCK SLIDERS         -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div class="card p-5 space-y-5 border border-white/[0.08]">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-white/[0.06]">
        <div>
          <div class="flex items-center space-x-2">
            <span class="h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse"></span>
            <h2 class="text-base font-semibold text-white tracking-tight">
              Real-Time Actuarial Stress Testing Sliders
            </h2>
            <span v-if="loading" class="text-[11px] text-sky-400 font-mono flex items-center space-x-1">
              <svg class="animate-spin h-3 w-3 text-sky-400 inline" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              <span>Recalculating...</span>
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-0.5">
            Adjust risk-factor shocks and watch liability reserves morph instantly with smooth animation.
          </p>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center space-x-2">
          <button
            @click="resetToBaseline"
            class="btn-secondary text-[11px] px-3 py-1.5 flex items-center space-x-1.5 hover:border-slate-500"
            title="Restore all sliders to default baseline"
          >
            <svg class="h-3.5 w-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Reset to Baseline</span>
          </button>
        </div>
      </div>

      <!-- Quick Preset Shocks Bar -->
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="text-[11px] text-slate-500 mr-1 font-mono">Presets:</span>
        <button
          v-for="p in presets"
          :key="p.id"
          @click="applyPreset(p)"
          class="btn-secondary text-[11px] px-2.5 py-1 rounded-md transition flex items-center space-x-1.5 hover:bg-slate-700/50"
        >
          <component :is="p.icon" class="w-3.5 h-3.5 text-slate-400" />
          <span>{{ p.label }}</span>
        </button>
      </div>

      <!-- 4 Interactive Sliders Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-1">
        
        <!-- Slider 1: Interest Rate Shift -->
        <div class="card-inset p-3.5 rounded-xl space-y-2 border border-white/[0.04]">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400 font-medium">Interest Rate Shift</span>
            <span
              :class="[
                'badge font-mono text-[11px]',
                shocks.interest_rate_bps > 0 ? 'badge-success' : shocks.interest_rate_bps < 0 ? 'badge-danger' : 'badge-info'
              ]"
            >
              {{ shocks.interest_rate_bps > 0 ? '+' : '' }}{{ shocks.interest_rate_bps }} bps
            </span>
          </div>
          <input
            type="range"
            v-model.number="shocks.interest_rate_bps"
            min="-200"
            max="200"
            step="10"
            class="w-full accent-sky-400 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div class="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>-200 bps</span>
            <span>0 bps (Base)</span>
            <span>+200 bps</span>
          </div>
        </div>

        <!-- Slider 2: Mortality Shock Multiplier -->
        <div class="card-inset p-3.5 rounded-xl space-y-2 border border-white/[0.04]">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400 font-medium">Mortality Multiplier</span>
            <span
              :class="[
                'badge font-mono text-[11px]',
                shocks.mortality_multiplier > 1.0 ? 'badge-danger' : shocks.mortality_multiplier < 1.0 ? 'badge-success' : 'badge-info'
              ]"
            >
              {{ (shocks.mortality_multiplier * 100).toFixed(0) }}% ({{ formatPercent((shocks.mortality_multiplier - 1.0) * 100, 0) }})
            </span>
          </div>
          <input
            type="range"
            v-model.number="shocks.mortality_multiplier"
            min="0.5"
            max="2.0"
            step="0.05"
            class="w-full accent-rose-400 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div class="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>50% (-50%)</span>
            <span>100% (Base)</span>
            <span>200% (+100%)</span>
          </div>
        </div>

        <!-- Slider 3: Lapse Rate Shock Multiplier -->
        <div class="card-inset p-3.5 rounded-xl space-y-2 border border-white/[0.04]">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400 font-medium">Lapse Rate Shock</span>
            <span
              :class="[
                'badge font-mono text-[11px]',
                shocks.lapse_multiplier !== 1.0 ? 'badge-warning' : 'badge-info'
              ]"
            >
              {{ (shocks.lapse_multiplier * 100).toFixed(0) }}% ({{ formatPercent((shocks.lapse_multiplier - 1.0) * 100, 0) }})
            </span>
          </div>
          <input
            type="range"
            v-model.number="shocks.lapse_multiplier"
            min="0.5"
            max="2.0"
            step="0.05"
            class="w-full accent-amber-400 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div class="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>50% (-50%)</span>
            <span>100% (Base)</span>
            <span>200% (+100%)</span>
          </div>
        </div>

        <!-- Slider 4: Expense Inflation % -->
        <div class="card-inset p-3.5 rounded-xl space-y-2 border border-white/[0.04]">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-400 font-medium">Expense Inflation</span>
            <span
              :class="[
                'badge font-mono text-[11px]',
                shocks.expense_inflation_pct > 0 ? 'badge-warning' : 'badge-info'
              ]"
            >
              +{{ shocks.expense_inflation_pct.toFixed(1) }}%
            </span>
          </div>
          <input
            type="range"
            v-model.number="shocks.expense_inflation_pct"
            min="0"
            max="15"
            step="0.5"
            class="w-full accent-indigo-400 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <div class="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>0% (Base)</span>
            <span>+7.5%</span>
            <span>+15.0%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading Skeleton when initial fetch is running -->
    <div v-if="loading && !stressData" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div v-for="i in 5" :key="i" class="card p-4 space-y-2">
        <div class="skeleton h-3 w-20"></div>
        <div class="skeleton h-6 w-28"></div>
        <div class="skeleton h-2.5 w-16"></div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- 2. REAL-TIME KPI STRIP: BASELINE VS. STRESSED          -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-if="stressData" class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Baseline Reserve</div>
        <div class="text-xl font-semibold text-sky-400 mt-1 font-mono">
          {{ formatCurrency(stressData.baseline_reserve) }}
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Unshocked Net BEL</div>
      </div>

      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Stressed Reserve</div>
        <div class="text-xl font-semibold text-rose-400 mt-1 font-mono">
          {{ formatCurrency(stressData.stressed_reserve) }}
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Under Current Slider Shocks</div>
      </div>

      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Net Liability Delta</div>
        <div :class="['text-xl font-semibold mt-1 font-mono', stressData.delta_reserve >= 0 ? 'text-rose-400' : 'text-emerald-400']">
          {{ stressData.delta_reserve >= 0 ? '+' : '' }}{{ formatCurrency(stressData.delta_reserve) }}
        </div>
        <div class="text-[10px] text-slate-500 mt-1">
          Shift: <strong>{{ formatPercent(stressData.delta_pct) }}</strong>
        </div>
      </div>

      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Effective Duration</div>
        <div class="text-xl font-semibold text-indigo-400 mt-1 font-mono">
          {{ stressData.effective_duration }} yrs
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Interest Rate Sensitivity</div>
      </div>

      <div class="card p-4">
        <div class="text-[11px] text-slate-500 uppercase tracking-wider font-medium">Dollar Duration (DV01)</div>
        <div class="text-xl font-semibold text-amber-400 mt-1 font-mono">
          {{ formatCurrency(stressData.dv01) }}
        </div>
        <div class="text-[10px] text-slate-500 mt-1">Per 1 bp parallel shift</div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- 3. DUAL CHARTS: TORNADO SENSITIVITY + TRAJECTORY       -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-if="stressData && stressData.tornado_data && stressData.reserve_trajectory" class="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- Chart 1: Dynamic Tornado Sensitivity -->
      <div class="card p-5 space-y-3">
        <div class="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div>
            <h3 class="text-sm font-semibold text-white">Dynamic Tornado Sensitivity</h3>
            <p class="text-[11px] text-slate-500">
              Downside (Blue) vs. Upside (Rose) vs. Current Slider Position (Gold)
            </p>
          </div>
          <span class="badge badge-info">OAT + Sliders</span>
        </div>
        <div class="w-full h-80">
          <BaseChart ref="tornadoChartRef" :option="tornadoChartOption" :loading="loading" />
        </div>
      </div>

      <!-- Chart 2: Reserve Trajectory (Baseline vs Stressed) -->
      <div class="card p-5 space-y-3">
        <div class="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div>
            <h3 class="text-sm font-semibold text-white">Gross Reserve Trajectory (tV)</h3>
            <p class="text-[11px] text-slate-500">
              Comparing Baseline (Sky) vs. Stressed Reserve Trajectory (Rose) over time
            </p>
          </div>
          <span class="badge badge-success">Smooth Morphing</span>
        </div>
        <div class="w-full h-80">
          <BaseChart ref="trajectoryChartRef" :option="trajectoryChartOption" :loading="loading" />
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!-- 4. DETAILED TRAJECTORY TABLE                           -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-if="stressData && stressData.reserve_trajectory" class="card p-5 space-y-3">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h3 class="text-sm font-semibold text-white">Duration-by-Duration Liability Comparison</h3>
          <p class="text-[11px] text-slate-500">
            Policy year t=0..T cash flows and discounted gross liability reserves
          </p>
        </div>
        <span class="text-xs text-slate-500 font-mono">
          {{ stressData.reserve_trajectory?.length || 0 }} durations
        </span>
      </div>

      <div class="overflow-x-auto card-inset rounded-lg max-h-[380px]">
        <table class="data-table">
          <thead>
            <tr>
              <th>Duration</th>
              <th>Age</th>
              <th>Baseline Reserve</th>
              <th>Stressed Reserve</th>
              <th>Reserve Delta ($)</th>
              <th>Baseline Net CF</th>
              <th>Stressed Net CF</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in stressData.reserve_trajectory" :key="row.duration">
              <td class="text-sky-400 font-semibold">t={{ row.duration }}</td>
              <td>{{ row.age }}</td>
              <td class="text-slate-300">{{ formatCurrency(row.baseline_reserve) }}</td>
              <td class="text-rose-400 font-semibold">{{ formatCurrency(row.stressed_reserve) }}</td>
              <td :class="row.delta_reserve >= 0 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'">
                {{ row.delta_reserve >= 0 ? '+' : '' }}{{ formatCurrency(row.delta_reserve) }}
              </td>
              <td class="text-slate-400">{{ formatCurrency(row.baseline_net_cf) }}</td>
              <td class="text-slate-300">{{ formatCurrency(row.stressed_net_cf) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>
