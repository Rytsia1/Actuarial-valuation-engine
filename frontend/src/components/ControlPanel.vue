<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:form', 'submit'])

const productTypes = [
  { value: 'term', label: 'Term Life Insurance' },
  { value: 'endowment', label: 'Endowment Insurance' },
  { value: 'whole_life', label: 'Whole Life Insurance' },
  { value: 'pure_endowment', label: 'Pure Endowment' },
]

function updateField(key, val) {
  emit('update:form', { ...props.form, [key]: val })
}

function updateNested(parent, key, val) {
  emit('update:form', {
    ...props.form,
    [parent]: { ...props.form[parent], [key]: val },
  })
}
</script>

<template>
  <div class="glass-panel rounded-xl p-5 space-y-6">
    <div class="flex items-center justify-between border-b border-slate-800 pb-3">
      <h2 class="text-sm font-semibold text-white uppercase tracking-wider flex items-center space-x-2">
        <svg class="h-4 w-4 text-sky-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
        <span>Contract & Assumptions</span>
      </h2>
      <span class="text-[11px] font-mono text-slate-400">SOA ILT / 5% Base</span>
    </div>

    <!-- Contract Specification -->
    <div class="space-y-4">
      <h3 class="text-xs font-mono font-medium text-sky-400 uppercase tracking-wider">
        1. Policy Contract
      </h3>

      <!-- Product Type -->
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1">Product Type</label>
        <select
          :value="form.product_type"
          @change="updateField('product_type', $event.target.value)"
          class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white focus:ring-1 focus:ring-sky-500 focus:border-sky-500 transition"
        >
          <option v-for="pt in productTypes" :key="pt.value" :value="pt.value">
            {{ pt.label }}
          </option>
        </select>
      </div>

      <!-- Issue Age & Term Grid -->
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">
            Issue Age (<span class="font-mono text-sky-400">x</span>)
          </label>
          <input
            type="number"
            :value="form.issue_age"
            @input="updateField('issue_age', Number($event.target.value))"
            min="0"
            max="100"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
        <div v-if="form.product_type !== 'whole_life'">
          <label class="block text-xs font-medium text-slate-300 mb-1">
            Term (<span class="font-mono text-sky-400">n</span> yrs)
          </label>
          <input
            type="number"
            :value="form.term"
            @input="updateField('term', Number($event.target.value))"
            min="1"
            max="80"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
      </div>

      <!-- Sum Assured -->
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1">
          Sum Assured (<span class="font-mono text-sky-400">S</span>)
        </label>
        <div class="relative">
          <span class="absolute inset-y-0 left-0 pl-3 flex items-center text-xs text-slate-400 font-mono">$</span>
          <input
            type="number"
            :value="form.sum_assured"
            @input="updateField('sum_assured', Number($event.target.value))"
            step="50000"
            min="10000"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg pl-7 pr-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
      </div>
    </div>

    <!-- Interest & Expense Assumptions -->
    <div class="space-y-4 border-t border-slate-800/80 pt-4">
      <h3 class="text-xs font-mono font-medium text-sky-400 uppercase tracking-wider">
        2. Economics & Expenses
      </h3>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Base Interest (i)</label>
          <input
            type="number"
            :value="form.interest_rate"
            @input="updateField('interest_rate', Number($event.target.value))"
            step="0.005"
            min="0.01"
            max="0.20"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Acquisition (α %)</label>
          <input
            type="number"
            :value="form.expense.percent_of_premium_first"
            @input="updateNested('expense', 'percent_of_premium_first', Number($event.target.value))"
            step="0.05"
            min="0"
            max="1.0"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
      </div>
    </div>

    <!-- Stochastic Vasicek ESG Parameters -->
    <div class="space-y-4 border-t border-slate-800/80 pt-4">
      <div class="flex items-center justify-between">
        <h3 class="text-xs font-mono font-medium text-sky-400 uppercase tracking-wider">
          3. Vasicek ESG & Monte Carlo
        </h3>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">
            Mean Rev Speed (<span class="font-mono text-sky-400">κ</span>)
          </label>
          <input
            type="number"
            :value="form.vasicek.kappa"
            @input="updateNested('vasicek', 'kappa', Number($event.target.value))"
            step="0.05"
            min="0.01"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">
            Long-term Mean (<span class="font-mono text-sky-400">θ</span>)
          </label>
          <input
            type="number"
            :value="form.vasicek.theta"
            @input="updateNested('vasicek', 'theta', Number($event.target.value))"
            step="0.005"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">
            Rate Volatility (<span class="font-mono text-sky-400">σ</span>)
          </label>
          <input
            type="number"
            :value="form.vasicek.sigma"
            @input="updateNested('vasicek', 'sigma', Number($event.target.value))"
            step="0.005"
            min="0"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Scenarios (N)</label>
          <select
            :value="form.n_scenarios"
            @change="updateField('n_scenarios', Number($event.target.value))"
            class="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-sky-500 transition"
          >
            <option :value="500">500 paths</option>
            <option :value="1000">1,000 paths</option>
            <option :value="2500">2,500 paths</option>
            <option :value="5000">5,000 paths</option>
          </select>
        </div>
      </div>

      <!-- Dynamic Lapse Toggle -->
      <div class="flex items-center justify-between p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
        <div>
          <div class="text-xs font-medium text-slate-200">Dynamic Policyholder Lapse</div>
          <div class="text-[10px] text-slate-400">S-curve interest rate sensitivity</div>
        </div>
        <label class="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            :checked="form.enable_dynamic_lapse"
            @change="updateField('enable_dynamic_lapse', $event.target.checked)"
            class="sr-only peer"
          />
          <div class="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-sky-500"></div>
        </label>
      </div>
    </div>

    <!-- Recalculate CTA -->
    <button
      @click="emit('submit')"
      :disabled="loading"
      class="w-full py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-semibold uppercase tracking-wider rounded-lg shadow-md shadow-sky-500/20 transition-all duration-150 disabled:opacity-50 flex items-center justify-center space-x-2"
    >
      <svg v-if="loading" class="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <span>{{ loading ? 'Running Simulation...' : 'Run Actuarial Valuation' }}</span>
    </button>
  </div>
</template>
