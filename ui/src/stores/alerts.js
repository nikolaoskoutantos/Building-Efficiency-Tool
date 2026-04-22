import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useAlertsStore = defineStore('alerts', () => {
  const alerts = ref([])

  function setAlerts(newAlerts) {
    alerts.value = newAlerts
  }

  function addAlert(alert) {
    alerts.value.push(alert)
  }

  function removeAlert(index) {
    if (index < 0 || index >= alerts.value.length) return
    alerts.value.splice(index, 1)
  }

  function clearAlerts() {
    alerts.value = []
  }

  return { alerts, setAlerts, addAlert, removeAlert, clearAlerts }
})
