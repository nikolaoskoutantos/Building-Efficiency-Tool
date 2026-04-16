<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { normalizeRole } from '@/utils/apiErrors'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentRole = computed(() => normalizeRole(auth.userProfile?.role) || 'UNKNOWN')
const requiredRoles = computed(() => route.query.required || 'a higher-privilege role')
const targetPath = computed(() => route.query.from || '/efficiencytool')

function goBackToDashboard() {
  router.push('/efficiencytool')
}
</script>

<template>
  <CRow class="justify-content-center mt-4">
    <CCol :md="8" :lg="6">
      <CCard class="border-warning">
        <CCardHeader class="bg-warning-subtle">
          <h5 class="mb-0">Access Restricted</h5>
        </CCardHeader>
        <CCardBody>
          <p class="mb-3">
            Your current role does not have permission to open this page.
          </p>
          <p class="text-body-secondary mb-2">
            Current role: <strong>{{ currentRole }}</strong>
          </p>
          <p class="text-body-secondary mb-2">
            Required role(s): <strong>{{ requiredRoles }}</strong>
          </p>
          <p class="text-body-secondary mb-4">
            Requested page: <code>{{ targetPath }}</code>
          </p>
          <CButton color="primary" @click="goBackToDashboard">
            Return to Dashboard
          </CButton>
        </CCardBody>
      </CCard>
    </CCol>
  </CRow>
</template>
