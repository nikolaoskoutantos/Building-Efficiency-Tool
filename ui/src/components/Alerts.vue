<template>
  <COffcanvas :visible="visible" :backdrop="false" placement="end" @hide="emit('close')" class="alerts-panel">
    <COffcanvasHeader class="alerts-panel__header">
      <div>
        <div class="alerts-panel__eyebrow">Monitoring</div>
        <COffcanvasTitle>Alerts</COffcanvasTitle>
      </div>
      <CButton class="btn-close" @click="emit('close')" aria-label="Close"></CButton>
    </COffcanvasHeader>
    <COffcanvasBody class="alerts-panel__body">
      <div class="alerts-summary">
        <div>
          <div class="alerts-summary__label">Active Feed</div>
          <div class="alerts-summary__value">{{ alertsStore.alerts.length }}</div>
        </div>
        <div class="alerts-summary__actions">
          <div class="alerts-summary__badge">Recent System Events</div>
          <CButton
            v-if="alertsStore.alerts.length"
            color="danger"
            variant="outline"
            size="sm"
            class="alerts-summary__clear"
            @click="alertsStore.clearAlerts()"
          >
            Clear All
          </CButton>
        </div>
      </div>

      <div v-if="alertsStore.alerts.length" class="alerts-list">
        <div v-for="(alert, idx) in alertsStore.alerts" :key="idx" class="alerts-row">
          <div class="alerts-row__top">
            <div class="alerts-row__meta">
              <span class="alerts-row__chip">Alert</span>
              <span class="alerts-row__timestamp">{{ new Date(alert.timestamp).toLocaleString() }}</span>
            </div>
            <CButton
              color="danger"
              variant="ghost"
              size="sm"
              class="alerts-row__remove"
              @click="alertsStore.removeAlert(idx)"
            >
              Remove
            </CButton>
          </div>
          <div class="alerts-row__description">{{ alert.description }}</div>
        </div>
      </div>

      <div v-else class="alerts-empty">
        <div class="alerts-empty__title">No alerts right now</div>
        <div class="alerts-empty__text">New system notifications will appear here as they arrive.</div>
      </div>
    </COffcanvasBody>
  </COffcanvas>
</template>

<script setup>
import { useAlertsStore } from '@/stores/alerts.js'
import { COffcanvas, COffcanvasHeader, COffcanvasTitle, COffcanvasBody, CButton } from '@coreui/vue'

defineProps({ visible: Boolean })
const emit = defineEmits(['close'])
const alertsStore = useAlertsStore()
</script>

<style scoped>
.alerts-panel :deep(.offcanvas) {
  border-left: 1px solid rgba(172, 199, 255, 0.35);
  background:
    linear-gradient(180deg, rgba(249, 251, 255, 0.98), rgba(240, 246, 255, 0.96));
  box-shadow: -18px 0 40px rgba(90, 117, 156, 0.12);
}

.alerts-panel__header {
  border-bottom: 1px solid rgba(172, 199, 255, 0.26);
  padding: 1.35rem 1.35rem 1rem;
}

.alerts-panel__eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6b87b3;
  margin-bottom: 0.2rem;
}

.alerts-panel__body {
  padding: 1.15rem 1.1rem 1.35rem;
}

.alerts-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.05rem;
  margin-bottom: 1rem;
  border: 1px solid rgba(172, 199, 255, 0.28);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(236, 245, 255, 0.96), rgba(255, 255, 255, 0.94));
  box-shadow: 0 14px 30px rgba(109, 129, 163, 0.08);
}

.alerts-summary__label {
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #51729c;
}

.alerts-summary__value {
  font-size: 1.9rem;
  font-weight: 800;
  color: #22324d;
  line-height: 1.05;
}

.alerts-summary__badge {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #31547e;
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
}

.alerts-summary__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.6rem;
  align-items: center;
}

.alerts-summary__clear {
  border-radius: 999px;
  font-weight: 700;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.alerts-row {
  padding: 0.95rem 1rem;
  border: 1px solid rgba(172, 199, 255, 0.24);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 10px 24px rgba(104, 130, 170, 0.07);
}

.alerts-row__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.8rem;
  margin-bottom: 0.4rem;
}

.alerts-row__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem 0.7rem;
}

.alerts-row__chip {
  display: inline-flex;
  align-items: center;
  padding: 0.22rem 0.55rem;
  border-radius: 999px;
  background: rgba(39, 122, 226, 0.12);
  color: #277ae2;
  font-size: 0.74rem;
  font-weight: 700;
}

.alerts-row__timestamp {
  font-size: 0.9rem;
  font-weight: 700;
  color: #22324d;
}

.alerts-row__remove {
  border-radius: 999px;
  font-weight: 700;
  padding-inline: 0.75rem;
  flex: 0 0 auto;
}

.alerts-row__description {
  font-size: 1rem;
  line-height: 1.55;
  color: #334155;
}

.alerts-empty {
  padding: 1.3rem 1.1rem;
  border: 1px dashed rgba(172, 199, 255, 0.45);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  text-align: center;
}

.alerts-empty__title {
  font-size: 1rem;
  font-weight: 700;
  color: #22324d;
  margin-bottom: 0.3rem;
}

.alerts-empty__text {
  color: #62748e;
  font-size: 0.94rem;
}

@media (max-width: 768px) {
  .alerts-summary {
    align-items: flex-start;
  }

  .alerts-summary__actions,
  .alerts-row__top {
    width: 100%;
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
