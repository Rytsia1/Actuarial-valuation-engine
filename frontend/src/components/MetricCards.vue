<script setup>
import { defineProps } from 'vue'
import { HelpCircle } from 'lucide-vue-next'

const props = defineProps({
  deterministic: {
    type: Object,
    default: null,
  },
  stochastic: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

function formatCurrency(val) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val)
}
</script>

<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- Card 1: Annual Net Premium -->
    <div class="glass-panel rounded-xl p-4 relative overflow-hidden group">
      <div class="absolute top-0 right-0 h-16 w-16 bg-sky-500/10 rounded-bl-full pointer-events-none transition-all duration-300 group-hover:scale-110"></div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5 group/tooltip cursor-help" title="The level annual premium required to fund the benefits based on the equivalence principle.">
          Annual Net Premium (P)
          <HelpCircle class="w-3 h-3 text-slate-500 group-hover/tooltip:text-sky-400 transition-colors" />
        </span>
        <span class="px-1.5 py-0.5 text-[9px] font-mono rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
          Equivalence
        </span>
      </div>
      <div class="text-2xl font-bold font-mono text-white tracking-tight mt-1">
        <span v-if="loading" class="animate-pulse text-slate-500">...</span>
        <span v-else>{{ formatCurrency(deterministic?.annual_net_premium) }}</span>
      </div>
      <div class="flex items-center space-x-2 text-xs text-slate-400 mt-2 font-mono">
        <span>NSP: {{ formatCurrency(deterministic?.nsp) }}</span>
        <span>•</span>
        <span>ä: {{ deterministic?.annuity_factor?.toFixed(3) || '—' }}</span>
      </div>
    </div>

    <!-- Card 2: Best Estimate Liability (BEL) -->
    <div class="glass-panel rounded-xl p-4 relative overflow-hidden group">
      <div class="absolute top-0 right-0 h-16 w-16 bg-indigo-500/10 rounded-bl-full pointer-events-none transition-all duration-300 group-hover:scale-110"></div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5 group/tooltip cursor-help" title="Best Estimate Liability. A negative value indicates a profitable contract (inflows > outflows) under this engine's convention.">
          Mean BEL / GPV
          <HelpCircle class="w-3 h-3 text-slate-500 group-hover/tooltip:text-indigo-400 transition-colors" />
        </span>
        <span
          :class="[
            'px-1.5 py-0.5 text-[9px] font-mono rounded border',
            (stochastic?.mean_bel || 0) < 0
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
          ]"
        >
          {{ (stochastic?.mean_bel || 0) < 0 ? 'Surplus/Profit' : 'Liability' }}
        </span>
      </div>
      <div class="text-2xl font-bold font-mono text-white tracking-tight mt-1">
        <span v-if="loading" class="animate-pulse text-slate-500">...</span>
        <span v-else>{{ formatCurrency(stochastic?.mean_bel ?? deterministic?.bel) }}</span>
      </div>
      <div class="flex items-center space-x-2 text-xs text-slate-400 mt-2 font-mono">
        <span class="cursor-help" title="Standard Deviation (σ). Represents the dispersion of possible BEL outcomes.">σ (Std. Dev.): {{ formatCurrency(stochastic?.std_bel) }}</span>
      </div>
    </div>

    <!-- Card 3: 95% Value at Risk (VaR) -->
    <div class="glass-panel rounded-xl p-4 relative overflow-hidden group">
      <div class="absolute top-0 right-0 h-16 w-16 bg-rose-500/10 rounded-bl-full pointer-events-none transition-all duration-300 group-hover:scale-110"></div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5 group/tooltip cursor-help" title="The threshold liability that will not be exceeded with 95% confidence.">
          Value at Risk (VaR 95%)
          <HelpCircle class="w-3 h-3 text-slate-500 group-hover/tooltip:text-rose-400 transition-colors" />
        </span>
        <span class="px-1.5 py-0.5 text-[9px] font-mono rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
          Tail Risk
        </span>
      </div>
      <div class="text-2xl font-bold font-mono text-rose-300 tracking-tight mt-1">
        <span v-if="loading" class="animate-pulse text-slate-500">...</span>
        <span v-else>{{ formatCurrency(stochastic?.var_95) }}</span>
      </div>
      <div class="flex items-center space-x-2 text-xs text-slate-400 mt-2 font-mono">
        <span>VaR 99%: {{ formatCurrency(stochastic?.var_99) }}</span>
      </div>
    </div>

    <!-- Card 4: 95% Conditional Value at Risk (CVaR / CTE) -->
    <div class="glass-panel rounded-xl p-4 relative overflow-hidden group">
      <div class="absolute top-0 right-0 h-16 w-16 bg-purple-500/10 rounded-bl-full pointer-events-none transition-all duration-300 group-hover:scale-110"></div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5 group/tooltip cursor-help" title="Conditional Value at Risk (Expected Shortfall). The average liability in the worst 5% of scenarios.">
          Expected Shortfall (CVaR 95%)
          <HelpCircle class="w-3 h-3 text-slate-500 group-hover/tooltip:text-purple-400 transition-colors" />
        </span>
        <span class="px-1.5 py-0.5 text-[9px] font-mono rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
          CTE 95
        </span>
      </div>
      <div class="text-2xl font-bold font-mono text-purple-300 tracking-tight mt-1">
        <span v-if="loading" class="animate-pulse text-slate-500">...</span>
        <span v-else>{{ formatCurrency(stochastic?.cvar_95) }}</span>
      </div>
      <div class="flex items-center space-x-2 text-xs text-slate-400 mt-2 font-mono">
        <span>CVaR 99%: {{ formatCurrency(stochastic?.cvar_99) }}</span>
      </div>
    </div>
  </div>
</template>
