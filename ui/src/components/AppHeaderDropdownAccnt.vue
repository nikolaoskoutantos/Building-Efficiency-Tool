<script setup>
import avatar from '@/assets/images/avatars/8.jpg'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import Alerts from '@/components/Alerts.vue'

const auth = useAuthStore()
const showAlerts = ref(false)

function handleLogout() {
  auth.logout()
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
       ROLE ?? NOT AVAILABLE
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
