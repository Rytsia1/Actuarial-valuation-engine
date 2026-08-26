<script setup>
import { ref, reactive, onMounted } from 'vue'
import HeaderBar from '../components/HeaderBar.vue'
import ControlPanel from '../components/ControlPanel.vue'
import MetricCards from '../components/MetricCards.vue'
import ReserveChart from '../components/ReserveChart.vue'
import StochasticFanChart from '../components/StochasticFanChart.vue'
import DistributionChart from '../components/DistributionChart.vue'
import CashFlowTable from '../components/CashFlowTable.vue'
import {
  fetchHealth,
  runDeterministicValuation,
  runStochasticValuation,
} from '../api/client'

// Dashboard State
const activeTab = ref('overview')
const backendStatus = ref('checking')
const loading = ref(false)
const errorMessage = ref(null)

// Form Parameters
const form = reactive({
  product_type: 'term',
  issue_age: 30,
  term: 20,
  sum_assured: 1000000,
  premium_paying_term: null,
  interest_rate: 0.05,
  gross_premium: null,
  expense: {
    percent_of_premium_first: 0.35,
    percent_of_premium_renewal: 0.05,
    per_policy_first: 200.0,
    per_policy_renewal: 20.0,
  },
  lapse: {
    duration_rates: [0.08, 0.05, 0.04, 0.03],
    flat_annual_rate: 0.02,
  },
  vasicek: {
    r0: 0.05,
    kappa: 0.20,
    theta: 0.05,
    sigma: 0.015,
  },
  enable_dynamic_lapse: true,
  dynamic_lapse: {
    base_lapse_rate: 0.04,
    credited_rate: 0.04,
    min_lapse_rate: 0.01,
    max_lapse_rate: 0.35,
    sensitivity: 25.0,
    spread_threshold: 0.0,
  },
  n_scenarios: 2500,
  seed: 42,
})

// Valuation Results
const deterministicData = ref(null)
const stochasticData = ref(null)

async function checkBackend() {
  try {
    const health = await fetchHealth()
    backendStatus.value = health.status === 'healthy' ? 'healthy' : 'error'
  } catch (err) {
    console.warn('Backend connection failed:', err)
    backendStatus.value = 'error'
  }
}

async function executeValuation() {
  loading.value = true
  errorMessage.value = null

  try {
    // 1. Prepare deterministic payload
    const detPayload = {
      product_type: form.product_type,
      issue_age: form.issue_age,
      term: form.product_type === 'whole_life' ? null : form.term,
      sum_assured: form.sum_assured,
      premium_paying_term: form.premium_paying_term,
      interest_rate: form.interest_rate,
      gross_premium: form.gross_premium,
      expense: form.expense,
      lapse: form.lapse,
    }

    // 2. Prepare stochastic payload
    const stochPayload = {
      product_type: form.product_type,
      issue_age: form.issue_age,
      term: form.product_type === 'whole_life' ? null : form.term,
      sum_assured: form.sum_assured,
      premium_paying_term: form.premium_paying_term,
      gross_premium: form.gross_premium,
      vasicek: form.vasicek,
      dynamic_lapse: form.enable_dynamic_lapse ? form.dynamic_lapse : null,
      expense: form.expense,
      n_scenarios: form.n_scenarios,
      seed: form.seed,
    }

    // Run parallel valuation
    const [detRes, stochRes] = await Promise.all([
      runDeterministicValuation(detPayload),
      runStochasticValuation(stochPayload),
    ])

    deterministicData.value = detRes
    stochasticData.value = stochRes
    backendStatus.value = 'healthy'
  } catch (err) {
    console.error('Valuation error:', err)
    errorMessage.value = err.message || 'Valuation calculation failed.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await checkBackend()
  await executeValuation()
})
</script>

<template>
  <div class="min-h-screen bg-slate-950 flex flex-col font-sans">
    <!-- Top Navigation Header -->
    <HeaderBar
      :backend-status="backendStatus"
      :active-tab="activeTab"
      :loading="loading"
      @update:active-tab="activeTab = $event"
      @recalculate="executeValuation"
    />

    <!-- Main Content Container -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      <!-- Error Notification Banner -->
      <div
        v-if="errorMessage"
        class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono flex items-center justify-between"
      >
        <div class="flex items-center space-x-2">
          <svg class="h-4 w-4 text-rose-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{{ errorMessage }}</span>
        </div>
        <button @click="executeValuation" class="underline hover:text-white">Retry</button>
      </div>

      <!-- Key Metrics Strip -->
      <MetricCards
        :deterministic="deterministicData"
        :stochastic="stochasticData"
        :loading="loading"
      />

      <!-- Main Layout Grid: Left Controls (1/3), Right Analytics (2/3) -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Sidebar Controls -->
        <div class="lg:col-span-1">
          <ControlPanel
            v-model:form="form"
            :loading="loading"
            @submit="executeValuation"
          />
        </div>

        <!-- Center/Right Analytics View -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Overview Tab: Reserves + Fan Chart -->
          <div v-if="activeTab === 'overview'" class="space-y-6">
            <ReserveChart
              :reserve-profile="deterministicData?.reserve_profile || []"
              :product-type="form.product_type"
              :sum-assured="form.sum_assured"
            />
            <StochasticFanChart
              :fan-chart-rates="stochasticData?.fan_chart_rates || []"
              :sample-paths="stochasticData?.sample_paths || []"
              :n-scenarios="form.n_scenarios"
            />
          </div>

          <!-- Stochastic Deep-Dive Tab: Fan Chart + Liability Distribution -->
          <div v-else-if="activeTab === 'stochastic'" class="space-y-6">
            <StochasticFanChart
              :fan-chart-rates="stochasticData?.fan_chart_rates || []"
              :sample-paths="stochasticData?.sample_paths || []"
              :n-scenarios="form.n_scenarios"
            />
            <DistributionChart
              :histogram-data="stochasticData?.liability_histogram || []"
              :var95="stochasticData?.var_95 || 0"
              :cvar95="stochasticData?.cvar_95 || 0"
              :mean-bel="stochasticData?.mean_bel || 0"
            />
          </div>

          <!-- Cash Flow Rollout Tab -->
          <div v-else-if="activeTab === 'cashflows'" class="space-y-6">
            <CashFlowTable
              :cash-flows="deterministicData?.cash_flows || []"
            />
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-slate-800/80 bg-slate-950 py-4 mt-auto">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between text-xs font-mono text-slate-500">
        <div>Actuarial Valuation & Risk Engine — Quantitative Suite</div>
        <div>FastAPI • Vue 3 • ECharts • NumPy</div>
      </div>
    </footer>
  </div>
</template>
