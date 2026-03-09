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
    redirect: '/efficiencytool',
    children: [
      {
        path: '/efficiencytool',
        name: 'EfficiencyTool',
        meta: { requiresAuth: true },
        component: () => import('@/views/pages/efficiencytool.vue'),
      },
      {
        path: '/device-registration',
        name: 'DeviceRegistration',
        meta: { requiresAuth: true },
        component: () => import('@/views/forms/DeviceRegistration.vue'),
      },
      {
        path: '/settings',
        name: 'Settings',
        meta: { requiresAuth: true },
        component: () => import('@/views/pages/Settings.vue'),
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

// Helper functions to reduce cognitive complexity
const logAuthState = (to, from, auth) => {
  console.log('🔒 Protected route accessed:', to.path)
  console.log('🔍 Auth state check:', {
    hasJwtToken: !!auth.getJwtToken(),
    isAuthenticated: auth.isAuthenticated,
    userProfile: !!auth.userProfile,
    isVerifying: auth.isVerifying,
    fromRoute: from.path
  })
}

const handleVerificationInProgress = async (auth, next) => {
  console.log('⏳ Auth verification in progress, waiting...')
  await new Promise(resolve => setTimeout(resolve, 200))
  
  if (auth.isAuthenticated) {
    console.log('✅ Auth completed during wait, allowing access')
    next()
    return true
  }
  return false
}

const handleJwtValidation = async (auth, next) => {
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
  return true
}

const handleSessionValidation = async (auth, next) => {
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

const handleProtectedRoute = async (to, from, auth, next) => {
  logAuthState(to, from, auth)
  
  // If currently verifying (during login), wait briefly and check again
  if (auth.isVerifying) {
    const handled = await handleVerificationInProgress(auth, next)
    if (handled) return
  }
  
  // Check if user is already authenticated
  if (auth.isAuthenticated) {
    console.log('✅ User authenticated, allowing access')
    next()
    return
  }
  
  // Check JWT token first
  const jwtToken = auth.getJwtToken()
  
  if (jwtToken) {
    await handleJwtValidation(auth, next)
  } else {
    await handleSessionValidation(auth, next)
  }
}

// 3. Global navigation guard
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth) {
    await handleProtectedRoute(to, from, auth, next)
  } else {
    next()
  }
})

export default router
