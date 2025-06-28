// Debug utility to help troubleshoot login/logout issues
export const debugAuth = {
  // Check all auth-related state
  checkAuthState() {
    console.log('🔍 === AUTH STATE DEBUG ===')
    
    // Check localStorage
    console.log('💾 localStorage:')
    console.log('  jwt_token:', localStorage.getItem('jwt_token')?.substring(0, 20) + '...' || 'null')
    console.log('  auth_user:', localStorage.getItem('auth_user') || 'null')
    console.log('  auth_wallet:', localStorage.getItem('auth_wallet') || 'null')
    
    // Check sessionStorage
    console.log('📝 sessionStorage:')
    console.log('  jwt_token:', sessionStorage.getItem('jwt_token') || 'null')
    console.log('  auth_user:', sessionStorage.getItem('auth_user') || 'null')
    
    // Check auth store
    try {
      const { useAuthStore } = window.Vue?.app?.config?.globalProperties || {}
      if (useAuthStore) {
        const auth = useAuthStore()
        console.log('🏪 Auth Store:')
        auth.debugAuthState()
      }
    } catch (error) {
      console.log('❌ Could not access auth store')
    }
    
    console.log('🔍 === END AUTH STATE DEBUG ===')
  },
  
  // Force clear everything
  forceClearAll() {
    console.log('💥 FORCE CLEARING ALL AUTH STATE')
    
    // Clear localStorage
    const authKeys = ['jwt_token', 'auth_user', 'auth_wallet']
    authKeys.forEach(key => {
      localStorage.removeItem(key)
      sessionStorage.removeItem(key)
    })
    
    // Try to reset auth store
    try {
      const { useAuthStore } = window.Vue?.app?.config?.globalProperties || {}
      if (useAuthStore) {
        const auth = useAuthStore()
        auth.forceLogout()
      }
    } catch (error) {
      console.log('❌ Could not access auth store for force reset')
    }
    
    console.log('✅ Force clear complete')
  },
  
  // Test login flow
  async testLoginFlow() {
    console.log('🧪 Testing login flow...')
    
    // Check initial state
    this.checkAuthState()
    
    console.log('🧪 Test complete - check logs above')
  }
}

// Make it available globally for console debugging
if (typeof window !== 'undefined') {
  window.debugAuth = debugAuth
}
