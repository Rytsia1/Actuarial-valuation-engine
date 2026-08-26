<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: {
    type: Object,
    default: () => ({
      growth_rate: 0.065,
      admin_charge: 100,
      allocation_pct: 0.95,
    }),
  },
})
</script>

<template>
  <div class="custom-flow-node border border-amber-500/40 bg-[#0F172A] rounded-xl shadow-xl p-3.5 w-64 text-slate-200">
    <!-- Input Handle -->
    <Handle
      type="target"
      :position="Position.Left"
      id="acc_inflow"
      class="!w-3 !h-3 !bg-emerald-400 !border-2 !border-[#0F172A]"
      title="Allocated Inflow"
    />

    <!-- Header -->
    <div class="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
      <div class="flex items-center space-x-1.5">
        <span class="h-2 w-2 rounded-full bg-amber-400"></span>
        <span class="text-xs font-semibold text-white">Unit Fund Accumulator</span>
      </div>
      <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">ACCOUNT</span>
    </div>

    <!-- Inputs -->
    <div class="space-y-2 text-[11px]">
      <div>
        <label class="text-slate-400 block text-[10px]">Fund Yield ($i_f$)</label>
        <input
          type="number"
          v-model.number="data.growth_rate"
          step="0.005"
          min="0.0"
          max="0.20"
          class="input-field py-1 text-xs text-slate-200 font-mono"
        />
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="text-slate-400 block text-[10px]">Allocation (%)</label>
          <input
            type="number"
            v-model.number="data.allocation_pct"
            step="0.05"
            min="0.5"
            max="1.0"
            class="input-field py-1 text-xs text-slate-200 font-mono"
          />
        </div>
        <div>
          <label class="text-slate-400 block text-[10px]">Admin Fee ($)</label>
          <input
            type="number"
            v-model.number="data.admin_charge"
            step="10"
            min="0"
            class="input-field py-1 text-xs text-slate-200 font-mono"
          />
        </div>
      </div>
    </div>

    <!-- Output Handle -->
    <Handle
      type="source"
      :position="Position.Right"
      id="cash_outflow"
      class="!w-3 !h-3 !bg-amber-400 !border-2 !border-[#0F172A]"
      title="COI Deduction / Payouts"
    />
  </div>
</template>

<style scoped>
.custom-flow-node {
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
  font-family: inherit;
}
</style>
