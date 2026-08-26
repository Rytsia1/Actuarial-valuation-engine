<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: {
    type: Object,
    default: () => ({
      benefit_type: 'Death Benefit',
      formula: '1.0 * SA',
      factor: 1.0,
      maturity_year: null,
    }),
  },
})
</script>

<template>
  <div class="custom-flow-node border border-rose-500/40 bg-[#0F172A] rounded-xl shadow-xl p-3.5 w-60 text-slate-200">
    <!-- Input Handle -->
    <Handle
      type="target"
      :position="Position.Left"
      id="outflow_in"
      class="!w-3 !h-3 !bg-rose-400 !border-2 !border-[#0F172A]"
      title="Contingency Trigger"
    />

    <!-- Header -->
    <div class="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
      <div class="flex items-center space-x-1.5">
        <span class="h-2 w-2 rounded-full bg-rose-400"></span>
        <span class="text-xs font-semibold text-white">Benefit Outflow</span>
      </div>
      <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300">OUTFLOW</span>
    </div>

    <!-- Inputs -->
    <div class="space-y-2 text-[11px]">
      <div>
        <label class="text-slate-400 block text-[10px]">Benefit Type</label>
        <select v-model="data.benefit_type" class="input-field py-1 text-xs text-slate-200">
          <option value="Death Benefit">Death Benefit</option>
          <option value="Maturity Benefit">Maturity Benefit</option>
          <option value="Surrender Value">Surrender Value</option>
          <option value="Expense Loadings">Expense Loadings</option>
        </select>
      </div>

      <div>
        <label class="text-slate-400 block text-[10px]">Formula / Scaling</label>
        <select v-model="data.formula" class="input-field py-1 text-xs text-slate-200 font-mono">
          <option value="1.0 * SA">100% Face Amount (1.0 × SA)</option>
          <option value="0.5 * SA">50% Face Amount (0.5 × SA)</option>
          <option value="2.0 * SA">200% Double Indemnity (2.0 × SA)</option>
          <option value="35% Y1 / 5% Ren">35% Y1 / 5% Ren (Expense)</option>
          <option value="Account Value Payout">Fund Account Value</option>
        </select>
      </div>
    </div>

    <!-- Output Handle -->
    <Handle
      type="source"
      :position="Position.Right"
      id="cash_outflow"
      class="!w-3 !h-3 !bg-rose-400 !border-2 !border-[#0F172A]"
      title="Cash Outflow Stream"
    />
  </div>
</template>

<style scoped>
.custom-flow-node {
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
  font-family: inherit;
}
</style>
