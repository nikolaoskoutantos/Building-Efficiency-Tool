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

        <div v-if="statusMessage" class="text-center mb-3">
          <output class="spinner-border spinner-border-sm me-2">
            <span class="visually-hidden">Loading...</span>
          </output>
          <span class="text-primary">{{ statusMessage }}</span>
        </div>

        <CButton
          color="primary"
          class="w-100 mb-3"
          @click="connectWallet"
          :disabled="isBusy"
        >
          {{ buttonLabel }}
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
import { computed, ref } from 'vue'
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
const appKitProviderState = useAppKitProvider<Eip1193Provider>('eip155')
const router = useRouter()
const auth = useAuthStore()

const isConnecting = ref(false)
const isSigningMessage = ref(false)
const lastProcessedAddress = ref<string | null>(null)

function extractWalletProvider(value: unknown): Eip1193Provider | null {
  if (!value || typeof value !== 'object') {
    return null
  }

  if ('request' in value && typeof value.request === 'function') {
    return value as Eip1193Provider
  }

  if ('value' in value) {
    const nestedValue = (value as { value?: unknown }).value

    if (nestedValue && typeof nestedValue === 'object' && 'request' in nestedValue && typeof nestedValue.request === 'function') {
      return nestedValue as Eip1193Provider
    }
  }

  return null
}

const activeWalletProvider = computed<Eip1193Provider | null>(() =>
  extractWalletProvider(appKitProviderState?.walletProvider),
)
const isVerifying = computed(() => auth.isVerifying)
const isBusy = computed(() => isConnecting.value || isSigningMessage.value || isVerifying.value)
const statusMessage = computed(() => {
  if (isConnecting.value) {
    return 'Waiting for wallet connection...'
  }

  if (isSigningMessage.value) {
    return 'Please sign the message in your wallet...'
  }

  if (isVerifying.value) {
    return 'Verifying wallet signature...'
  }

  return ''
})
const buttonLabel = computed(() => {
  if (isConnecting.value) {
    return 'Connecting Wallet...'
  }

  if (isSigningMessage.value) {
    return 'Signing Message...'
  }

  if (isVerifying.value) {
    return 'Verifying Login...'
  }

  return 'Connect Wallet'
})

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitForWalletReady(timeoutMs = 12000, stepMs = 250) {
  const startedAt = Date.now()

  while (Date.now() - startedAt < timeoutMs) {
    const address = accountData.value.address ?? null
    const provider = activeWalletProvider.value

    if (address && provider) {
      return { address, provider }
    }

    await sleep(stepMs)
  }

  throw new Error('Wallet connection timed out before AppKit returned both address and provider')
}

function generateNonce() {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}

function createSignMessage(address: string, nonce: string) {
  const timestamp = new Date().toISOString()
  return `Welcome to QoE Application!

Click to sign in and accept the Terms of Service.

This request will not trigger a blockchain transaction or cost any gas fees.

Wallet address: ${address}
Nonce: ${nonce}
Issued at: ${timestamp}`
}

function setBasicWalletData(address: string) {
  auth.setWalletData({
    address,
    chainId: null,
    walletType: 'web3',
    balance: null,
    ensName: null,
    avatar: null,
  })
}

async function signMessage(address: string, providerSource: Eip1193Provider) {
  try {
    isSigningMessage.value = true

    const provider = new ethers.providers.Web3Provider(providerSource)
    const signer = provider.getSigner()
    const nonce = generateNonce()
    const message = createSignMessage(address, nonce)
    const signature = await signer.signMessage(message)

    return {
      address,
      nonce,
      message,
      signature,
    }
  } finally {
    isSigningMessage.value = false
  }
}

async function ensureAuthenticatedBeforeRedirect() {
  if (!auth.isAuthenticated) {
    await sleep(200)
  }
}

async function finalizeSuccessfulLogin(address: string, shouldRedirect: boolean) {
  await ensureAuthenticatedBeforeRedirect()
  lastProcessedAddress.value = address

  if (shouldRedirect) {
    await router.replace('/efficiencytool')
    return
  }

  await router.replace('/efficiencytool')
}

async function authenticateWalletAddress(address: string, providerSource: Eip1193Provider) {
  if (lastProcessedAddress.value === address && auth.isAuthenticated) {
    return
  }

  setBasicWalletData(address)

  const authData = await signMessage(address, providerSource)
  const result = await auth.setSignedMessage(authData)

  if (!result.success) {
    throw new Error(result.error || 'Authentication failed')
  }

  await finalizeSuccessfulLogin(address, result.shouldRedirect)
}

function clearFreshLoginState() {
  auth.isAuthenticated = false
  auth.isVerifying = false
  auth.userProfile = null
  auth.walletAddress = null
  auth.chainId = null
  auth.walletType = null
  auth.balance = null
  auth.ensName = null
  auth.avatar = null
  auth.connected = false
  auth.signedMessage = null
  auth.signature = null
  auth.nonce = null
  auth.clearJwtToken()
  lastProcessedAddress.value = null
}

async function cleanupFailedAuthentication() {
  lastProcessedAddress.value = null
  clearFreshLoginState()

  try {
    await disconnect()
  } catch (error) {
    console.warn('Wallet disconnect after failed authentication did not complete cleanly:', error)
  }
}

async function connectWallet() {
  if (isBusy.value) {
    return
  }

  isConnecting.value = true

  try {
    if (auth.isAuthenticated) {
      clearFreshLoginState()
    } else {
      lastProcessedAddress.value = null
    }

    await open()

    const { address, provider } = await waitForWalletReady()
    await authenticateWalletAddress(address, provider)
  } catch (error) {
    console.error('Wallet authentication failed:', error)
    await cleanupFailedAuthentication()
  } finally {
    isConnecting.value = false
  }
}

async function logout() {
  clearFreshLoginState()

  try {
    await disconnect()
  } catch (error) {
    console.warn('Wallet disconnect during logout did not complete cleanly:', error)
  }

  await router.push('/')
}
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
