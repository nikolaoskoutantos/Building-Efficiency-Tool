import { defineStore } from 'pinia'
import { useDisconnect } from '@reown/appkit/vue' // ✅ Correct Reown hook

export const useAuthStore = defineStore('auth', {
  state: () => ({
    walletAddress: null,
    chainId: null,
    isAuthenticated: false,
    userProfile: null,
    sessionToken: null,
    walletType: null,
    balance: null,
    ensName: null,
    avatar: null,
    permissions: [],
    lastLogin: null,
    connected: false,
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
      this.isAuthenticated = true
    },

    async logout() {
      try {
        const { disconnect } = useDisconnect() // ✅ Safe access
        if (disconnect) await disconnect()
      } catch (err) {
        console.warn('No disconnect function or already disconnected:', err)
      }

      // Reset state
      this.walletAddress = null
      this.chainId = null
      this.walletType = null
      this.balance = null
      this.ensName = null
      this.avatar = null
      this.connected = false
      this.lastLogin = null
      this.isAuthenticated = false
      this.sessionToken = null
      this.permissions = []
    }
  }
})
