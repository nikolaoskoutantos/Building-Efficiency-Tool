import { createRouter, createWebHashHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout'
import { useAuthStore } from '@/stores/auth'

// 1. Define your routes
const routes = [
  {
    path: '/',
    name: 'Home',
    component: DefaultLayout,
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        meta: { requiresAuth: true },
        component: () =>
          import(
            /* webpackChunkName: "dashboard" */ '@/views/dashboard/Dashboard.vue'
          ),
      },
      {
        path: '/efficiencytool',
        name: 'EfficiencyTool',
        meta: { requiresAuth: true },
        component: () => import('@/views/pages/efficiencytool.vue'),
      },
    ],
  },
  {
    path: '/login',
    name: 'LoginWeb3',
    component: () => import('@/views/pages/LoginWeb3.vue'),
  },
]

// 2. Create the router
const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// 3. Global navigation guard
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  // Adjust this check depending on your actual auth logic (e.g., wallet address or token)
  const isAuthenticated = !!auth.walletAddress || !!auth.isAuthenticated

  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
