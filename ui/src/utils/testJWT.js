// JWT Test Utility
// Use this in browser console to test JWT functionality

export const testJWT = {
  // Test JWT token storage
  testTokenStorage() {
    console.log('🧪 Testing JWT Token Storage...')
    
    const testToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoidGVzdCIsInJvbGUiOiJ1c2VyIiwiZXhwIjoxNjcwMDAwMDAwfQ.test'
    
    // Test localStorage
    localStorage.setItem('jwt_token', testToken)
    const retrieved = localStorage.getItem('jwt_token')
    
    console.log('✅ Token stored and retrieved:', retrieved === testToken)
    
    // Clean up
    localStorage.removeItem('jwt_token')
    return retrieved === testToken
  },

  // Test API requests with JWT
  async testApiWithJWT() {
    console.log('🧪 Testing API Requests with JWT...')
    
    try {
      const { apiRequest } = await import('../config/api.js')
      const { useAuthStore } = await import('../stores/auth.js')
      
      const auth = useAuthStore()
      
      // Mock a JWT token
      auth.setJwtToken('test-jwt-token')
      
      // This should include the JWT token in headers
      const response = await apiRequest('/auth/me', {
        method: 'GET'
      })
      
      console.log('📡 API request sent with JWT header')
      return true
    } catch (error) {
      console.error('❌ API test failed:', error)
      return false
    }
  },

  // Test the complete auth flow
  async testAuthFlow() {
    console.log('🧪 Testing Complete Auth Flow...')
    
    try {
      const { useAuthStore } = await import('../stores/auth.js')
      const auth = useAuthStore()
      
      // 1. Test initialization
      auth.initializeAuth()
      console.log('✅ Auth initialized')
      
      // 2. Test token validation (should fail with test token)
      auth.setJwtToken('invalid-test-token')
      const isValid = await auth.validateJwtToken()
      console.log('✅ Token validation tested (expected to fail):', !isValid)
      
      // 3. Test token clearing
      auth.clearJwtToken()
      const clearedToken = auth.getJwtToken()
      console.log('✅ Token cleared:', !clearedToken)
      
      return true
    } catch (error) {
      console.error('❌ Auth flow test failed:', error)
      return false
    }
  }
}

// Make it available globally for console testing
if (typeof window !== 'undefined') {
  window.testJWT = testJWT
}
