<script setup>
defineProps({
  form: {
    type: Object,
    required: true,
  },
  availableTables: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  simProgress: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['submit', 'open-table-modal'])
</script>

<template>
  <div class="card p-5 space-y-4">
    <div class="text-xs font-semibold text-slate-300 uppercase tracking-wider pb-2 border-b border-white/[0.06]">
      Contract Parameters
    </div>

    <!-- Table Selection -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label class="text-[11px] text-slate-400 font-medium">Mortality Table</label>
        <button @click="emit('open-table-modal')" type="button" class="text-[11px] text-sky-400 hover:text-sky-300">
          + Upload
        </button>
      </div>
      <select v-model="form.table_id" @change="emit('submit')" class="input-field">
        <option v-for="t in availableTables" :key="t.table_id" :value="t.table_id">
          {{ t.name }} {{ t.is_builtin ? '(Built-in)' : '(Custom)' }}
        </option>
      </select>
    </div>

    <!-- Product -->
    <div>
      <label class="text-[11px] text-slate-400 font-medium mb-1 block">Product Line</label>
      <select v-model="form.product_type" class="input-field">
        <option value="endowment">Endowment Insurance</option>
        <option value="term">Term Life Insurance</option>
        <option value="whole_life">Whole Life Insurance</option>
        <option value="pure_endowment">Pure Endowment</option>
      </select>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <div>
        <label class="text-[11px] text-slate-400 font-medium mb-1 block">Issue Age</label>
        <input type="number" v-model.number="form.issue_age" min="0" max="100" class="input-field" />
      </div>
      <div v-if="form.product_type !== 'whole_life'">
        <label class="text-[11px] text-slate-400 font-medium mb-1 block">Term (yrs)</label>
        <input type="number" v-model.number="form.term" min="1" max="80" class="input-field" />
      </div>
    </div>

    <div>
      <label class="text-[11px] text-slate-400 font-medium mb-1 block">Sum Assured ($)</label>
      <input type="number" v-model.number="form.sum_assured" step="50000" class="input-field" />
    </div>

    <!-- Economics -->
    <div class="pt-3 border-t border-white/[0.06] space-y-3">
      <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Economics</div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-[10px] text-slate-500 mb-1 block">Base Rate (i)</label>
          <input type="number" v-model.number="form.interest_rate" step="0.005" min="0.0" max="0.20" class="input-field" />
        </div>
        <div>
          <label class="text-[10px] text-slate-500 mb-1 block">Acquisition (α)</label>
          <input type="number" v-model.number="form.expense.percent_of_premium_first" step="0.05" min="0" max="1.0" class="input-field" />
        </div>
      </div>
    </div>

    <!-- Vasicek ESG -->
    <div class="pt-3 border-t border-white/[0.06] space-y-3">
      <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Vasicek ESG</div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="text-[10px] text-slate-500 mb-1 block">κ (reversion)</label>
          <input type="number" v-model.number="form.vasicek.kappa" step="0.05" class="input-field" />
        </div>
        <div>
          <label class="text-[10px] text-slate-500 mb-1 block">θ (long-term)</label>
          <input type="number" v-model.number="form.vasicek.theta" step="0.005" class="input-field" />
        </div>
        <div>
          <label class="text-[10px] text-slate-500 mb-1 block">σ (volatility)</label>
          <input type="number" v-model.number="form.vasicek.sigma" step="0.005" class="input-field" />
        </div>
        <div>
          <label class="text-[10px] text-slate-500 mb-1 block">Paths (N)</label>
          <select v-model.number="form.n_scenarios" class="input-field">
            <option :value="1000">1,000</option>
            <option :value="2500">2,500</option>
            <option :value="5000">5,000</option>
            <option :value="10000">10,000</option>
            <option :value="25000">25,000</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Dynamic Lapse Toggle -->
    <div class="pt-3 border-t border-white/[0.06] flex items-center justify-between">
      <div>
        <div class="text-xs text-slate-300 font-medium">Dynamic Lapse</div>
        <div class="text-[10px] text-slate-500">S-Curve Disintermediation</div>
      </div>
      <div
        @click="form.enable_dynamic_lapse = !form.enable_dynamic_lapse"
        :class="['toggle-track', form.enable_dynamic_lapse ? 'active' : '']"
        role="button"
        tabindex="0"
      >
        <div class="toggle-thumb"></div>
      </div>
    </div>

    <!-- Run Button -->
    <button
      @click="emit('submit')"
      :disabled="loading"
      type="button"
      class="btn-primary w-full py-2.5 flex items-center justify-center space-x-2 text-[13px] mt-2"
    >
      <svg v-if="loading" class="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <span>{{ loading ? `Simulating (${simProgress.toFixed(0)}%)` : 'Run Valuation Engine' }}</span>
    </button>
  </div>
</template>
