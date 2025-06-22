<template>
  <COffcanvas :visible="visible" placement="end" @hide="emit('close')">
    <COffcanvasHeader>
      <COffcanvasTitle>Alerts</COffcanvasTitle>
      <CButton class="btn-close" @click="emit('close')" aria-label="Close"></CButton>
    </COffcanvasHeader>
    <COffcanvasBody>
      <CListGroup>
        <CListGroupItem v-for="(alert, idx) in alertsStore.alerts" :key="idx">
          <div class="fw-bold">{{ new Date(alert.timestamp).toLocaleString() }}</div>
          <div>{{ alert.description }}</div>
        </CListGroupItem>
      </CListGroup>
    </COffcanvasBody>
  </COffcanvas>
</template>

<script setup>
import { useAlertsStore } from '@/stores/alerts.js'
import { COffcanvas, COffcanvasHeader, COffcanvasTitle, COffcanvasBody, CListGroup, CListGroupItem, CButton } from '@coreui/vue'

const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close'])
const alertsStore = useAlertsStore()
</script>
