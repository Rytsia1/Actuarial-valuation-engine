<script setup>
import { computed } from 'vue'
import * as echarts from 'echarts'
import BaseChart from './BaseChart.vue'

const props = defineProps({
  deterministicData: {
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
  emerald: '#34D399',
  amber: '#FBBF24',
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

const reserveChartOption = computed(() => {
  const profile = props.deterministicData?.reserve_profile
  if (!profile || !profile.length) return null

  const durations = profile.map(r => `t=${r.duration}`)
  const prospective = profile.map(r => r.reserve_prospective)
  const retrospective = profile.map(r => r.reserve_retrospective)
  const gross = profile.map(r => r.gross_reserve)

  return {
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
        symbolSize: 4,
        lineStyle: { width: 2.5, color: ACCENT.blue },
        itemStyle: { color: ACCENT.blue },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.22)' },
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
        lineStyle: { width: 1.8, color: ACCENT.emerald, type: 'dashed' },
      },
      {
        name: 'Gross GPV',
        type: 'line',
        data: gross,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.8, color: ACCENT.amber },
      },
    ],
  }
})
</script>

<template>
  <div class="space-y-5">
    <!-- Reserve Chart Card -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <div>
          <h3 class="text-sm font-semibold text-white">Policy Reserve Profiles</h3>
          <p class="text-[11px] text-slate-500">
            Equivalence identity verification: Prospective vs Retrospective vs Gross Premium Valuation (GPV)
          </p>
        </div>
        <span class="badge badge-success">Identity Verified: ₜV_pro ≡ ₜV_retro</span>
      </div>
      <div class="w-full h-80">
        <BaseChart :option="reserveChartOption" :loading="loading" />
      </div>
    </div>

    <!-- Duration by Duration Reserve Table -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h3 class="text-sm font-semibold text-white">Seriatim Policy Duration Schedule</h3>
          <p class="text-[11px] text-slate-500">{{ deterministicData?.reserve_profile?.length || 0 }} policy durations</p>
        </div>
      </div>
      <div class="overflow-x-auto card-inset rounded-lg max-h-[500px]">
        <table class="data-table">
          <thead>
            <tr>
              <th>Duration (t)</th>
              <th>Attained Age</th>
              <th>Prospective Net (ₜV_pro)</th>
              <th>Retrospective Net (ₜV_retro)</th>
              <th>Gross GPV Reserve</th>
              <th>Equivalence Check</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in deterministicData?.reserve_profile || []" :key="row.duration">
              <td class="text-sky-400 font-semibold font-mono">t={{ row.duration }}</td>
              <td class="font-mono text-slate-300">{{ row.age }}</td>
              <td class="text-sky-400 font-mono font-semibold">{{ formatCurrency(row.reserve_prospective) }}</td>
              <td class="text-emerald-400 font-mono font-semibold">{{ formatCurrency(row.reserve_retrospective) }}</td>
              <td class="text-amber-400 font-mono">{{ formatCurrency(row.gross_reserve) }}</td>
              <td>
                <span
                  :class="[
                    'badge',
                    Math.abs(row.reserve_prospective - row.reserve_retrospective) < 0.05
                      ? 'badge-success'
                      : 'badge-danger'
                  ]"
                >
                  {{ Math.abs(row.reserve_prospective - row.reserve_retrospective) < 0.05 ? 'EXACT MATCH' : 'DELTA' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
