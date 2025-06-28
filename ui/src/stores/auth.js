import { defineStore } from 'pinia'
import { buildApiUrl } from '../config/api.js'
import { useDisconnect } from '@reown/appkit/vue' // ✅ Correct Reown hook

export const useAuthStore = defineStore('auth', {
  state: () => ({
    walletAddress: null,
    chainId: null,
    isAuthenticated: false,
    userProfile: null,
    sessionToken: null,
    jwtToken: null, // Add JWT token storage
    walletType: null,
    balance: null,
    ensName: null,
    avatar: null,
    permissions: [],
    lastLogin: null,
    connected: false,
    // New state for message signing
    signedMessage: null,
    signature: null,
    nonce: null,
    isVerifying: false,
  }),

  actions: {
    setWalletData({ address, chainId, walletType, balance, ensName, avatar }) {
      this.walletAddress = address
      this.chainId = chainId
      this.walletType = walletType
      this.balance = balance
      this.ensName = ensName
      this.avatar = avatar
      this.connected = true
      this.lastLogin = new Date().toISOString()
      // Don't set isAuthenticated here - only after backend verification
      // this.isAuthenticated = true
    },

    // New method to handle signed message and backend verification
    async setSignedMessage({ message, signature, nonce, address }) {
      try {
        this.isVerifying = true
        this.signedMessage = message
        this.signature = signature
        this.nonce = nonce
        
        // Send to backend for verification
        const authResult = await this.verifySignatureWithBackend({
          message,
          signature,
          nonce,
          address
        })
        
        if (authResult.success) {
          console.log('✅ Authentication successful with backend!')
          return { success: true, shouldRedirect: authResult.shouldRedirect }
        } else {
          throw new Error(authResult.error || 'Backend verification failed')
        }
      } catch (error) {
        console.error('❌ Backend verification failed:', error)
        // Reset auth state on failure
        this.isAuthenticated = false
        this.signedMessage = null
        this.signature = null
        this.nonce = null
        throw error
      } finally {
        this.isVerifying = false
      }
    },

    // Backend API call to verify signature
    async verifySignatureWithBackend({ message, signature, nonce, address }) {
      try {
        const response = await fetch(buildApiUrl('/auth/login'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include', // Important for session cookies
          body: JSON.stringify({
            message,
            signature,
            nonce,
            address
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const result = await response.json()
        
        // Handle authentication response (JWT or session-based)
        if (result.success) {
          console.log('✅ Backend authentication successful')
          console.log('📝 Login result:', {
            success: result.success,
            user: result.user,
            role: result.role,
            wallet: result.wallet,
            auth_method: result.auth_method,
            hasToken: !!result.token
          })
          
          // Update basic auth state - SET THESE TOGETHER FOR ATOMICITY
          this.isAuthenticated = true
          this.userProfile = {
            user: result.user,
            role: result.role,
            wallet: result.wallet,
            auth_method: result.auth_method
          }
          this.walletAddress = result.wallet
          
          // Handle JWT token if present
          if (result.token) {
            console.log('🔑 JWT token received, storing...')
            this.setJwtToken(result.token)
          } else {
            console.log('🍪 Session-based authentication (no JWT token)')
            // Clear any existing JWT token since we're using session-based auth
            this.clearJwtToken()
          }
          
          console.log('✅ Auth state updated after login')
          this.debugAuthState()
          
          // Force a small delay to ensure reactivity has propagated
          await new Promise(resolve => setTimeout(resolve, 10))
          
          return { ...result, shouldRedirect: true }
        } else {
          throw new Error(result.message || 'Authentication failed')
        }
        
      } catch (error) {
        console.error('❌ Backend API call failed:', error)
        return { 
          success: false, 
          error: error.message || 'Failed to communicate with backend' 
        }
      }
    },

    async logout() {
      console.log('🚪 Starting logout process...')
      this.debugAuthState()
      
      // Set logout flag IMMEDIATELY to prevent race conditions
      this.isAuthenticated = false
      this.isVerifying = false
      
      try {
        // Include JWT token in logout request if available
        const token = this.getJwtToken()
        const headers = { 'Content-Type': 'application/json' }
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
          console.log('📤 Sending logout request to backend with JWT token...')
        }
        
        // Call backend logout endpoint to clear session
        await fetch(buildApiUrl('/auth/logout'), {
          method: 'POST',
          headers,
          credentials: 'include'
        })
        
        console.log('✅ Backend logout successful')
      } catch (error) {
        console.warn('⚠️ Backend logout failed:', error)
      }

      // Clear JWT token and localStorage FIRST
      console.log('🗑️ Clearing JWT token...')
      this.clearJwtToken()

      // Disconnect wallet
      try {
        const { disconnect } = useDisconnect()
        if (disconnect) {
          console.log('🔌 Disconnecting wallet...')
          await disconnect()
        }
      } catch (err) {
        console.warn('⚠️ Wallet disconnect failed or already disconnected:', err)
      }

      // Reset all auth state
      console.log('🔄 Resetting auth state...')
      this.walletAddress = null
      this.chainId = null
      this.walletType = null
      this.balance = null
      this.ensName = null
      this.avatar = null
      this.connected = false
      this.lastLogin = null
      this.sessionToken = null
      this.jwtToken = null
      this.userProfile = null
      this.permissions = []
      this.signedMessage = null
      this.signature = null
      this.nonce = null
      
      console.log('✅ Logout complete - all auth data cleared')
      this.debugAuthState()
      
      // Add a longer delay to ensure state is fully reset and propagated
      await new Promise(resolve => setTimeout(resolve, 250))
    },

    // JWT Token Management
    setJwtToken(token) {
      console.log('💾 Setting JWT token:', token ? token.substring(0, 20) + '...' : 'null')
      this.jwtToken = token
      // Store JWT in localStorage for persistence
      if (token) {
        localStorage.setItem('jwt_token', token)
        console.log('✅ JWT token stored in localStorage')
      } else {
        localStorage.removeItem('jwt_token')
        console.log('🗑️ JWT token removed from localStorage')
      }
    },

    getJwtToken() {
      // Return stored token or get from localStorage
      return this.jwtToken || localStorage.getItem('jwt_token')
    },

    clearJwtToken() {
      console.log('🗑️ Clearing JWT token and localStorage...')
      this.jwtToken = null
      localStorage.removeItem('jwt_token')
      
      // Also clear any other auth-related localStorage items
      localStorage.removeItem('auth_user')
      localStorage.removeItem('auth_wallet')
      
      // Clear sessionStorage as well (in case anything was stored there)
      sessionStorage.removeItem('jwt_token')
      sessionStorage.removeItem('auth_user')
      
      console.log('✅ JWT token and storage cleared')
    },

    // Initialize JWT token from localStorage on app start
    async initializeAuth() {
      try {
        const storedToken = localStorage.getItem('jwt_token')
        if (storedToken) {
          this.jwtToken = storedToken
          // Validate token with backend and wait for result
          const isValid = await this.validateJwtToken()
          if (isValid) {
            console.log('✅ JWT token restored and validated on app start')
          } else {
            console.log('❌ Stored JWT token was invalid, cleared')
          }
        } else {
          console.log('ℹ️ No stored JWT token found')
        }
      } catch (error) {
        console.error('Auth initialization failed:', error)
      }
    },

    // Validate JWT token with backend
    async validateJwtToken() {
      try {
        const token = this.getJwtToken()
        if (!token) {
          console.log('❌ No JWT token to validate')
          return false
        }

        console.log('🔄 Validating JWT token with backend...')
        const response = await fetch(buildApiUrl('/auth/me'), {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const userData = await response.json()
          console.log('✅ JWT token valid, updating auth state:', userData)
          
          // Update auth state with validated user data
          this.isAuthenticated = true
          this.userProfile = userData
          this.walletAddress = userData.wallet || userData.user
          
          return true
        } else {
          console.log('❌ JWT token invalid, status:', response.status)
          // Token is invalid, clear it
          this.clearJwtToken()
          this.isAuthenticated = false
          this.userProfile = null
          this.walletAddress = null
          return false
        }
      } catch (error) {
        console.error('JWT validation failed:', error)
        this.clearJwtToken()
        this.isAuthenticated = false
        this.userProfile = null
        this.walletAddress = null
        return false
      }
    },

    // Debug method to check auth state
    debugAuthState() {
      console.log('🔍 Current Auth State:', {
        isAuthenticated: this.isAuthenticated,
        hasJwtToken: !!this.getJwtToken(),
        jwtToken: this.getJwtToken()?.substring(0, 20) + '...',
        userProfile: this.userProfile,
        walletAddress: this.walletAddress,
        sessionToken: this.sessionToken
      })
    },

    // Force clear all authentication data (nuclear option)
    forceLogout() {
      console.log('💥 Force logout - clearing ALL auth data...')
      
      // Clear all possible storage locations
      localStorage.clear() // Nuclear option - clears everything
      sessionStorage.clear()
      
      // Reset all state
      this.$reset() // Pinia built-in method to reset store to initial state
      
      console.log('✅ Force logout complete')
    },

    // Force reset all auth state - useful for logout or error conditions
    forceResetState() {
      console.log('🔄 Force resetting all auth state...')
      this.isAuthenticated = false
      this.isVerifying = false
      this.walletAddress = null
      this.chainId = null
      this.walletType = null
      this.balance = null
      this.ensName = null
      this.avatar = null
      this.connected = false
      this.lastLogin = null
      this.sessionToken = null
      this.jwtToken = null
      this.userProfile = null
      this.permissions = []
      this.signedMessage = null
      this.signature = null
      this.nonce = null
      
      // Clear localStorage
      this.clearJwtToken()
      
      console.log('✅ Force reset complete')
      this.debugAuthState()
    },
  },

  // Computed properties
  getters: {
    // Check if user is fully authenticated (both flags set)
    isFullyAuthenticated(state) {
      return state.isAuthenticated && !!state.userProfile
    },
  }
})
