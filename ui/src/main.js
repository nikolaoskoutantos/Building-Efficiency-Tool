import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'

import { createAppKit } from '@reown/appkit/vue'
import { Ethers5Adapter } from '@reown/appkit-adapter-ethers5'
import { mainnet, arbitrum, base } from '@reown/appkit/networks'
import { baseSepolia } from './networks/baseSepolia'  // ✅ import your custom network
import '@coreui/coreui/dist/css/coreui.min.css'
// CoreUI
import CoreuiVue from '@coreui/vue'
import CIcon from '@coreui/icons-vue'
import { iconsSet as icons } from '@/assets/icons'
import DocsComponents from '@/components/DocsComponents'
import DocsExample from '@/components/DocsExample'
import DocsIcons from '@/components/DocsIcons'

// ✅ Reown AppKit Setup
createAppKit({
  adapters: [new Ethers5Adapter()],
  networks: [mainnet, arbitrum, base, baseSepolia], // ✅ add baseSepolia here
  projectId: '734b9e874694e044fa1e63fba83e0aa0',
  metadata: {
    name: 'Auth',
    description: 'AppKit Example',
    url: 'https://reown.com/appkit',
    icons: ['https://assets.reown.com/reown-profile-pic.png'],
  },
  features: { analytics: true },
})

// ✅ Vue App Setup
const app = createApp(App)
const pinia = createPinia()

app.use(router)
app.use(pinia)
app.use(CoreuiVue)
app.provide('icons', icons)
app.component('CIcon', CIcon)
app.component('DocsComponents', DocsComponents)
app.component('DocsExample', DocsExample)
app.component('DocsIcons', DocsIcons)

// Initialize auth store and JWT token validation
import { useAuthStore } from './stores/auth'

// Initialize auth store before mounting the app
const initializeApp = async () => {
  const authStore = useAuthStore(pinia)
  
  // Wait for auth initialization to complete
  await authStore.initializeAuth()
  
  // Now mount the app after auth is initialized
  app.mount('#app')
}

// Initialize the app
initializeApp()
