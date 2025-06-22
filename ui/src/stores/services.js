import { defineStore } from 'pinia'
// stores/services.js
export const useServicesStore = defineStore('services', {
  state: () => ({
    services: [
      {
        id: 1,
        name: 'Weather Data Feed',
        cost: 10,
        description: 'Provides real-time price data from multiple sources.',
        metadata: { endpoint: 'https://oracle.example/api', version: '1.0', owner: 'Chainlink' },
        checked: false // ✅ add this
      },
      {
        id: 2,
        name: 'Environmental Data Service',
        cost: 5,
        description: 'Generates secure random numbers for smart contracts.',
        metadata: { endpoint: 'https://random.example/api', version: '2.1', owner: 'Chainlink VRF' },
        checked: false
      },
      {
        id: 3,
        name: 'Material Cost Data',
        cost: 8,
        description: 'Delivers weather data for any location worldwide.',
        metadata: { endpoint: 'https://weather.example/api', version: '3.2', owner: 'WeatherCo' },
        checked: false
      }
    ]
  }),
  actions: {
    toggleChecked(id) {
      const service = this.services.find(s => s.id === id)
      if (service) service.checked = !service.checked
    }
  }
})

