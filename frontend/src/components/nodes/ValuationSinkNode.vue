<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: {
    type: Object,
    default: () => ({
      label: 'Valuation Consolidator',
      isSimulating: false,
    }),
  },
})

const emit = defineEmits(['simulate'])
</script>

<template>
  <div class="custom-flow-node border-2 border-indigo-500/60 bg-[#0F172A] rounded-xl shadow-2xl p-4 w-72 text-slate-200 relative">
    <!-- Input Handles -->
    <Handle
      type="target"
      :position="Position.Left"
      id="sink_inflow"
      :style="{ top: '35%' }"
      class="!w-3.5 !h-3.5 !bg-emerald-400 !border-2 !border-[#0F172A]"
      title="Inflows (Premiums)"
    />
    <Handle
      type="target"
      :position="Position.Left"
      id="sink_outflow"
      :style="{ top: '65%' }"
      class="!w-3.5 !h-3.5 !bg-rose-400 !border-2 !border-[#0F172A]"
      title="Outflows (Claims & Exp)"
    />

    <!-- Header -->
    <div class="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.08]">
      <div class="flex items-center space-x-2">
        <span class="h-2.5 w-2.5 rounded-full bg-indigo-400 animate-pulse"></span>
        <span class="text-xs font-semibold text-white">Valuation Consolidator</span>
      </div>
      <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">TERMINAL</span>
    </div>

    <!-- Description & Formula -->
    <div class="space-y-2 text-[11px]">
      <div class="card-inset p-2 rounded-lg text-[10px] space-y-1">
        <div class="text-slate-400">Net Liability Cash Flow:</div>
        <div class="font-mono text-indigo-300 font-semibold">NCFₜ = Outgoₜ - Inflowₜ</div>
        <div class="text-[9px] text-slate-500">BEL = ∑ vᵗ · NCFₜ (Gross Premium Valuation)</div>
      </div>

      <!-- Quick Metrics Preview if simulated -->
      <div v-if="data.summary" class="grid grid-cols-2 gap-2 pt-1">
        <div class="card-inset p-1.5 rounded">
          <div class="text-[9px] text-slate-400">Total BEL</div>
          <div class="text-xs font-mono font-semibold text-sky-400">${{ (data.summary.total_bel / 1000).toFixed(1) }}k</div>
        </div>
        <div class="card-inset p-1.5 rounded">
          <div class="text-[9px] text-slate-400">Ann. Premium</div>
          <div class="text-xs font-mono font-semibold text-emerald-400">${{ data.summary.annual_premium?.toFixed(0) }}</div>
        </div>
      </div>

      <!-- Action Button -->
      <button
        @click="$emit('simulate')"
        :disabled="data.isSimulating"
        class="w-full mt-2 btn-primary py-2 text-xs flex items-center justify-center space-x-1.5 shadow-lg shadow-sky-500/20"
      >
        <svg v-if="data.isSimulating" class="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        <svg v-else class="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
        </svg>
        <span>{{ data.isSimulating ? 'Simulating...' : 'Simulate Product' }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.custom-flow-node {
  box-shadow: 0 8px 30px -4px rgba(0, 0, 0, 0.7);
  font-family: inherit;
}
</style>
