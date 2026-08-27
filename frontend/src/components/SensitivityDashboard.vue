<script setup>
import { ref } from 'vue'
import StressTestDashboard from './StressTestDashboard.vue'

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
  sensitivityData: {
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
const stressTestRef = ref(null)

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

defineExpose({
  resizeCharts: () => {
    stressTestRef.value?.resizeCharts?.()
  },
})
</script>

<template>
  <div class="space-y-6">
    <!-- Error Alert Banner -->
    <div
      v-if="error"
      class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between shadow-lg"
    >
      <div class="flex items-center space-x-2.5">
        <span class="h-2 w-2 rounded-full bg-rose-400"></span>
        <div>
          <strong class="font-semibold text-rose-200">Sensitivity Analysis Error:</strong>
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

    <!-- Interactive Real-Time Stress Testing Sliders & Trajectory -->
    <StressTestDashboard
      :contract-form="form"
      :is-active="isActive"
      ref="stressTestRef"
    />

    <!-- Compound Macro-Scenarios -->
    <div
      v-if="sensitivityData && sensitivityData.combined_scenarios && sensitivityData.combined_scenarios.length"
      class="card p-5 space-y-3"
    >
      <div class="flex items-center justify-between pb-2 border-b border-white/[0.06]">
        <div>
          <h3 class="text-sm font-semibold text-white">Standard Compound Regulatory &amp; Macro Stress Scenarios</h3>
          <p class="text-[11px] text-slate-500">Joint shocks evaluating severe economic &amp; demographic downturns</p>
        </div>
        <span class="badge badge-warning">ERM Matrix</span>
      </div>
      <div class="overflow-x-auto card-inset rounded-lg max-h-[380px]">
        <table class="data-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Rate Shift</th>
              <th>Mortality</th>
              <th>Lapse</th>
              <th>Expense</th>
              <th>Shocked Reserve</th>
              <th>Delta ($)</th>
              <th>Solvency Impact</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sc in sensitivityData.combined_scenarios" :key="sc.scenario_id">
              <td>
                <div class="font-semibold text-white text-[11px]">{{ sc.name }}</div>
                <div class="text-[10px] text-slate-500">{{ sc.description }}</div>
              </td>
              <td class="font-mono text-sky-400">
                {{ sc.rate_shift_bps > 0 ? '+' : '' }}{{ sc.rate_shift_bps }} bps
              </td>
              <td class="font-mono text-slate-300">{{ (sc.mortality_multiplier * 100).toFixed(0) }}%</td>
              <td class="font-mono text-slate-300">{{ (sc.lapse_multiplier * 100).toFixed(0) }}%</td>
              <td class="font-mono text-slate-300">{{ (sc.expense_multiplier * 100).toFixed(0) }}%</td>
              <td class="text-sky-400 font-semibold font-mono">{{ formatCurrency(sc.shocked_reserve) }}</td>
              <td :class="['font-mono font-semibold', sc.delta_reserve > 0 ? 'text-rose-400' : 'text-emerald-400']">
                {{ sc.delta_reserve > 0 ? '+' : '' }}{{ formatCurrency(sc.delta_reserve) }} ({{ formatPercent(sc.delta_pct) }})
              </td>
              <td>
                <span
                  :class="[
                    'badge',
                    sc.solvency_impact === 'HIGH RISK'
                      ? 'badge-danger'
                      : sc.solvency_impact === 'MODERATE RISK'
                      ? 'badge-warning'
                      : 'badge-success'
                  ]"
                >
                  {{ sc.solvency_impact }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
