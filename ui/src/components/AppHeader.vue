// ...existing code...
<script setup>
import Leaderboard from '@/components/Leaderboard.vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useColorModes } from '@coreui/vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useSidebarStore } from '@/stores/sidebar.js'
import { useAlertsStore } from '@/stores/alerts.js'
import Alerts from '@/components/Alerts.vue'

import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AppHeaderDropdownAccnt from '@/components/AppHeaderDropdownAccnt.vue'

const headerClassNames = ref('mb-4 p-0')
const { colorMode, setColorMode } = useColorModes('coreui-free-vue-admin-template-theme')
const sidebar = useSidebarStore()
const auth = useAuthStore()
const alertsStore = useAlertsStore()
const router = useRouter()
const showAlerts = ref(false)
const bellAnimating = ref(false)
const alertsBadge = computed(() => {
  const count = alertsStore.alerts.length
  if (count <= 0) return ''
  return count > 9 ? '9+' : String(count)
})

watch(
  () => alertsStore.alerts.length,
  (nextCount, prevCount) => {
    if (nextCount > prevCount) {
      bellAnimating.value = false
      requestAnimationFrame(() => {
        bellAnimating.value = true
        window.setTimeout(() => {
          bellAnimating.value = false
        }, 720)
      })
    }
  },
)

onMounted(() => {
  document.addEventListener('scroll', () => {
    headerClassNames.value = document.documentElement.scrollTop > 0
      ? 'mb-4 p-0 shadow-sm'
      : 'mb-4 p-0'
  })
})

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

function navigateToSettings(event) {
  if (event && event.preventDefault) event.preventDefault();
  router.push('/settings');
}


</script>




<template>
  <CHeader position="sticky" :class="['app-header-shell', { 'app-header-shell--dark': colorMode === 'dark' }, headerClassNames]">
    <CContainer class="app-header-shell__bar border-bottom px-4" fluid>
      <CHeaderToggler class="app-header-shell__toggler" @click="sidebar.toggleVisible()" style="margin-inline-start: -14px">
        <CIcon icon="cil-menu" size="lg" />
      </CHeaderToggler>
      <CHeaderNav class="d-none d-md-flex app-header-shell__nav">
        <CNavItem>
          <CNavLink href="/dashboard"> Dashboard </CNavLink>
        </CNavItem>
        <CNavItem>
          <CNavLink href="#" @click="navigateToSettings">Settings</CNavLink>
        </CNavItem>
      </CHeaderNav>
      <CHeaderNav class="ms-auto app-header-shell__actions">
        <CNavItem>
          <CNavLink
            href="#"
            @click="onShowAlerts"
            :class="['app-header-shell__alert-link', { 'app-header-shell__alert-link--animated': bellAnimating }]"
          >
            <CIcon icon="cil-bell" size="lg" />
            <span v-if="alertsBadge" class="app-header-shell__alert-badge">{{ alertsBadge }}</span>
          </CNavLink>
        </CNavItem>
        <CNavItem>
          <CNavLink href="#" @click="onShowLeaderboard">
            <CIcon icon="cil-list" size="lg" />
          </CNavLink>
        </CNavItem>
        <CNavItem>
          <CButton color="danger" size="sm" class="align-self-center ms-2 app-header-shell__logout" @click="logout">Logout</CButton>
        </CNavItem>
      </CHeaderNav>
      <CHeaderNav class="app-header-shell__utility">
        <div class="nav-item py-1">
          <div class="vr h-100 mx-2 text-body text-opacity-75"></div>
        </div>
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
        <div class="nav-item py-1">
          <div class="vr h-100 mx-2 text-body text-opacity-75"></div>
        </div>
        <AppHeaderDropdownAccnt @logout="logout" />
      </CHeaderNav>
    </CContainer>
    <CContainer class="app-header-shell__crumbs px-4" fluid>
      <AppBreadcrumb />
    </CContainer>
  </CHeader>
  <Leaderboard :visible="showLeaderboard" @close="showLeaderboard = false" myBuilding="Building B" />
  <Alerts :visible="showAlerts" @close="showAlerts = false" />
</template>

<style scoped>
.app-header-shell {
  backdrop-filter: blur(18px);
}

