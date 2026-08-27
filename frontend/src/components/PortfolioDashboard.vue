<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick, markRaw } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  portfolioData: {
    type: Object,
    default: null,
  },
  portfolioLoading: {
    type: Boolean,
    default: false,
  },
  portfolioError: {
    type: String,
    default: null,
  },
  portfolioInterestRate: {
    type: Number,
    default: 0.05,
  },
  form: {
    type: Object,
    required: true,
  },
  isActive: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['upload-file', 'run-demo', 'update:portfolioInterestRate'])

const fileInput = ref(null)
const isDragging = ref(false)

const portfolioCfChartRef = ref(null)
const portfolioProdChartRef = ref(null)
const portfolioAgeChartRef = ref(null)

let portfolioCfChart = null
let portfolioProdChart = null
let portfolioAgeChart = null
let resizeObserver = null

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

function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  emit('upload-file', file)
}

function handleFileDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  emit('upload-file', file)
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

function renderPortfolioCharts() {
  if (!props.portfolioData) return

  if (portfolioCfChartRef.value && props.portfolioData.annual_cash_flows) {
    portfolioCfChart = getOrCreateChart(portfolioCfChartRef.value)
    if (portfolioCfChart) {
      const cfs = props.portfolioData.annual_cash_flows
      const years = cfs.map(d => `Yr ${d.year}`)
      const premiums = cfs.map(d => d.premium_income)
      const claims = cfs.map(d => d.death_claims + d.maturity_benefits)
      const expenses = cfs.map(d => d.total_expenses)
      const netLiability = cfs.map(d => d.net_liability_cf)

      portfolioCfChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'axis' },
        legend: {
          data: ['Premiums', 'Claims', 'Expenses', 'Net Liability'],
          textStyle: { color: ACCENT.slate, fontSize: 11 },
          top: 0,
          right: 10,
        },
        grid: { top: 40, left: 70, right: 20, bottom: 30 },
        xAxis: {
          type: 'category',
          data: years,
          axisLine: chartAxisLine,
          axisLabel: { ...chartAxisLabel, interval: Math.max(1, Math.floor(years.length / 10)) },
        },
        yAxis: {
          type: 'value',
          axisLabel: { ...chartAxisLabel, formatter: v => `$${(v / 1_000_000).toFixed(1)}M` },
          splitLine: chartSplitLine,
        },
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

  if (portfolioProdChartRef.value && props.portfolioData.product_breakdown) {
    portfolioProdChart = getOrCreateChart(portfolioProdChartRef.value)
    if (portfolioProdChart) {
      const prodEntries = Object.entries(props.portfolioData.product_breakdown).map(([k, v]) => ({
        name: k.replace('_', ' ').toUpperCase(),
        value: v.sum_assured,
      }))
      portfolioProdChart.setOption({
        backgroundColor: 'transparent',
        tooltip: { ...chartTooltip, trigger: 'item' },
        legend: { orient: 'vertical', left: 'left', top: 'middle', textStyle: { color: ACCENT.slate, fontSize: 11 } },
        series: [
          {
            name: 'Face Amount',
            type: 'pie',
            radius: ['45%', '75%'],
            center: ['65%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 4, borderColor: '#0F172A', borderWidth: 2 },
            label: { show: false },
            data: prodEntries,
            color: [ACCENT.blue, ACCENT.indigo, ACCENT.emerald, ACCENT.amber],
          },
        ],
      }, true)
      portfolioProdChart.resize()
    }
  }

  if (portfolioAgeChartRef.value && props.portfolioData.age_breakdown) {
    portfolioAgeChart = getOrCreateChart(portfolioAgeChartRef.value)
    if (portfolioAgeChart) {
      const ageEntries = Object.entries(props.portfolioData.age_breakdown)
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

watch(
  () => [props.portfolioData, props.isActive],
  () => {
    if (props.isActive) {
      nextTick(renderPortfolioCharts)
    }
  },
  { deep: true }
)

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    if (props.isActive) {
      portfolioCfChart?.resize()
      portfolioProdChart?.resize()
      portfolioAgeChart?.resize()
    }
  })
  if (props.isActive) {
    nextTick(renderPortfolioCharts)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  portfolioCfChart?.dispose()
  portfolioProdChart?.dispose()
  portfolioAgeChart?.dispose()
})
</script>

<template>
  <div class="space-y-5">
    <!-- Upload Card -->
    <div class="card p-5 space-y-4">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div>
          <h2 class="text-base font-semibold text-white">Seriatim Portfolio Batch Valuation</h2>
          <p class="text-[11px] text-slate-500">Upload seriatim CSV policyholder files or generate synthetic portfolios</p>
        </div>
        <button
          @click="emit('run-demo', 1000)"
          :disabled="portfolioLoading"
          type="button"
          class="btn-primary flex items-center space-x-1.5"
        >
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
        @drop.prevent="handleFileDrop"
        :class="[
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition',
          isDragging ? 'border-sky-400 bg-sky-500/5' : 'border-white/[0.1] hover:border-sky-400/40 bg-[#0F172A]'
        ]"
        @click="fileInput?.click()"
        role="button"
        tabindex="0"
      >
        <input type="file" ref="fileInput" accept=".csv" class="hidden" @change="handleFileUpload" />
        <div class="flex flex-col items-center space-y-2">
          <div class="h-10 w-10 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          </div>
          <p class="text-sm text-slate-300">Drop your CSV here or <span class="text-sky-400">browse files</span></p>
          <p class="text-[10px] text-slate-500 font-mono">
            policy_id, issue_age, term_years, sum_assured, gross_premium, product_type
          </p>
        </div>
      </div>

      <div v-if="portfolioError" class="p-3 card-inset border-rose-500/20 text-rose-400 text-xs">
        {{ portfolioError }}
      </div>
    </div>

    <!-- Portfolio Summary KPIs -->
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
              <tr>
                <th>Policy ID</th>
                <th>Product</th>
                <th>Age</th>
                <th>Term</th>
                <th>Face Amount</th>
                <th>Premium</th>
                <th>PVFB</th>
                <th>PVFP</th>
                <th>Net BEL</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pol in portfolioData.sample_seriatim" :key="pol.policy_id">
                <td class="text-sky-400 font-semibold font-mono">{{ pol.policy_id }}</td>
                <td class="uppercase text-[11px] font-mono">{{ pol.product_type }}</td>
                <td class="font-mono">{{ pol.issue_age }}</td>
                <td class="font-mono">{{ pol.term_years }} yrs</td>
                <td class="font-mono">{{ formatCurrency(pol.sum_assured) }}</td>
                <td class="text-emerald-400 font-mono">{{ formatCurrency(pol.gross_premium) }}</td>
                <td class="text-rose-400 font-mono">{{ formatCurrency(pol.pvfb) }}</td>
                <td class="text-emerald-400 font-mono">{{ formatCurrency(pol.pvfp) }}</td>
                <td :class="['font-mono font-semibold', pol.bel > 0 ? 'text-rose-400' : 'text-emerald-400']">
                  {{ formatCurrency(pol.bel) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
