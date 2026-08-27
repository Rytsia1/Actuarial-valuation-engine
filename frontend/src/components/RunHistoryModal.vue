<script setup>
import { X, Clock, Play } from 'lucide-vue-next'

const props = defineProps({
  modelValue: Boolean,
  history: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

function formatCurrency(val) {
  if (val === undefined || val === null || isNaN(val)) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val)
}

function formatProduct(type) {
  const map = {
    'endowment': 'Endowment',
    'term': 'Term',
    'whole_life': 'Whole Life',
    'pure_endowment': 'Pure Endowment'
  }
  return map[type] || type
}

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <div v-if="modelValue" class="relative z-50" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <div class="fixed inset-0 bg-slate-900/80 backdrop-blur-sm transition-opacity" @click="close"></div>

    <div class="fixed inset-0 z-10 w-screen overflow-y-auto">
      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-xl bg-[#0B0F19] text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-slate-700">
          <!-- Header -->
          <div class="border-b border-white/[0.06] px-5 py-4 flex items-center justify-between">
            <div class="flex items-center space-x-2 text-slate-200">
              <Clock class="h-4 w-4 text-purple-400" />
              <h3 class="text-sm font-semibold tracking-tight" id="modal-title">Valuation Run History</h3>
            </div>
            <button @click="close" class="text-slate-400 hover:text-white transition-colors">
              <X class="h-4 w-4" />
            </button>
          </div>

          <!-- Content -->
          <div class="p-5 max-h-[60vh] overflow-y-auto space-y-3">
            <div v-if="history.length === 0" class="text-center py-10">
              <Clock class="mx-auto h-8 w-8 text-slate-600 mb-3" />
              <p class="text-slate-400 text-sm">No valuation runs recorded in this session.</p>
              <p class="text-slate-500 text-xs mt-1">Execute the valuation engine to see history here.</p>
            </div>

            <div v-for="(run, idx) in history" :key="idx" class="card-inset p-3 rounded-lg border border-white/[0.03]">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-medium text-slate-300">Run {{ history.length - idx }}</span>
                <span class="text-[10px] font-mono text-slate-500">{{ run.timestamp }}</span>
              </div>
              <div class="text-[11px] text-slate-400 mb-2">
                {{ formatProduct(run.product) }} · Age {{ run.age }} <span v-if="run.product !== 'whole_life'">· {{ run.term }} Yr</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300">
                  BEL: <strong :class="run.bel < 0 ? 'text-emerald-400' : 'text-amber-400'">{{ formatCurrency(run.bel) }}</strong>
                </span>
              </div>
            </div>
          </div>
          
          <div class="px-5 py-4 border-t border-white/[0.06] bg-slate-900/50">
            <p class="text-[10px] text-slate-500 text-center">History is kept for the duration of your browser session.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