.app-header-shell__bar {
  min-height: 72px;
  border-color: rgba(172, 199, 255, 0.28) !important;
  background:
    linear-gradient(180deg, rgba(249, 251, 255, 0.96), rgba(241, 247, 255, 0.92));
  box-shadow:
    0 12px 30px rgba(103, 129, 167, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.app-header-shell__crumbs {
  padding-top: 0.35rem;
  background: transparent;
}

.app-header-shell :deep(.breadcrumb) {
  margin-bottom: 0;
  padding: 0.65rem 0.25rem 0;
}

.app-header-shell__toggler {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  color: #22324d;
  background: rgba(39, 122, 226, 0.08);
}

.app-header-shell__nav :deep(.nav-link),
.app-header-shell__actions :deep(.nav-link),
.app-header-shell__utility :deep(.dropdown-toggle) {
  border-radius: 14px;
  padding: 0.55rem 0.8rem;
  color: #334155;
  font-weight: 600;
  transition: background-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.app-header-shell__nav :deep(.nav-link:hover),
.app-header-shell__actions :deep(.nav-link:hover),
.app-header-shell__utility :deep(.dropdown-toggle:hover) {
  background: rgba(39, 122, 226, 0.08);
  color: #1f4d8f;
  box-shadow: 0 8px 20px rgba(104, 130, 170, 0.08);
}

.app-header-shell__alert-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transform-origin: top center;
}

.app-header-shell__alert-link--animated {
  animation: app-header-bell-ring 0.72s ease;
}

.app-header-shell__alert-badge {
  position: absolute;
  right: 0.24rem;
  bottom: 0.1rem;
  min-width: auto;
  height: auto;
  padding: 0;
  border: 0;
  background: transparent;
  color: #334155;
  display: block;
  font-size: 0.86rem;
  font-weight: 800;
  line-height: 1;
  text-align: center;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.85);
}

.app-header-shell__logout {
  border-radius: 14px;
  padding-inline: 0.95rem;
  font-weight: 700;
  box-shadow: 0 10px 22px rgba(220, 53, 69, 0.16);
}

.app-header-shell :deep(.dropdown-menu) {
  border: 1px solid rgba(172, 199, 255, 0.3);
  border-radius: 18px;
  box-shadow: 0 20px 40px rgba(103, 129, 167, 0.14);
  padding: 0.45rem;
}

.app-header-shell :deep(.dropdown-item) {
  border-radius: 12px;
}

.app-header-shell :deep(.dropdown-item:hover) {
  background: rgba(39, 122, 226, 0.08);
}

.app-header-shell--dark .app-header-shell__bar {
  border-color: rgba(71, 85, 105, 0.48) !important;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.94));
  box-shadow:
    0 14px 34px rgba(2, 6, 23, 0.32),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.app-header-shell--dark .app-header-shell__crumbs {
  background:
    linear-gradient(180deg, rgba(23, 32, 48, 0.94), rgba(17, 24, 39, 0.9));
  border-bottom: 1px solid rgba(71, 85, 105, 0.32);
}

.app-header-shell--dark .app-header-shell__toggler {
  color: #dbe7fb;
  background: rgba(59, 130, 246, 0.16);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.app-header-shell--dark .app-header-shell__nav .nav-link,
.app-header-shell--dark .app-header-shell__actions .nav-link,
.app-header-shell--dark .app-header-shell__utility .dropdown-toggle {
  color: #d8e2f1;
}

.app-header-shell--dark .app-header-shell__nav .nav-link:hover,
.app-header-shell--dark .app-header-shell__actions .nav-link:hover,
.app-header-shell--dark .app-header-shell__utility .dropdown-toggle:hover {
  background: rgba(59, 130, 246, 0.14);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(2, 6, 23, 0.22);
}

.app-header-shell--dark .app-header-shell__alert-badge {
  color: #e2e8f0;
  text-shadow: 0 1px 0 rgba(15, 23, 42, 0.55);
}

.app-header-shell--dark .app-header-shell__logout {
  box-shadow: 0 12px 24px rgba(127, 29, 29, 0.24);
}

.app-header-shell--dark .breadcrumb,
.app-header-shell--dark .breadcrumb-item,
.app-header-shell--dark .breadcrumb-item a {
  color: #a8b4c7;
}

.app-header-shell--dark .breadcrumb-item.active {
  color: #f8fafc;
}

.app-header-shell--dark .dropdown-menu {
  border-color: rgba(71, 85, 105, 0.42);
  background: rgba(15, 23, 42, 0.98);
  box-shadow: 0 20px 40px rgba(2, 6, 23, 0.38);
}

.app-header-shell--dark .dropdown-item {
  color: #d8e2f1;
}

.app-header-shell--dark .dropdown-item:hover,
.app-header-shell--dark .dropdown-item.active {
  background: rgba(59, 130, 246, 0.14);
  color: #ffffff;
}

@keyframes app-header-bell-ring {
  0% { transform: rotate(0deg) scale(1); }
  18% { transform: rotate(12deg) scale(1.04); }
  36% { transform: rotate(-10deg) scale(1.04); }
  54% { transform: rotate(8deg) scale(1.02); }
  72% { transform: rotate(-4deg) scale(1.01); }
  100% { transform: rotate(0deg) scale(1); }
}

@media (max-width: 991px) {
  .app-header-shell__bar {
    min-height: 64px;
  }
}
</style>
