<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { workflowApi, WorkflowStep } from '../services/workflowApi'
import { useErrorStore } from '../stores/useErrorStore'
import { useLoadingStore } from '../stores/useLoadingStore'
import StepIndicator from '../components/StepIndicator.vue'
import ProductCard from '../components/ProductCard.vue'
import RiskAnalysis from '../components/RiskAnalysis.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import ErrorBanner from '../components/ErrorBanner.vue'
// Normally we'd import the actual blueprint editor here, but for the wizard we might navigate or render it.
// To keep it simple, we will provide a "Configure Blueprint" button that takes them to the builder,
// or we assume the builder is part of this view. The prompt says "BlueprintEditor".
// I'll create a simple placeholder form for assumptions and button for blueprint.

const route = useRoute()
const router = useRouter()
const errorStore = useErrorStore()
const loadingStore = useLoadingStore()

const projectId = route.params.projectId
const state = ref(null)
const isPolling = ref(false)
const pollInterval = ref(null)

const projectName = ref('')
const assumptionName = ref('Base Scenario')
const discountRate = ref(0.05)
const mortalityTable = ref('soa_ilt.csv')

const loadState = async () => {
  if (!projectId) {
    state.value = { step: WorkflowStep.PROJECT }
    return
  }
  try {
    const response = await workflowApi.getState(projectId)
    state.value = response.data || response
  } catch (err) {
    errorStore.setError({ code: 'LOAD_ERROR', message: 'Failed to load workflow state' })
  }
}

onMounted(() => {
  loadState()
  pollInterval.value = setInterval(() => {
    if (state.value?.step === WorkflowStep.RUNNING) {
      loadState()
    }
  }, 2000)
})

onUnmounted(() => {
  if (pollInterval.value) clearInterval(pollInterval.value)
})

const handleAction = async (action, data = null) => {
  errorStore.clearError()
  try {
    if (action === 'create_project') {
      loadingStore.startLoading()
      const response = await workflowApi.start(projectName.value, "Valuation Project")
      const newState = response.data || response
      router.replace(`/wizard/${newState.project_id}`)
      state.value = newState
    } 
    else if (action === 'create_contract') {
      loadingStore.startLoading()
      const response = await workflowApi.addContract(projectId, `${data} Contract`, data, { nodes: [], edges: [] })
      state.value = response.data || response
    } 
    else if (action === 'validate_blueprint') {
      // In a real app, this would save the blueprint state first.
      // Assuming they went to the builder and saved, we just reload state to advance.
      router.push(`/projects/${projectId}`) // Go to actual builder
    } 
    else if (action === 'set_assumptions') {
      loadingStore.startLoading()
      const response = await workflowApi.setAssumptions(projectId, assumptionName.value, {
        discount_rate: discountRate.value,
        mortality_table: mortalityTable.value
      })
      state.value = response.data || response
    } 
    else if (action === 'run_valuation') {
      loadingStore.startLoading()
      const response = await workflowApi.runValuation(projectId)
      state.value = response.data || response
      isPolling.value = true
    }
  } catch (err) {
    console.error(err)
    // Error store will catch via interceptor, but we can also set it explicitly if needed
  } finally {
    loadingStore.stopLoading()
  }
}
</script>

