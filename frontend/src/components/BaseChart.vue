<script setup>
import { ref, markRaw, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: {
    type: Object,
    default: null,
  },
  theme: {
    type: [String, Object],
    default: null,
  },
  notMerge: {
    type: Boolean,
    default: true,
  },
  lazyUpdate: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  autoResize: {
    type: Boolean,
    default: true,
  },
  height: {
    type: String,
    default: '100%',
  },
  width: {
    type: String,
    default: '100%',
  },
})

const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null

function init() {
  if (!chartRef.value) return
  if (chartRef.value.clientWidth === 0 || chartRef.value.clientHeight === 0) return

  if (!chartInstance) {
    chartInstance = markRaw(echarts.init(chartRef.value, props.theme))
  }

  if (props.option && chartInstance) {
    chartInstance.setOption(props.option, props.notMerge, props.lazyUpdate)
  }
}

function resize() {
  if (chartInstance && chartRef.value && chartRef.value.clientWidth > 0) {
    chartInstance.resize()
  } else if (!chartInstance && chartRef.value && chartRef.value.clientWidth > 0) {
    init()
  }
}

watch(
  () => props.option,
  (newOpt) => {
    if (newOpt) {
      if (!chartInstance) {
        nextTick(init)
      } else {
        chartInstance.setOption(newOpt, props.notMerge, props.lazyUpdate)
      }
    }
  },
  { deep: true }
)

watch(
  () => props.loading,
  (isLoading) => {
    if (!chartInstance) return
    if (isLoading) {
      chartInstance.showLoading({
        text: '',
        color: '#38BDF8',
        textColor: '#CBD5E1',
        maskColor: 'rgba(15, 23, 42, 0.4)',
      })
    } else {
      chartInstance.hideLoading()
    }
  }
)

onMounted(() => {
  if (props.autoResize && typeof window !== 'undefined' && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      resize()
    })
    if (chartRef.value) {
      resizeObserver.observe(chartRef.value)
    }
  }
  nextTick(init)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

defineExpose({
  getInstance: () => chartInstance,
  resize,
})
</script>

<template>
  <div ref="chartRef" class="w-full h-full" :style="{ width, height }"></div>
</template>
