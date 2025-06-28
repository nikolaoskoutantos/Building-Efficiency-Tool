<template>
  <div class="login-wrapper">
    <!-- Left panel (Desktop only) -->
    <div class="visual-panel d-none d-md-flex flex-column justify-content-center align-items-center text-dark p-5">
      <h6 class="small text-uppercase">A Wise Quote</h6>
      <h1 class="display-4 fw-bold mt-4">Get Everything<br />You Want</h1>
      <p class="mt-3 text-center">You can get everything you want if you work hard, trust the process, and stick to the plan.</p>
    </div>

    <!-- Right panel (Login form) -->
    <div class="form-panel d-flex flex-column justify-content-center align-items-center p-5 w-100">
      <CContainer class="w-100" style="max-width: 400px">
        <h2 class="mb-4 text-center">Welcome Back</h2>
        <p class="text-center text-muted mb-4">Sign in using your wallet (Reown AppKit)</p>

        <!-- Show signing status -->
        <div v-if="isSigningMessage" class="text-center mb-3">
          <div class="spinner-border spinner-border-sm me-2" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <span class="text-primary">Please sign the message in your wallet...</span>
        </div>

        <CButton 
          color="primary" 
          class="w-100 mb-3" 
          @click="connectWallet"
          :disabled="isSigningMessage"
        >
          {{ isSigningMessage ? 'Signing Message...' : 'Connect Wallet' }}
        </CButton>
        <CButton color="secondary" class="w-100" @click="logout">Logout</CButton>

        <p class="text-center mt-4 text-muted">
          Don’t have a wallet? <a href="https://metamask.io/" target="_blank">Get MetaMask</a>
        </p>
      </CContainer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useAppKit, useAppKitAccount, useDisconnect } from '@reown/appkit/vue'
import { ethers } from 'ethers'

const { open, close } = useAppKit()
const { disconnect } = useDisconnect()
const accountData = useAppKitAccount()
const router = useRouter()
const auth = useAuthStore()

// Loading state for message signing
const isSigningMessage = ref(false)

async function connectWallet() {
  try {
    console.log('🔗 Starting wallet connection...')
    
    // Reset any previous auth state to ensure clean login
    if (auth.isAuthenticated) {
      console.log('⚠️ User already authenticated, clearing state for fresh login...')
      auth.isAuthenticated = false
      auth.userProfile = null
      auth.clearJwtToken()
    }
    
    await open()
  } catch (err) {
    console.error('❌ Wallet connection failed:', err)
  }
}

// Generate a unique nonce for message signing
function generateNonce() {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}

// Create the message to be signed
function createSignMessage(address: string, nonce: string) {
  const timestamp = new Date().toISOString()
  return `Welcome to QoE Application!

Click to sign in and accept the Terms of Service.

This request will not trigger a blockchain transaction or cost any gas fees.

Wallet address: ${address}
Nonce: ${nonce}
Issued at: ${timestamp}`
}

// Sign message with wallet
async function signMessage(address: string) {
  try {
    isSigningMessage.value = true
    
    // Get provider from window (MetaMask, etc.)
    if (!window.ethereum) {
      throw new Error('No Ethereum provider found')
    }
    
    const provider = new ethers.providers.Web3Provider(window.ethereum)
    const signer = provider.getSigner()
    
    // Generate nonce and message
    const nonce = generateNonce()
    const message = createSignMessage(address, nonce)
    
    console.log('📝 Signing message:', message)
    
    // Sign the message
    const signature = await signer.signMessage(message)
    
    console.log('✅ Message signed successfully!')
    
    return {
      message,
      signature,
      nonce,
      address
    }
  } catch (error) {
    console.error('❌ Message signing failed:', error)
    throw error
  } finally {
    isSigningMessage.value = false
  }
}

async function logout() {
  await disconnect()
  auth.setWalletData({
    address: null,
    chainId: null,
    walletType: null,
    balance: null,
    ensName: null,
    avatar: null,
  })
  router.push('/')
}

watch(
  () => accountData.value.address,
  async (address) => {
    if (address) {
      try {
        // First set basic wallet data
        auth.setWalletData({
          address,
          chainId: null, // Will be set by the provider
          walletType: 'web3',
          balance: null,
          ensName: null,
          avatar: null,
        })
        
        // Then sign the authentication message
        const authData = await signMessage(address)
        
        console.log('🔐 About to call setSignedMessage...')
        auth.debugAuthState()
        
        // Store the signed message in auth store and get result
        const result = await auth.setSignedMessage(authData)
        
        console.log('🎯 Login result:', result)
        console.log('🔍 Auth state after setSignedMessage:')
        auth.debugAuthState()
        
        // Redirect to dashboard if authentication was successful
        if (result.success && result.shouldRedirect) {
          console.log('✅ Redirecting to dashboard...')
          
          // Verify auth state before redirect
          if (!auth.isAuthenticated) {
            console.warn('⚠️ Auth state not set properly, waiting longer...')
            await new Promise(resolve => setTimeout(resolve, 200))
          }
          
          // Use replace instead of push to avoid back navigation issues
          await router.replace('/dashboard')
        } else if (result.success) {
          console.log('✅ Login successful but no redirect flag')
          
          // Verify auth state before redirect
          if (!auth.isAuthenticated) {
            console.warn('⚠️ Auth state not set properly, waiting longer...')
            await new Promise(resolve => setTimeout(resolve, 200))
          }
          
          // Still redirect if login was successful
          await router.replace('/dashboard')
        } else if (!result.success) {
          throw new Error(result.error || 'Authentication failed')
        }
      } catch (error) {
        console.error('❌ Authentication failed:', error)
        // If signing fails, disconnect wallet
        await disconnect()
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.login-wrapper {
  display: flex;
  min-height: 100vh;
  background-color: #f8f9fa;
}

/* Left panel (quote + image) */
.visual-panel {
  background-image: url('@/assets/images/login.jpg'); /* Your image path */
  background-size: cover;
  background-position: center;
  width: 50%;
  color: #111;
}

/* Right panel (form) */
.form-panel {
  width: 100%;
  max-width: 50%;
  background-color: #fff;
}

@media (max-width: 768px) {
  .login-wrapper {
    flex-direction: column;
    background-image: url('@/assets/images/login.jpg');
    background-size: cover;
    background-position: center;
  }

  .visual-panel {
    display: none !important;
  }

  .form-panel {
    max-width: 100%;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 2rem 1rem;

    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 100vh; /* ⬅️ fills the screen height */
  }

  .form-panel > .container {
    margin-top: auto;
    margin-bottom: auto; /* ⬅️ centers content vertically */
  }
}

</style>
