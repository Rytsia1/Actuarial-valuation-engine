<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi } from '../services/projectApi'
import { useProjectStore } from '../stores/useProjectStore'
import EmptyState from '../components/EmptyState.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { useErrorStore } from '../stores/useErrorStore'
import ErrorBanner from '../components/ErrorBanner.vue'

const router = useRouter()
const projectStore = useProjectStore()
const errorStore = useErrorStore()

const projects = ref([])
const isLoading = ref(true)

onMounted(async () => {
  projectStore.clearStore()
  errorStore.clearError()
  await loadProjects()
})

const loadProjects = async () => {
  try {
    isLoading.value = true
    const response = await projectApi.list()
    projects.value = response.data || response // depending on axios setup
  } catch (err) {
    console.error("Failed to load projects", err)
    // Error is handled by global interceptor + useErrorStore
  } finally {
    isLoading.value = false
  }
}

const createProject = async () => {
  const name = prompt('Enter project name:')
  if (!name) return
  
  try {
    isLoading.value = true
    const response = await projectApi.create(name)
    const newProject = response.data || response
    router.push(`/wizard/${newProject.id}`)
  } catch (err) {
    console.error("Failed to create project", err)
  } finally {
    isLoading.value = false
  }
}

const openProject = (project) => {
  projectStore.setCurrentProject(project)
  router.push(`/wizard/${project.id}`)
}
</script>

<template>
  <div class="h-screen w-full bg-[#0B0F19] text-slate-200 flex flex-col font-sans relative">
    
    <ErrorBanner />
    <LoadingOverlay v-if="isLoading" />

    <!-- Header -->
    <header class="h-16 shrink-0 border-b border-white/[0.08] bg-[#0F172A] flex items-center px-6 justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-activity"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.48 12H2"/></svg>
        </div>
        <h1 class="text-lg font-medium text-white tracking-wide">Actura Dashboard</h1>
      </div>
      
      <div class="flex items-center gap-4">
        <router-link to="/sandbox" class="text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-flask-conical"><path d="M10 2v7.31"/><path d="M14 9.3V1.99"/><path d="M8.5 2h7"/><path d="M14 9.3a6.5 6.5 0 1 1-4 0"/><path d="M5.52 16h12.96"/></svg>
          Legacy Features (Sandbox)
        </router-link>

        <div class="w-px h-4 bg-white/[0.1]"></div>

        <button @click="createProject" class="h-9 px-4 rounded-md bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20">
          New Project
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 overflow-auto p-8 relative">
      <div v-if="!isLoading && projects.length === 0" class="h-full flex items-center justify-center">
        <EmptyState
          title="No projects yet"
          description="Create your first project to start building actuarial valuations and simulating cash flows."
        >
          <template #icon>
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-folder-plus"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/><path d="M12 10v6"/><path d="M9 13h6"/></svg>
          </template>
        </EmptyState>
      </div>

      <div v-else-if="!isLoading" class="max-w-6xl mx-auto">
        <h2 class="text-2xl font-semibold text-white mb-6">My Projects</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div 
            v-for="project in projects" 
            :key="project.id"
            @click="openProject(project)"
            class="group cursor-pointer rounded-xl border border-white/[0.08] bg-[#0F172A] p-6 hover:border-indigo-500/50 hover:bg-[#151f38] transition-all duration-300 hover:shadow-xl hover:shadow-indigo-500/10 flex flex-col h-48"
          >
            <div class="flex items-start justify-between mb-4">
              <h3 class="text-lg font-medium text-slate-200 group-hover:text-indigo-400 transition-colors">{{ project.name }}</h3>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right text-slate-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </div>
            
            <p class="text-slate-400 text-sm flex-1 line-clamp-3">
              {{ project.description || 'No description provided.' }}
            </p>
            
            <div class="mt-4 pt-4 border-t border-white/[0.05] flex items-center justify-between text-xs text-slate-500">
              <span class="flex items-center gap-1.5">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-clock"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                Updated {{ new Date(project.updated_at).toLocaleDateString() }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
