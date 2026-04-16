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
          <output class="spinner-border spinner-border-sm me-2">
            <span class="visually-hidden">Loading...</span>
          </output>
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
        <CButton color="secondary" class="w-100" @click="logout">Register</CButton>

        <p class="text-center mt-4 text-muted">
          Don’t have a wallet? <a href="https://metamask.io/" target="_blank">Get MetaMask</a>
        </p>
      </CContainer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useAppKit, useAppKitAccount, useAppKitProvider, useDisconnect } from '@reown/appkit/vue'
import { ethers } from 'ethers'

type Eip1193Provider = {
  request: (args: { method: string; params?: unknown[] | object }) => Promise<unknown>
  on?: (...args: unknown[]) => void
  removeListener?: (...args: unknown[]) => void
}

const { open } = useAppKit()
const { disconnect } = useDisconnect()
const accountData = useAppKitAccount()
const { walletProvider } = useAppKitProvider<Eip1193Provider>('eip155')
const router = useRouter()
const auth = useAuthStore()

// Loading state for message signing
const isSigningMessage = ref(false)
const lastProcessedAddress = ref<string | null>(null)
const activeEthereumProvider = computed<Eip1193Provider | null>(() => {
  if (walletProvider?.value) {
    return walletProvider.value
  }

  const globalEthereum = (globalThis as typeof globalThis & { ethereum?: Eip1193Provider }).ethereum
  return globalEthereum ?? null
})

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

    lastProcessedAddress.value = null
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

    const providerSource = activeEthereumProvider.value
    if (!providerSource) {
      throw new Error('No wallet provider found from AppKit or browser wallet')
    }

    const provider = new ethers.providers.Web3Provider(providerSource)
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

function canStartWalletAuthentication(address?: string | null, provider?: Eip1193Provider | null) {
  if (!address || !provider) {
    return false
  }

  if (isSigningMessage.value || auth.isVerifying) {
    return false
  }

  if (lastProcessedAddress.value === address && auth.isAuthenticated) {
    return false
  }

  return true
}

function setBasicWalletData(address: string) {
  auth.setWalletData({
    address,
    chainId: null, // Will be set by the provider
    walletType: 'web3',
    balance: null,
    ensName: null,
    avatar: null,
  })
}

async function ensureAuthenticatedBeforeRedirect() {
  if (!auth.isAuthenticated) {
    console.warn('⚠️ Auth state not set properly, waiting longer...')
    await new Promise(resolve => setTimeout(resolve, 200))
  }
}

async function finalizeSuccessfulLogin(address: string, shouldRedirect: boolean) {
  if (shouldRedirect) {
    console.log('✅ Redirecting to dashboard...')
  } else {
    console.log('✅ Login successful but no redirect flag')
  }

  await ensureAuthenticatedBeforeRedirect()
  lastProcessedAddress.value = address
  await router.replace('/efficiencytool')
}

async function authenticateWalletAddress(address: string) {
  setBasicWalletData(address)

  const authData = await signMessage(address)

  console.log('🔐 About to call setSignedMessage...')
  auth.debugAuthState()

  const result = await auth.setSignedMessage(authData)

  console.log('🎯 Login result:', result)
  console.log('🔍 Auth state after setSignedMessage:')
  auth.debugAuthState()

  if (!result.success) {
    throw new Error(result.error || 'Authentication failed')
  }

  await finalizeSuccessfulLogin(address, result.shouldRedirect)
}

watch(
  () => [accountData.value.address, activeEthereumProvider.value] as const,
  async ([address, provider]) => {
    if (!canStartWalletAuthentication(address, provider)) {
      return
    }

    const walletAddress = address
    if (!walletAddress) {
      return
    }

    try {
      await authenticateWalletAddress(walletAddress)
    } catch (error) {
      console.error('❌ Authentication failed:', error)
      lastProcessedAddress.value = null
      // If signing fails, disconnect wallet
      await disconnect()
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
