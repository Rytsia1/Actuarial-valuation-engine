import { createRouter, createWebHistory } from 'vue-router'
import ProjectDashboardView from '../views/ProjectDashboardView.vue'
import ContractBuilderView from '../views/ContractBuilderView.vue'
import MainDashboard from '../views/MainDashboard.vue'
import TermsOfService from '../views/TermsOfService.vue'
import PrivacyPolicy from '../views/PrivacyPolicy.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: ProjectDashboardView,
  },
  {
    path: '/sandbox',
    name: 'Sandbox',
    component: MainDashboard,
  },
  {
    path: '/projects/:id',
    name: 'ContractBuilder',
    component: ContractBuilderView,
  },
  {
    path: '/wizard/:projectId?',
    name: 'ValuationWizard',
    component: () => import('../views/ValuationWizardView.vue'),
  },
  {
    path: '/terms',
    name: 'Terms',
    component: TermsOfService,
  },
  {
    path: '/privacy',
    name: 'Privacy',
    component: PrivacyPolicy,
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
