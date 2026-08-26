<script setup>
import { ref, markRaw, onMounted, onUnmounted, watch, defineProps } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  histogramData: {
    type: Array,
    default: () => [],
  },
  var95: {
    type: Number,
    default: 0,
  },
  cvar95: {
    type: Number,
    default: 0,
  },
  meanBel: {
    type: Number,
    default: 0,
  },
})

const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null

function initChart() {
  if (!chartRef.value) return
  chartInstance = markRaw(echarts.init(chartRef.value))
  updateChartOptions()
}

function updateChartOptions() {
  if (!chartInstance || !props.histogramData.length) return

  const bins = props.histogramData.map(d => `$${(d.bin_mid / 1000).toFixed(1)}k`)
  const counts = props.histogramData.map(d => ({
    value: d.count,
    itemStyle: {
      color: d.bin_mid >= props.var95 ? '#f43f5e' : '#38bdf8',
    },
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
        const item = params[0]
        const dataPoint = props.histogramData[item.dataIndex]
        const isTail = dataPoint.bin_mid >= props.var95
        return `
          <div class="font-bold border-b border-slate-700 pb-1 mb-1 ${isTail ? 'text-rose-400' : 'text-sky-400'}">
            Liability Range: $${dataPoint.bin_start.toLocaleString()} — $${dataPoint.bin_end.toLocaleString()}
          </div>
          <div class="flex justify-between text-xs py-0.5 text-slate-300">
            <span>Scenario Frequency:</span>
            <span class="font-bold text-white font-mono">${item.value} paths</span>
          </div>
          ${isTail ? '<div class="text-[10px] text-rose-400 mt-1 font-mono">⚠️ 95% Tail Risk Region (Exceeds VaR)</div>' : ''}
        `
      },
    },
    grid: {
      top: 30,
      left: 55,
      right: 25,
      bottom: 35,
    },
    xAxis: {
      type: 'category',
      data: bins,
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace',
        interval: Math.max(1, Math.floor(bins.length / 8)),
      },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace',
      },
      splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.4)' } },
    },
    series: [
      {
        name: 'Scenario Count',
        type: 'bar',
        data: counts,
        barWidth: '85%',
        itemStyle: {
          borderRadius: [3, 3, 0, 0],
        },
      },
    ],
  }

  chartInstance.setOption(option, true)
}

watch(
  () => [props.histogramData, props.var95],
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
          <span>Stochastic Liability Distribution & Tail Loss</span>
        </h3>
        <p class="text-xs text-slate-400 font-mono">
          Empirical histogram with shaded 95% Value at Risk tail
        </p>
      </div>
      <div class="flex items-center space-x-2">
        <span class="flex items-center space-x-1 text-[11px] font-mono text-slate-300">
          <span class="inline-block w-2.5 h-2.5 rounded-sm bg-sky-400"></span>
          <span>Typical (95%)</span>
        </span>
        <span class="flex items-center space-x-1 text-[11px] font-mono text-rose-300">
          <span class="inline-block w-2.5 h-2.5 rounded-sm bg-rose-500"></span>
          <span>Tail Risk (5%)</span>
        </span>
      </div>
    </div>

    <!-- Chart Canvas -->
    <div ref="chartRef" class="w-full h-80"></div>
  </div>
</template>
