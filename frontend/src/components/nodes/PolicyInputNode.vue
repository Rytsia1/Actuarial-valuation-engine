<script setup>
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  data: {
    type: Object,
    default: () => ({
      product_name: 'Term Life 20Y',
      age: 35,
      term: 20,
      sum_assured: 1000000,
      premium_freq: 'annual',
      interest_rate: 0.05,
      table_id: 'soa_ilt',
    }),
  },
})
</script>

<template>
  <div class="custom-flow-node border border-sky-500/40 bg-[#0F172A] rounded-xl shadow-xl p-3.5 w-64 text-slate-200">
    <!-- Header -->
    <div class="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
      <div class="flex items-center space-x-1.5">
        <span class="h-2 w-2 rounded-full bg-sky-400"></span>
        <span class="text-xs font-semibold text-white">Policy Parameters</span>
      </div>
      <span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300">SOURCE</span>
    </div>

    <!-- Inputs -->
    <div class="space-y-2 text-[11px]">
      <div>
        <label class="text-slate-400 block text-[10px]">Product Title</label>
        <input
          type="text"
          v-model="data.product_name"
          class="input-field py-1 text-xs text-slate-200"
          placeholder="e.g. 20-Year Term"
        />
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="text-slate-400 block text-[10px]">Issue Age</label>
          <input
            type="number"
            v-model.number="data.age"
            min="0"
            max="99"
            class="input-field py-1 text-xs text-slate-200 font-mono"
          />
        </div>
        <div>
          <label class="text-slate-400 block text-[10px]">Term (Yrs)</label>
          <input
            type="number"
            v-model.number="data.term"
            min="1"
            max="80"
            class="input-field py-1 text-xs text-slate-200 font-mono"
          />
        </div>
      </div>

      <div>
        <label class="text-slate-400 block text-[10px]">Face Amount ($ SA)</label>
        <input
          type="number"
          v-model.number="data.sum_assured"
          step="50000"
          class="input-field py-1 text-xs text-slate-200 font-mono"
        />
      </div>
    </div>

    <!-- Output Handle -->
    <Handle
      type="source"
      :position="Position.Right"
      id="policy_meta"
      class="!w-3 !h-3 !bg-sky-400 !border-2 !border-[#0F172A]"
      title="Policy Metadata"
    />
  </div>
</template>

<style scoped>
.custom-flow-node {
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
  font-family: inherit;
}
</style>
