<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen bg-[#070b14] text-slate-300 py-12 px-6 sm:px-12 lg:px-24 selection:bg-sky-500/30">
    <div class="max-w-4xl mx-auto space-y-8">
      <!-- Header -->
      <header class="border-b border-slate-800 pb-8 flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-white tracking-tight mb-2">Privacy Policy</h1>
          <p class="text-sm text-slate-500">Effective Date: October 2026</p>
        </div>
        <button 
          @click="router.push('/')" 
          class="flex items-center space-x-2 px-4 py-2 bg-slate-900 border border-slate-700 hover:border-sky-500 hover:text-sky-400 rounded-lg text-sm font-medium transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
          <span>Back to Dashboard</span>
        </button>
      </header>

      <!-- Content -->
      <article class="prose prose-invert prose-slate max-w-none space-y-8">
        
        <section>
          <h2 class="text-xl font-semibold text-white mb-3">1. Information We Collect</h2>
          <p class="leading-relaxed">
            Actura collects necessary information to provide enterprise-grade valuation services. This includes account credentials, license keys, and any user-uploaded actuarial inputs such as portfolio CSV batches, custom mortality tables, or contract blueprints.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-semibold text-white mb-3">2. Data Processing & Security</h2>
          <p class="leading-relaxed">
            The confidentiality of your actuarial data is paramount. All uploaded simulation inputs, contract definitions, and deterministic/stochastic processing payloads are transmitted via secure connections. 
          </p>
          <p class="leading-relaxed mt-2">
            During heavy stochastic computations, data is temporarily staged in secure memory enclaves. We employ industry-standard encryption to ensure that proprietary cash-flow data and reserve calculations remain strictly confidential. Actura does not sell or distribute your models to third parties.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-semibold text-white mb-3">3. Cookies & Analytics</h2>
          <p class="leading-relaxed">
            The Actura dashboard uses essential tracking and session cookies strictly for maintaining active user sessions (e.g., verifying Pro License status during WebSocket streaming) and ensuring the Neo-skeuomorphic UI performs optimally. We do not use third-party advertising cookies.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-semibold text-white mb-3">4. User Rights</h2>
          <p class="leading-relaxed">
            You maintain full ownership of the data you upload to Actura. You reserve the right to:
          </p>
          <ul class="list-disc pl-5 mt-2 space-y-1">
            <li>Request a full export of your configured mortality tables and logic blueprints.</li>
            <li>Delete your account and invoke the permanent erasure of all associated portfolio data.</li>
            <li>Correct or update institutional contact and billing information.</li>
          </ul>
        </section>

      </article>

      <footer class="pt-8 border-t border-slate-800 text-sm text-slate-500 text-center">
        © 2026 Actura. All rights reserved.
      </footer>
    </div>
  </div>
</template
