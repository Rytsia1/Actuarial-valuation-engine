import { createRouter, createWebHistory } from 'vue-router'
import MainDashboard from '../views/MainDashboard.vue'
import TermsOfService from '../views/TermsOfService.vue'
import PrivacyPolicy from '../views/PrivacyPolicy.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: MainDashboard,
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
