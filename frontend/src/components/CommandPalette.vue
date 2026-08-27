<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { Search, Play, Download, Upload, Clock, Activity, LayoutDashboard, Target } from 'lucide-vue-next'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue', 'action'])

const searchInput = ref(null)
const searchQuery = ref('')
const selectedIndex = ref(0)

const actions = [
  { id: 'run_valuation', title: 'Run Valuation Engine', subtitle: 'Execute deterministic and stochastic engines', icon: Play, color: 'text-sky-400' },
  { id: 'export_csv', title: 'Export Valuation CSV', subtitle: 'Download reserve profiles as CSV', icon: Download, color: 'text-emerald-400' },
  { id: 'upload_table', title: 'Upload Mortality Table', subtitle: 'Import custom CSV mortality assumptions', icon: Upload, color: 'text-amber-400' },
  { id: 'view_history', title: 'View Run History', subtitle: 'See previous valuation parameters', icon: Clock, color: 'text-purple-400' },
  { id: 'tab_overview', title: 'Overview Dashboard', subtitle: 'Switch to main summary', icon: LayoutDashboard, color: 'text-slate-400' },
  { id: 'tab_sensitivity', title: 'Sensitivity Analysis', subtitle: 'Switch to stress testing', icon: Target, color: 'text-rose-400' }
]

const filteredActions = ref([...actions])

watch(searchQuery, (newVal) => {
  if (!newVal) {
    filteredActions.value = [...actions]
  } else {
    const q = newVal.toLowerCase()
    filteredActions.value = actions.filter(a => 
      a.title.toLowerCase().includes(q) || a.subtitle.toLowerCase().includes(q)
    )
  }
  selectedIndex.value = 0
})

watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    searchQuery.value = ''
    selectedIndex.value = 0
    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})

function close() {
  emit('update:modelValue', false)
}

function handleKeydown(e) {
  if (!props.modelValue) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % filteredActions.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value - 1 + filteredActions.value.length) % filteredActions.value.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (filteredActions.value[selectedIndex.value]) {
      executeAction(filteredActions.value[selectedIndex.value])
    }
  } else if (e.key === 'Escape') {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function executeAction(action) {
  emit('action', action.id)
  close()
}
</script>

<template>
  <div v-if="modelValue" class="relative z-50" role="dialog" aria-modal="true">
    <div class="fixed inset-0 bg-slate-900/80 backdrop-blur-sm transition-opacity" @click="close"></div>

    <div class="fixed inset-0 z-10 w-screen overflow-y-auto p-4 sm:p-6 md:p-20">
      <div class="mx-auto max-w-xl transform divide-y divide-slate-800 overflow-hidden rounded-xl bg-slate-900 border border-slate-700 shadow-2xl transition-all">
        <div class="relative">
          <Search class="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-slate-500" />
          <input
            ref="searchInput"
            v-model="searchQuery"
            class="h-12 w-full bg-transparent pl-11 pr-4 text-slate-200 placeholder:text-slate-500 focus:ring-0 sm:text-sm border-0 outline-none"
            placeholder="Type a command or search..."
          />
        </div>

        <ul v-if="filteredActions.length > 0" class="max-h-80 scroll-py-2 overflow-y-auto p-2" role="listbox">
          <li
            v-for="(action, idx) in filteredActions"
            :key="action.id"
            @click="executeAction(action)"
            @mouseenter="selectedIndex = idx"
            :class="[
              'cursor-pointer select-none rounded-md px-3 py-2',
              selectedIndex === idx ? 'bg-slate-800 text-white' : 'text-slate-300'
            ]"
            role="option"
            :aria-selected="selectedIndex === idx"
          >
            <div class="flex items-center space-x-3">
              <component :is="action.icon" :class="['h-5 w-5 flex-shrink-0', action.color]" />
              <div class="flex flex-col">
                <span class="text-sm font-medium">{{ action.title }}</span>
                <span class="text-xs text-slate-500">{{ action.subtitle }}</span>
              </div>
            </div>
          </li>
        </ul>

        <div v-else class="px-6 py-14 text-center text-sm sm:px-14">
          <Search class="mx-auto h-6 w-6 text-slate-500" />
          <p class="mt-4 font-semibold text-slate-300">No results found</p>
          <p class="mt-2 text-slate-500">We couldn't find anything with that term. Please try again.</p>
        </div>
      </div>
    </div>
  </div>
</template>
