<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: {
    type: Object,
    default: () => ({
      decrement_type: 'Mortality',
      table_id: 'soa_ilt',
      multiplier: 1.0,
      lapse_rate: 0.03,
    }),
  },
})
</script>

<template>
  <div class="custom-flow-node border border-indigo-500/40 bg-[#0F172A] rounded-xl shadow-xl p-3.5 w-64 text-slate-200 relative">
    <!-- Input Handle -->
    <Handle
      type="target"
      :position="Position.Left"
      id="contingency_in"
      class="!w-3 !h-3 !bg-sky-400 !border-2 !border-[#0F172A]"
      title="Policy Meta In"
    />

    <!-- Header -->
    <div class="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
      <div class="flex items-center space-x-1.5">
        <span class="h-2 w-2 rounded-full bg-indigo-400"></span>
        <span class="text-xs font-semibold text-white">Contingency Splitter</span>
      </div>
      <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">DECREMENT</span>
    </div>

    <!-- Inputs -->
    <div class="space-y-2 text-[11px]">
      <div>
        <label class="text-slate-400 block text-[10px]">Mortality Table</label>
        <select v-model="data.table_id" class="input-field py-1 text-xs text-slate-200 font-mono">
          <option value="soa_ilt">SOA Illustrative (SOA_ILT)</option>
        </select>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="text-slate-400 block text-[10px]">Mort Multiplier</label>
          <input
            type="number"
            v-model.number="data.multiplier"
            step="0.05"
            min="0.1"
            max="3.0"
            class="input-field py-1 text-xs text-slate-200 font-mono"
          />
        </div>
        <div>
          <label class="text-slate-400 block text-[10px]">Lapse Rate</label>
          <input
            type="number"
            v-model.number="data.lapse_rate"
            step="0.01"
            min="0.0"
            max="0.5"
            class="input-field py-1 text-xs text-slate-200 font-mono"
          />
        </div>
      </div>

      <!-- Port Labels -->
      <div class="pt-2 border-t border-white/[0.04] space-y-1.5 text-[10px]">
        <div class="flex items-center justify-end space-x-1.5 pr-2">
          <span class="text-slate-400">on Death ($q_x$)</span>
          <span class="h-1.5 w-1.5 rounded-full bg-rose-400"></span>
        </div>
        <div class="flex items-center justify-end space-x-1.5 pr-2">
          <span class="text-slate-400">on Lapse ($w_x$)</span>
          <span class="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
        </div>
        <div class="flex items-center justify-end space-x-1.5 pr-2">
          <span class="text-slate-400">on Survival ($p_x$)</span>
          <span class="h-1.5 w-1.5 rounded-full bg-sky-400"></span>
        </div>
      </div>
    </div>

    <!-- Output Handles -->
    <Handle
      type="source"
      :position="Position.Right"
      id="on_death"
      :style="{ top: '65%' }"
      class="!w-3 !h-3 !bg-rose-400 !border-2 !border-[#0F172A]"
      title="Death Event"
    />
    <Handle
      type="source"
      :position="Position.Right"
      id="on_lapse"
      :style="{ top: '78%' }"
      class="!w-3 !h-3 !bg-amber-400 !border-2 !border-[#0F172A]"
      title="Lapse Event"
    />
    <Handle
      type="source"
      :position="Position.Right"
      id="on_survival"
      :style="{ top: '91%' }"
      class="!w-3 !h-3 !bg-sky-400 !border-2 !border-[#0F172A]"
      title="Survival Event"
    />
  </div>
</template>

<style scoped>
.custom-flow-node {
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
  font-family: inherit;
}
</style>
