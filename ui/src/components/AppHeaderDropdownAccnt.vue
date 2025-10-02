<script setup>
import avatar from '@/assets/images/avatars/8.jpg'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import Alerts from '@/components/Alerts.vue'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const showAlerts = ref(false)

async function handleLogout() {
  try {
    console.log('🚪 Initiating logout from dropdown...')
    await auth.logout()
    
    // Add a small delay to ensure state is fully propagated
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Force navigate to login with page reload to clear any lingering state
    console.log('🔄 Navigating to login...')
    await router.push('/login')
    
    // Optional: Force a page reload to completely reset state
    // Uncomment if you still see race conditions
    // window.location.reload()
    
  } catch (error) {
    console.error('❌ Logout failed:', error)
    
    // Force reset state on error
    auth.forceResetState()
    
    // Ensure we navigate to login even on error
    await router.push('/login')
  }
}
</script>

<template>
  <CDropdown placement="bottom-end" variant="nav-item">
    <CDropdownToggle class="py-0 pe-0" :caret="false">
      <CAvatar :src="avatar" size="md" />
    </CDropdownToggle>
    <CDropdownMenu class="pt-0">
      <CDropdownHeader
        component="h6"
        class="bg-body-secondary text-body-secondary fw-semibold mb-2 rounded-top"
      >
        Account
      </CDropdownHeader>
      <CDropdownItem class="fw-bold" style="font-weight: bold;">
       ROLE: Building Manager
      </CDropdownItem>
      <CDropdownItem @click="showAlerts = true">
        <CIcon icon="cil-bell" /> Alerts
      </CDropdownItem>
      <CDropdownHeader
        component="h6"
        class="bg-body-secondary text-body-secondary fw-semibold my-2"
      >
        Profile
      </CDropdownHeader>
      <CDropdownItem>
        <CIcon icon="cil-user" />
        <span class="ms-2">{{ auth.walletAddress ? auth.walletAddress : 'No Wallet Connected' }}</span>
      </CDropdownItem>
      <CDropdownItem>
        <CIcon icon="cil-settings" /> Settings
      </CDropdownItem>
      <CDropdownDivider />
      <CDropdownItem @click="handleLogout">
        <CIcon icon="cil-lock-locked" /> Logout
      </CDropdownItem>
    </CDropdownMenu>
    <Alerts :visible="showAlerts" @close="showAlerts = false" />
  </CDropdown>
</template>
