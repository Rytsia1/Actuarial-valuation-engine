<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  backendStatus: {
    type: String,
    default: 'checking', // 'healthy', 'error', 'checking'
  },
  activeTab: {
    type: String,
    default: 'overview',
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:activeTab', 'recalculate'])
</script>

<template>
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <!-- Title & Branding -->
      <div class="flex items-center space-x-3">
        <div class="h-9 w-9 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <svg class="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-base font-bold tracking-tight text-white font-sans">
              ACTUARY<span class="text-sky-400">ENGINE</span>
            </h1>
            <span class="px-1.5 py-0.5 text-[10px] font-mono font-semibold rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
              v0.3.0
            </span>
          </div>
          <p class="text-xs text-slate-400 font-mono">
            Valuation, Reserves & Stochastic Risk Engine
          </p>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="hidden md:flex items-center space-x-1 bg-slate-950/60 p-1 rounded-lg border border-slate-800">
        <button
          v-for="tab in [
            { id: 'overview', label: 'Valuation & Reserves' },
            { id: 'stochastic', label: 'Monte Carlo & ESG' },
            { id: 'cashflows', label: 'Cash Flow Rollout' }
          ]"
          :key="tab.id"
          @click="emit('update:activeTab', tab.id)"
          :class="[
            'px-3.5 py-1.5 text-xs font-medium rounded-md transition-all duration-150',
            activeTab === tab.id
              ? 'bg-sky-500 text-white shadow-sm shadow-sky-500/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Actions & Health Status -->
      <div class="flex items-center space-x-4">
        <!-- Backend Status Badge -->
        <div class="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs font-mono">
          <span
            :class="[
              'h-2 w-2 rounded-full animate-pulse',
              backendStatus === 'healthy' ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-rose-400'
            ]"
          ></span>
          <span :class="backendStatus === 'healthy' ? 'text-slate-300' : 'text-rose-400'">
            {{ backendStatus === 'healthy' ? 'SOA ILT API' : 'Disconnected' }}
          </span>
        </div>

        <!-- Recalculate Button -->
        <button
          @click="emit('recalculate')"
          :disabled="loading"
          class="flex items-center space-x-1.5 px-3.5 py-1.5 bg-sky-500 hover:bg-sky-400 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-sm shadow-sky-500/20 transition duration-150"
        >
          <svg
            :class="['h-3.5 w-3.5', loading ? 'animate-spin' : '']"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span>{{ loading ? 'Simulating...' : 'Recalculate' }}</span>
        </button>
      </div>
    </div>
  </header>
</template>
