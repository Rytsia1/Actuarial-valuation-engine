<script setup>
import { defineProps } from 'vue'

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
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider">
          Annual Net Premium (P)
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
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider">
          Mean BEL / GPV
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
        <span>Std Dev: {{ formatCurrency(stochastic?.std_bel) }}</span>
      </div>
    </div>

    <!-- Card 3: 95% Value at Risk (VaR) -->
    <div class="glass-panel rounded-xl p-4 relative overflow-hidden group">
      <div class="absolute top-0 right-0 h-16 w-16 bg-rose-500/10 rounded-bl-full pointer-events-none transition-all duration-300 group-hover:scale-110"></div>
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider">
          Value at Risk (VaR 95%)
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
        <span class="text-[11px] font-mono font-medium text-slate-400 uppercase tracking-wider">
          Expected Shortfall (CVaR 95%)
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
