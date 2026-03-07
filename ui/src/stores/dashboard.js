import { defineStore } from 'pinia'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    // Loading states
    loading: false,
    lastLoaded: null,
    error: null,
    
    // Core data
    devices: [],
    buildings: [],
    mqttConfig: {
      broker_url: '',
      broker_port: 1883,
      broker_username: null,
      broker_password: null
    },
    userSettings: {
      default_building_id: null,
      theme: 'light',
      notifications_enabled: true,
      auto_refresh_devices: true
    },
    stats: {
      total_devices: 0,
      total_sensors: 0,
      total_buildings: 0,
      devices_with_sensors: 0,
      average_sensors_per_device: 0
    }
  }),

  getters: {
    // Get devices with sensors
    devicesWithSensors: (state) => {
      return state.devices.filter(device => device.sensor_count > 0)
    },
    
    // Get device by ID
    getDeviceById: (state) => {
      return (deviceId) => state.devices.find(device => device.id === deviceId)
    },
    
    // Get building by ID
    getBuildingById: (state) => {
      return (buildingId) => state.buildings.find(building => building.id === buildingId)
    },
    
    // Get default building
    defaultBuilding: (state) => {
      if (state.userSettings.default_building_id) {
        return state.buildings.find(building => building.id === state.userSettings.default_building_id)
      }
      return state.buildings.length > 0 ? state.buildings[0] : null
    },
    
    // Check if data is fresh (loaded within last 5 minutes)
    isDataFresh: (state) => {
      if (!state.lastLoaded) return false
      const fiveMinutesAgo = Date.now() - (5 * 60 * 1000)
      return new Date(state.lastLoaded).getTime() > fiveMinutesAgo
    },
    
    // MQTT connection info for components
    mqttConnectionInfo: (state) => {
      return {
        url: state.mqttConfig.broker_url,
        port: state.mqttConfig.broker_port,
        username: state.mqttConfig.broker_username,
        password: state.mqttConfig.broker_password,
        hasCredentials: !!(state.mqttConfig.broker_username && state.mqttConfig.broker_password)
      }
    }
  },

  actions: {
    // Load dashboard data from API
    async loadDashboardData(force = false) {
      // Don't reload if data is fresh unless forced
      if (!force && this.isDataFresh) {
        console.log('Dashboard data is fresh, skipping reload')
        return
      }

      this.loading = true
      this.error = null
      
      try {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
        const response = await fetch(`${apiBaseUrl}/dashboard`)
        
        if (!response.ok) {
          throw new Error(`Failed to fetch dashboard data: ${response.status}`)
        }
        
        const data = await response.json()
        
        // Update all dashboard data
        this.devices = data.devices || []
        this.buildings = data.buildings || []
        this.mqttConfig = {
          ...this.mqttConfig,
          ...data.mqtt_config
        }
        this.userSettings = {
          ...this.userSettings,
          ...data.user_settings
        }
        this.stats = data.stats || this.stats
        this.lastLoaded = new Date().toISOString()
        
        console.log('Dashboard data loaded successfully:', {
          devices: this.devices.length,
          buildings: this.buildings.length,
          stats: this.stats
        })
        
      } catch (error) {
        console.error('Failed to load dashboard data:', error)
        this.error = error.message
        // Don't clear existing data on error, just log it
      } finally {
        this.loading = false
      }
    },

    // Refresh dashboard data 
    async refreshDashboardData() {
      return this.loadDashboardData(true)
    },

    // Add a new device to the store (after registration)
    addDevice(device) {
      this.devices.push(device)
      this.updateStats()
    },

    // Update a device in the store
    updateDevice(deviceId, updates) {
      const index = this.devices.findIndex(device => device.id === deviceId)
      if (index !== -1) {
        this.devices[index] = { ...this.devices[index], ...updates }
        this.updateStats()
      }
    },

    // Remove a device from the store
    removeDevice(deviceId) {
      const index = this.devices.findIndex(device => device.id === deviceId)
      if (index !== -1) {
        this.devices.splice(index, 1)
        this.updateStats()
      }
    },

    // Update user settings
    updateUserSettings(settings) {
      this.userSettings = { ...this.userSettings, ...settings }
    },

    // Update MQTT config 
    updateMqttConfig(config) {
      this.mqttConfig = { ...this.mqttConfig, ...config }
    },

    // Recalculate statistics
    updateStats() {
      const totalDevices = this.devices.length
      const totalSensors = this.devices.reduce((sum, device) => sum + (device.sensor_count || 0), 0)
      const devicesWithSensors = this.devices.filter(device => device.sensor_count > 0).length
      
      this.stats = {
        total_devices: totalDevices,
        total_sensors: totalSensors,
        total_buildings: this.buildings.length,
        devices_with_sensors: devicesWithSensors,
        average_sensors_per_device: totalDevices > 0 ? Math.round((totalSensors / totalDevices) * 10) / 10 : 0
      }
    },

    // Clear all data (for logout)
    clearDashboardData() {
      this.devices = []
      this.buildings = []
      this.mqttConfig = {
        broker_url: '',
        broker_port: 1883,
        broker_username: null,
        broker_password: null
      }
      this.userSettings = {
        default_building_id: null,
        theme: 'light',
        notifications_enabled: true,
        auto_refresh_devices: true
      }
      this.stats = {
        total_devices: 0,
        total_sensors: 0,
        total_buildings: 0,
        devices_with_sensors: 0,
        average_sensors_per_device: 0
      }
      this.lastLoaded = null
      this.error = null
    },

    // Get fresh statistics (can be used for real-time updates)
    async loadStats() {
      try {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
        const response = await fetch(`${apiBaseUrl}/dashboard/stats`)
        
        if (response.ok) {
          const stats = await response.json()
          this.stats = stats
          return stats
        }
      } catch (error) {
        console.warn('Failed to load fresh stats:', error)
      }
      return this.stats
    }
  }
})