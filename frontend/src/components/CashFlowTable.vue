<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  cashFlows: {
    type: Array,
    default: () => [],
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
  <div class="glass-panel rounded-xl p-5 space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-white">
          Multi-Decrement Cash Flow Rollout
        </h3>
        <p class="text-xs text-slate-400 font-mono">
          Year-by-year in-force cohort decrement, premiums, claims, expenses, and discounted liabilities
        </p>
      </div>
      <span class="text-xs font-mono text-slate-400">
        {{ cashFlows.length }} projection years
      </span>
    </div>

    <!-- Table Container with Horizontal & Vertical Scroll -->
    <div class="overflow-x-auto border border-slate-800 rounded-lg max-h-[520px]">
      <table class="min-w-full text-left text-xs divide-y divide-slate-800 font-mono">
        <thead class="sticky top-0 bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 z-10 text-slate-300">
          <tr>
            <th class="px-3 py-2.5 font-semibold">Year (t)</th>
            <th class="px-3 py-2.5 font-semibold">Age</th>
            <th class="px-3 py-2.5 font-semibold">In-force (BOY)</th>
            <th class="px-3 py-2.5 font-semibold">Premium Income</th>
            <th class="px-3 py-2.5 font-semibold">Death Claims</th>
            <th class="px-3 py-2.5 font-semibold">Lapse Payouts</th>
            <th class="px-3 py-2.5 font-semibold">Expenses</th>
            <th class="px-3 py-2.5 font-semibold">Net Liability CF</th>
            <th class="px-3 py-2.5 font-semibold">PV Net Liability</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/60 bg-slate-950/40 text-slate-300">
          <tr
            v-for="row in cashFlows"
            :key="row.year"
            class="hover:bg-slate-800/40 transition-colors"
          >
            <td class="px-3 py-2 font-medium text-sky-400">t={{ row.year }}</td>
            <td class="px-3 py-2">{{ row.age }}</td>
            <td class="px-3 py-2 text-slate-400">{{ (row.inforce_boy * 100).toFixed(2) }}%</td>
            <td class="px-3 py-2 text-emerald-400">{{ formatCurrency(row.premium_income) }}</td>
            <td class="px-3 py-2 text-rose-300">{{ formatCurrency(row.death_claims) }}</td>
            <td class="px-3 py-2 text-slate-400">{{ formatCurrency(row.lapse_payouts) }}</td>
            <td class="px-3 py-2 text-amber-300">{{ formatCurrency(row.total_expense) }}</td>
            <td
              :class="[
                'px-3 py-2 font-bold',
                row.net_liability_cf > 0 ? 'text-rose-400' : 'text-emerald-400'
              ]"
            >
              {{ formatCurrency(row.net_liability_cf) }}
            </td>
            <td
              :class="[
                'px-3 py-2 font-bold',
                row.pv_net_liability > 0 ? 'text-rose-400' : 'text-emerald-400'
              ]"
            >
              {{ formatCurrency(row.pv_net_liability) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
