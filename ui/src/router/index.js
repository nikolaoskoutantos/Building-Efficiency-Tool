import { createRouter, createWebHashHistory } from 'vue-router'
import DefaultLayout from '@/layouts/DefaultLayout'
import { useAuthStore } from '@/stores/auth'
import { buildApiUrl } from '@/config/api.js'
import { normalizeRole } from '@/utils/apiErrors'

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
        meta: { requiresAuth: true, allowedRoles: ['BUILDING_MANAGER', 'ADMIN'] },
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
    path: '/access-denied',
    name: 'AccessDenied',
    meta: { requiresAuth: true },
    component: () => import('@/views/pages/AccessDenied.vue'),
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

const handleVerificationInProgress = async (to, auth, next) => {
  console.log('⏳ Auth verification in progress, waiting...')
  await new Promise(resolve => setTimeout(resolve, 200))
  
  if (auth.isAuthenticated) {
    if (handleRoleRestriction(to, auth, next)) {
      return true
    }
    console.log('✅ Auth completed during wait, allowing access')
    next()
    return true
  }
  return false
}

const handleRoleRestriction = (to, auth, next) => {
  const allowedRoles = to.meta.allowedRoles
  const currentRole = normalizeRole(auth.userProfile?.role)

  if (Array.isArray(allowedRoles) && allowedRoles.length > 0 && !allowedRoles.includes(currentRole)) {
    console.warn('⛔ Route blocked due to role restrictions', {
      path: to.path,
      role: currentRole,
      allowedRoles,
    })
    next({
      name: 'AccessDenied',
      query: {
        from: to.path,
        required: allowedRoles.join(', '),
      },
    })
    return true
  }

  return false
}

const handleJwtValidation = async (to, auth, next) => {
  console.log('🔄 Validating JWT token...')
  try {
    const isValid = await auth.validateJwtToken()
    if (isValid) {
      if (handleRoleRestriction(to, auth, next)) {
        return
      }
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
}

const handleSessionValidation = async (to, auth, next) => {
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
      if (handleRoleRestriction(to, auth, next)) {
        return
      }
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
    const handled = await handleVerificationInProgress(to, auth, next)
    if (handled) return
  }
  
  // Check if user is already authenticated
  if (auth.isAuthenticated) {
    if (handleRoleRestriction(to, auth, next)) {
      return
    }

    console.log('✅ User authenticated, allowing access')
    next()
    return
  }
  
  // Check JWT token first
  const jwtToken = auth.getJwtToken()
  
  if (jwtToken) {
    await handleJwtValidation(to, auth, next)
  } else {
    await handleSessionValidation(to, auth, next)
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
