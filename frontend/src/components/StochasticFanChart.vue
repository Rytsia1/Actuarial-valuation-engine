<script setup>
import { ref, onMounted, onUnmounted, watch, defineProps } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  fanChartRates: {
    type: Array,
    default: () => [],
  },
  samplePaths: {
    type: Array,
    default: () => [],
  },
  nScenarios: {
    type: Number,
    default: 2000,
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
  if (!chartInstance || !props.fanChartRates.length) return

  const years = props.fanChartRates.map(row => `t=${row.year}`)
  const p5 = props.fanChartRates.map(row => (row.p5 * 100).toFixed(2))
  const p25 = props.fanChartRates.map(row => (row.p25 * 100).toFixed(2))
  const p50 = props.fanChartRates.map(row => (row.p50 * 100).toFixed(2))
  const p75 = props.fanChartRates.map(row => (row.p75 * 100).toFixed(2))
  const p95 = props.fanChartRates.map(row => (row.p95 * 100).toFixed(2))
  const mean = props.fanChartRates.map(row => (row.mean * 100).toFixed(2))

  // Build sample path series
  const sampleSeries = props.samplePaths.slice(0, 8).map((path, idx) => ({
    name: `Path ${idx + 1}`,
    type: 'line',
    data: path.map(r => (r * 100).toFixed(2)),
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 0.8, color: 'rgba(148, 163, 184, 0.25)' },
    silent: true,
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: '#334155',
      borderWidth: 1,
      textStyle: { color: '#e2e8f0', fontSize: 12, fontFamily: 'monospace' },
      formatter: function (params) {
        const yearItem = params[0]
        let header = `<div class="font-bold border-b border-slate-700 pb-1 mb-1 text-sky-400">Short Rate Paths (${yearItem.axisValue})</div>`
        const relevant = params.filter(p => ['p95', 'p75', 'Median (p50)', 'p25', 'p5', 'Mean Rate'].includes(p.seriesName))
        let body = relevant
          .map(
            item => `
            <div class="flex items-center justify-between space-x-4 py-0.5">
              <span class="flex items-center space-x-1.5">
                <span class="inline-block w-2 h-2 rounded-full" style="background:${item.color}"></span>
                <span class="text-slate-300 text-xs">${item.seriesName}:</span>
              </span>
              <span class="font-bold text-white text-xs font-mono">${item.value}%</span>
            </div>
          `
          )
          .join('')
        return header + body
      },
    },
    legend: {
      data: ['95% Upper Bound', 'Median (p50)', 'Mean Rate', '5% Lower Bound'],
      textStyle: { color: '#94a3b8', fontSize: 11, fontFamily: 'sans-serif' },
      top: 0,
      right: 10,
    },
    grid: {
      top: 40,
      left: 55,
      right: 25,
      bottom: 35,
    },
    xAxis: {
      type: 'category',
      data: years,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace',
        interval: Math.max(1, Math.floor(years.length / 8)),
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
        formatter: val => `${val}%`,
      },
      splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.4)' } },
    },
    series: [
      ...sampleSeries,
      {
        name: '95% Upper Bound',
        type: 'line',
        data: p95,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#38bdf8' },
        areaStyle: {
          color: 'rgba(56, 189, 248, 0.12)',
        },
      },
      {
        name: 'p75',
        type: 'line',
        data: p75,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1, color: 'rgba(56, 189, 248, 0.6)' },
        areaStyle: {
          color: 'rgba(56, 189, 248, 0.18)',
        },
      },
      {
        name: 'Median (p50)',
        type: 'line',
        data: p50,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2.5, color: '#0ea5e9' },
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
        lineStyle: { width: 1, color: 'rgba(56, 189, 248, 0.6)' },
      },
      {
        name: '5% Lower Bound',
        type: 'line',
        data: p5,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#38bdf8' },
      },
    ],
  }

  chartInstance.setOption(option, true)
}

watch(
  () => [props.fanChartRates, props.samplePaths],
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
          <span>Vasicek ESG Stochastic Fan Chart</span>
        </h3>
        <p class="text-xs text-slate-400 font-mono">
          5th, 25th, 50th, 75th, 95th Percentiles across {{ nScenarios.toLocaleString() }} Monte Carlo paths
        </p>
      </div>
      <span class="px-2 py-0.5 text-[10px] font-mono rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
        $dr_t = \kappa(\theta - r_t)dt + \sigma dW_t$
      </span>
    </div>

    <!-- Chart Canvas -->
    <div ref="chartRef" class="w-full h-80"></div>
  </div>
</template>
