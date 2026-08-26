<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: {
    type: Object,
    default: () => ({
      inflow_type: 'Gross Premium',
      mode: 'formula',
      amount: 0,
      frequency: 'annual',
    }),
  },
})
</script>

<template>
  <div class="custom-flow-node border border-emerald-500/40 bg-[#0F172A] rounded-xl shadow-xl p-3.5 w-60 text-slate-200">
    <!-- Input Handle -->
    <Handle
      type="target"
      :position="Position.Left"
      id="inflow_in"
      class="!w-3 !h-3 !bg-sky-400 !border-2 !border-[#0F172A]"
      title="Policy Meta Inflow"
    />

    <!-- Header -->
    <div class="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
      <div class="flex items-center space-x-1.5">
        <span class="h-2 w-2 rounded-full bg-emerald-400"></span>
        <span class="text-xs font-semibold text-white">Cash Inflow</span>
      </div>
      <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">INFLOW</span>
    </div>

    <!-- Inputs -->
    <div class="space-y-2 text-[11px]">
      <div>
        <label class="text-slate-400 block text-[10px]">Inflow Type</label>
        <select v-model="data.inflow_type" class="input-field py-1 text-xs text-slate-200">
          <option value="Gross Premium">Gross Premium</option>
          <option value="Single Premium">Single Premium</option>
          <option value="Top-Up Inflow">Top-Up Inflow</option>
        </select>
      </div>

      <div>
        <label class="text-slate-400 block text-[10px]">Mode</label>
        <div class="flex items-center space-x-2">
          <label class="flex items-center space-x-1 cursor-pointer">
            <input type="radio" value="formula" v-model="data.mode" class="accent-emerald-400" />
            <span class="text-[10px] text-slate-300">Auto Formula</span>
          </label>
          <label class="flex items-center space-x-1 cursor-pointer">
            <input type="radio" value="fixed" v-model="data.mode" class="accent-emerald-400" />
            <span class="text-[10px] text-slate-300">Fixed ($)</span>
          </label>
        </div>
      </div>

      <div v-if="data.mode === 'fixed'">
        <label class="text-slate-400 block text-[10px]">Annual Amount ($)</label>
        <input
          type="number"
          v-model.number="data.amount"
          min="0"
          step="100"
          class="input-field py-1 text-xs text-slate-200 font-mono"
        />
      </div>
      <div v-else class="text-[10px] text-emerald-400/80 font-mono pt-1">
        ✓ Equivalence principle loaded GP
      </div>
    </div>

    <!-- Output Handle -->
    <Handle
      type="source"
      :position="Position.Right"
      id="cash_inflow"
      class="!w-3 !h-3 !bg-emerald-400 !border-2 !border-[#0F172A]"
      title="Cash Inflow Stream"
    />
  </div>
</template>

<style scoped>
.custom-flow-node {
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
  font-family: inherit;
}
</style>
