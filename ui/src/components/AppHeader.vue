// ...existing code...
<script setup>
import Leaderboard from '@/components/Leaderboard.vue'
import { onMounted, ref } from 'vue'
import { useColorModes } from '@coreui/vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useSidebarStore } from '@/stores/sidebar.js'
import { useAppKit } from '@reown/appkit/vue'
import Alerts from '@/components/Alerts.vue'

import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AppHeaderDropdownAccnt from '@/components/AppHeaderDropdownAccnt.vue'
import { useDisconnect } from '@reown/appkit/vue'
import { COffcanvas, COffcanvasHeader, COffcanvasTitle, COffcanvasBody, CListGroup, CListGroupItem, CButton } from '@coreui/vue'
import { useAlertsStore } from '@/stores/alerts.js'

const headerClassNames = ref('mb-4 p-0')
const { colorMode, setColorMode } = useColorModes('coreui-free-vue-admin-template-theme')
const sidebar = useSidebarStore()
const auth = useAuthStore()
const router = useRouter()
const appkit = useAppKit()
const showAlerts = ref(false)
const alertsStore = useAlertsStore()

onMounted(() => {
  document.addEventListener('scroll', () => {
    headerClassNames.value = document.documentElement.scrollTop > 0
      ? 'mb-4 p-0 shadow-sm'
      : 'mb-4 p-0'
  })
})

const { disconnect } = useDisconnect()
const showLeaderboard = ref(false);

function onShowLeaderboard(event) {
  if (event && event.preventDefault) event.preventDefault();
  showLeaderboard.value = true;
}

async function logout() {
  try {
    console.log('🚪 AppHeader: Starting logout...')
    
    // Call the proper auth store logout method (this will clear JWT, call backend, disconnect wallet)
    await auth.logout()
    
    console.log('✅ AppHeader: Logout successful, redirecting to login')
    
    // Add delay to ensure state propagation
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Force redirect with replace to avoid back navigation issues
    await router.replace('/login')
    
  } catch (err) {
    console.error('❌ AppHeader logout failed:', err)
    
    // Force reset state on error
    auth.forceResetState()
    
    // Even if logout fails, redirect to login
    await router.replace('/login')
  }
}

function onShowAlerts(event) {
  if (event && event.preventDefault) event.preventDefault();
  showAlerts.value = true;
}


</script>




<template>
  <CHeader position="sticky" :class="headerClassNames">
    <CContainer class="border-bottom px-4" fluid>
      <CHeaderToggler @click="sidebar.toggleVisible()" style="margin-inline-start: -14px">
        <CIcon icon="cil-menu" size="lg" />
      </CHeaderToggler>
      <CHeaderNav class="d-none d-md-flex">
        <CNavItem>
          <CNavLink href="/dashboard"> Dashboard </CNavLink>
        </CNavItem>
        <CNavItem>
          <CNavLink href="#">Users</CNavLink>
        </CNavItem>
        <CNavItem>
          <CNavLink href="#">Settings</CNavLink>
        </CNavItem>
      </CHeaderNav>
      <CHeaderNav class="ms-auto">
        <CNavItem>
          <CNavLink href="#" @click="onShowAlerts">
            <CIcon icon="cil-bell" size="lg" />
          </CNavLink>
        </CNavItem>
        <CNavItem>
          <CNavLink href="#" @click="onShowLeaderboard">
            <CIcon icon="cil-list" size="lg" />
          </CNavLink>
        </CNavItem>
        <CNavItem>
          <CButton color="danger" size="sm" class="align-self-center ms-2" @click="logout">Logout</CButton>
        </CNavItem>
      </CHeaderNav>
      <CHeaderNav>
        <li class="nav-item py-1">
          <div class="vr h-100 mx-2 text-body text-opacity-75"></div>
        </li>
        <CDropdown variant="nav-item" placement="bottom-end">
          <CDropdownToggle :caret="false">
            <CIcon v-if="colorMode === 'dark'" icon="cil-moon" size="lg" />
            <CIcon v-else-if="colorMode === 'light'" icon="cil-sun" size="lg" />
            <CIcon v-else icon="cil-contrast" size="lg" />
          </CDropdownToggle>
          <CDropdownMenu>
            <CDropdownItem
              :active="colorMode === 'light'"
              class="d-flex align-items-center"
              component="button"
              type="button"
              @click="setColorMode('light')"
            >
              <CIcon class="me-2" icon="cil-sun" size="lg" /> Light
            </CDropdownItem>
            <CDropdownItem
              :active="colorMode === 'dark'"
              class="d-flex align-items-center"
              component="button"
              type="button"
              @click="setColorMode('dark')"
            >
              <CIcon class="me-2" icon="cil-moon" size="lg" /> Dark
            </CDropdownItem>
            <CDropdownItem
              :active="colorMode === 'auto'"
              class="d-flex align-items-center"
              component="button"
              type="button"
              @click="setColorMode('auto')"
            >
              <CIcon class="me-2" icon="cil-contrast" size="lg" /> Auto
            </CDropdownItem>
          </CDropdownMenu>
        </CDropdown>
        <li class="nav-item py-1">
          <div class="vr h-100 mx-2 text-body text-opacity-75"></div>
        </li>
        <AppHeaderDropdownAccnt @logout="logout" />
      </CHeaderNav>
    </CContainer>
    <CContainer class="px-4" fluid>
      <AppBreadcrumb />
    </CContainer>
  </CHeader>
  <Leaderboard :visible="showLeaderboard" @close="showLeaderboard = false" myBuilding="Building B" />
  <Alerts :visible="showAlerts" @close="showAlerts = false" />
</template>
