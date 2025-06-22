import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useRatesStore = defineStore('rates', () => {
  // Example state
  const rates = ref([])

  // Example actions
  function setRates(newRates) {
    rates.value = newRates
  }

  function addRate(rate) {
    rates.value.push(rate)
  }

  return { rates, setRates, addRate }
})
