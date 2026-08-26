<script setup>
import { ref, onMounted, onUnmounted, watch, defineProps } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  reserveProfile: {
    type: Array,
    default: () => [],
  },
  productType: {
    type: String,
    default: 'term',
  },
  sumAssured: {
    type: Number,
    default: 1000000,
  },
})

const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChartOptions()
}

function updateChartOptions() {
  if (!chartInstance || !props.reserveProfile.length) return

  const durations = props.reserveProfile.map(row => `t=${row.duration} (Age ${row.age})`)
  const prospective = props.reserveProfile.map(row => row.reserve_prospective)
  const retrospective = props.reserveProfile.map(row => row.reserve_retrospective)
  const gross = props.reserveProfile.map(row => row.gross_reserve)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: '#334155',
      borderWidth: 1,
      textStyle: { color: '#e2e8f0', fontSize: 12, fontFamily: 'monospace' },
      formatter: function (params) {
        let header = `<div class="font-bold border-b border-slate-700 pb-1 mb-1 text-sky-400">${params[0].axisValue}</div>`
        let body = params
          .map(
            item => `
            <div class="flex items-center justify-between space-x-4 py-0.5">
              <span class="flex items-center space-x-1.5">
                <span class="inline-block w-2.5 h-2.5 rounded-full" style="background:${item.color}"></span>
                <span class="text-slate-300 text-xs">${item.seriesName}:</span>
              </span>
              <span class="font-bold text-white text-xs font-mono">$${Number(item.value).toLocaleString()}</span>
            </div>
          `
          )
          .join('')
        return header + body
      },
    },
    legend: {
      data: ['Prospective Reserve (_t V)', 'Retrospective Reserve (_t V_retro)', 'Gross Reserve (GPV)'],
      textStyle: { color: '#94a3b8', fontSize: 11, fontFamily: 'sans-serif' },
      top: 0,
      right: 10,
    },
    grid: {
      top: 40,
      left: 65,
      right: 25,
      bottom: 35,
    },
    xAxis: {
      type: 'category',
      data: durations,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace',
        interval: Math.max(1, Math.floor(durations.length / 8)),
      },
      splitLine: { show: true, lineStyle: { color: 'rgba(51, 65, 85, 0.3)' } },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace',
        formatter: val => `$${(val / 1000).toFixed(0)}k`,
      },
      splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.4)' } },
    },
    series: [
      {
        name: 'Prospective Reserve (_t V)',
        type: 'line',
        data: prospective,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2.5, color: '#38bdf8' },
        itemStyle: { color: '#38bdf8' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(56, 189, 248, 0.25)' },
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
        name: 'Gross Reserve (GPV)',
        type: 'line',
        data: gross,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#fbbf24' },
        itemStyle: { color: '#fbbf24' },
      },
    ],
  }

  chartInstance.setOption(option, true)
}

watch(
  () => props.reserveProfile,
  () => {
    updateChartOptions()
  },
  { deep: true }
)

onMounted(() => {
  initChart()
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize()
    })
    resizeObserver.observe(chartRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
  chartInstance?.dispose()
})
</script>

<template>
  <div class="glass-panel rounded-xl p-5 space-y-3">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-white flex items-center space-x-2">
          <span>Policy Reserve Trajectory (${}_t V$)</span>
        </h3>
        <p class="text-xs text-slate-400 font-mono">
          Prospective (${}_t V_{\text{pro}}$) vs. Retrospective (${}_t V_{\text{retro}}$) vs. Gross GPV
        </p>
      </div>
      <div class="flex items-center space-x-2">
        <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          ${}_0 V = 0$
        </span>
        <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
          ${}_t V_{\text{pro}} \equiv {}_t V_{\text{retro}}$
        </span>
      </div>
    </div>

    <!-- Chart Canvas -->
    <div ref="chartRef" class="w-full h-80"></div>
  </div>
</template>
