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

        <CButton color="primary" class="w-100 mb-3" @click="connectWallet">Connect Wallet</CButton>
        <CButton color="secondary" class="w-100" @click="logout">Logout</CButton>

        <p class="text-center mt-4 text-muted">
          Don’t have a wallet? <a href="https://metamask.io/" target="_blank">Get MetaMask</a>
        </p>
      </CContainer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppKit, useAppKitAccount } from '@reown/appkit/vue'

const { open, disconnect } = useAppKit()
const accountData = useAppKitAccount()
const router = useRouter()
const auth = useAuthStore()

async function connectWallet() {
  try {
    await open()
  } catch (err) {
    console.error('❌ Wallet connection failed:', err)
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
  (address) => {
    if (address) {
      auth.setWalletData({
        address,
        chainId: accountData.value.chainId,
        walletType: accountData.value.walletType,
        balance: accountData.value.balance,
        ensName: accountData.value.ensName,
        avatar: accountData.value.avatar,
      })
      router.push('/dashboard')
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
