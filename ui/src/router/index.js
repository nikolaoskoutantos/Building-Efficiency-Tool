import { createRouter, createWebHashHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout'
import { useAuthStore } from '@/stores/auth'
import { buildApiUrl } from '@/config/api.js'

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
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth) {
    console.log('🔒 Protected route accessed:', to.path)
    console.log('🔍 Auth state check:', {
      hasJwtToken: !!auth.getJwtToken(),
      isAuthenticated: auth.isAuthenticated,
      userProfile: !!auth.userProfile,
      isVerifying: auth.isVerifying,
      fromRoute: from.path
    })
    
    // If currently verifying (during login), wait briefly and check again
    if (auth.isVerifying) {
      console.log('⏳ Auth verification in progress, waiting...')
      await new Promise(resolve => setTimeout(resolve, 200))
      
      // Check again after waiting
      if (auth.isAuthenticated) {
        console.log('✅ Auth completed during wait, allowing access')
        next()
        return
      }
    }
    
    // Check if user is already authenticated - be more flexible about userProfile
    if (auth.isAuthenticated) {
      console.log('✅ User authenticated, allowing access')
      next()
      return
    }
    
    // Check JWT token first
    const jwtToken = auth.getJwtToken()
    
    if (jwtToken) {
      // We have a JWT token, validate it
      console.log('🔄 Validating JWT token...')
      try {
        const isValid = await auth.validateJwtToken()
        if (isValid) {
          console.log('✅ JWT token valid, allowing access')
          next()
        } else {
          console.log('❌ JWT token invalid, redirecting to login')
          next('/login')
        }
      } catch (error) {
        console.error('JWT validation failed:', error)
        auth.clearJwtToken()
        next('/login')
      }
    } else {
      // No JWT token, try session-based auth as fallback
      console.log('📝 No JWT token, trying session validation...')
      try {
        const response = await fetch(buildApiUrl('/auth/me'), {
          credentials: 'include'
        })
        
        if (response.ok) {
          const userData = await response.json()
          auth.isAuthenticated = true
          auth.userProfile = userData
          auth.walletAddress = userData.wallet || userData.user
          console.log('✅ Session valid, allowing access')
          next()
        } else {
          console.log('❌ No valid session, redirecting to login')
          next('/login')
        }
      } catch (error) {
        console.warn('Session validation failed:', error)
        next('/login')
      }
    }
  } else {
    next()
  }
})

export default router
