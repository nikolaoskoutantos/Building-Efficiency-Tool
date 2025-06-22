import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useAlertsStore = defineStore('alerts', () => {
  // Mock alert data
  const alerts = ref([
    {
      timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      description: 'Temperature sensor reported a sudden drop in indoor temperature.'
    },
    {
      timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      description: 'Forecast service unavailable, using cached data.'
    },
    {
      timestamp: new Date().toISOString(),
      description: 'Energy efficiency improved by 10% after user action.'
    }
  ])

  function setAlerts(newAlerts) {
    alerts.value = newAlerts
  }

  function addAlert(alert) {
    alerts.value.push(alert)
  }

  return { alerts, setAlerts, addAlert }
})