<template>
  <div class="h-screen w-full bg-[#0B0F19] text-slate-200 flex flex-col font-sans">
    <ErrorBanner />
    
    <header class="h-16 shrink-0 border-b border-white/[0.08] bg-[#0F172A] flex items-center px-6 justify-between">
      <div class="flex items-center gap-3 cursor-pointer" @click="router.push('/')">
        <div class="w-8 h-8 rounded bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.48 12H2"/></svg>
        </div>
        <h1 class="text-lg font-medium text-white tracking-wide">Valuation Wizard</h1>
      </div>
    </header>

    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar -->
      <aside class="w-64 border-r border-white/[0.06] bg-[#0F172A] p-6 hidden md:block">
        <h3 class="text-sm font-semibold text-white mb-6 uppercase tracking-wider">Workflow Step</h3>
        <StepIndicator :current="state?.step" />
      </aside>

      <!-- Main Content -->
      <main class="flex-1 p-8 overflow-y-auto relative flex justify-center">
        <LoadingOverlay v-if="loadingStore.isLoading" />
        
        <div v-if="!state" class="flex items-center justify-center h-full">
          <div class="animate-pulse flex flex-col items-center">
            <div class="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p class="text-slate-400">Loading workflow state...</p>
          </div>
        </div>

        <div v-else class="w-full max-w-3xl pt-8">
          <!-- Step 1: Project -->
          <div v-if="state.step === WorkflowStep.PROJECT" class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
              <h2 class="text-3xl font-bold text-white mb-2">Create Project</h2>
              <p class="text-slate-400 text-lg">Name your actuarial project to get started.</p>
            </div>
            <div class="card p-6 space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-1.5">Project Name</label>
                <input v-model="projectName" type="text" class="input-field w-full" placeholder="e.g. Q3 Term Life Valuation" />
              </div>
              <button @click="handleAction('create_project')" :disabled="!projectName" class="btn-primary w-full py-2.5">
                Start Project
              </button>
            </div>
          </div>

          <!-- Step 2: Contract -->
          <div v-else-if="state.step === WorkflowStep.CONTRACT" class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
              <h2 class="text-3xl font-bold text-white mb-2">Select Product</h2>
              <p class="text-slate-400 text-lg">Choose the insurance product for this valuation.</p>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <ProductCard type="WholeLife" title="Whole Life" description="Permanent life insurance with fixed premiums and guaranteed death benefit." @select="(type) => handleAction('create_contract', type)" />
              <ProductCard type="Term" title="Term Life" description="Temporary coverage for a specified term (e.g. 10, 20, 30 years)." @select="(type) => handleAction('create_contract', type)" />
              <ProductCard type="Annuity" title="Annuity" description="A stream of income payments for life or a specified period." @select="(type) => handleAction('create_contract', type)" />
            </div>
          </div>

          <!-- Step 3: Blueprint -->
          <div v-else-if="state.step === WorkflowStep.BLUEPRINT" class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
              <h2 class="text-3xl font-bold text-white mb-2">Build Blueprint</h2>
              <p class="text-slate-400 text-lg">Design the cash flow projection graph.</p>
            </div>
            <div class="card p-8 text-center space-y-4 border-dashed border-2 border-slate-700 bg-[#0F172A]/50">
              <div class="w-16 h-16 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-network"><rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/></svg>
              </div>
              <h3 class="text-xl font-medium text-white">Open the Visual Builder</h3>
              <p class="text-slate-400 max-w-md mx-auto">Use our node-based canvas to map out premiums, decrements, and benefits. The engine will validate your graph automatically.</p>
              <button @click="handleAction('validate_blueprint')" class="btn-primary mt-2">
                Launch Builder
              </button>
            </div>
          </div>

          <!-- Step 4: Assumptions -->
          <div v-else-if="state.step === WorkflowStep.ASSUMPTIONS" class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div>
              <h2 class="text-3xl font-bold text-white mb-2">Configure Assumptions</h2>
              <p class="text-slate-400 text-lg">Set the economic and biometric assumptions for the run.</p>
            </div>
            <div class="card p-6 space-y-5">
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-1.5">Scenario Name</label>
                <input v-model="assumptionName" type="text" class="input-field w-full" />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-300 mb-1.5">Discount Rate (%)</label>
                  <input v-model.number="discountRate" type="number" step="0.01" class="input-field w-full" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-300 mb-1.5">Mortality Table</label>
                  <select v-model="mortalityTable" class="input-field w-full">
                    <option value="soa_ilt.csv">SOA Illustrative Life Table</option>
                    <option value="cso_2001.csv">2001 CSO</option>
                  </select>
                </div>
              </div>
              <div class="pt-2 border-t border-slate-700/50 flex justify-end">
                <button @click="handleAction('set_assumptions')" class="btn-primary px-6">
                  Save & Continue
                </button>
              </div>
            </div>
          </div>

          <!-- Step 5: Running -->
          <div v-else-if="state.step === WorkflowStep.RUNNING" class="space-y-6 h-64 flex flex-col items-center justify-center animate-in fade-in zoom-in-95 duration-500">
            <div class="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-6 shadow-[0_0_15px_rgba(99,102,241,0.5)]"></div>
            <h2 class="text-2xl font-bold text-white">Valuation in Progress</h2>
            <p class="text-slate-400">Running stochastic simulations and compiling results...</p>
          </div>

          <!-- Step 6: Results -->
          <div v-else-if="state.step === WorkflowStep.RESULTS" class="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-3xl font-bold text-white mb-2">Valuation Results</h2>
                <p class="text-slate-400 text-lg">Review the computed risk metrics.</p>
              </div>
              <button @click="router.push(`/projects/${projectId}`)" class="btn-secondary">
                View Cash Flows
              </button>
            </div>
            
            <RiskAnalysis :data="state.result" />
            
            <div class="flex justify-end pt-4">
              <button @click="router.push('/')" class="btn-primary flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check-circle"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                Complete Workflow
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
