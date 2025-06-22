import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useControlStore = defineStore('control', () => {
  // Example preferences state
  const preferences = ref({
    switchValue: false,
    slider1: 50,
    slider2: 50,
    comment: ''
  })

  function setPreferences(newPrefs) {
    preferences.value = { ...preferences.value, ...newPrefs }
  }

  function resetPreferences() {
    preferences.value = {
      switchValue: false,
      slider1: 50,
      slider2: 50,
      comment: ''
    }
  }

  return { preferences, setPreferences, resetPreferences }
})
