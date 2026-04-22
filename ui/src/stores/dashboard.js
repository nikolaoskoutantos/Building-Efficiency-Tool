import { defineStore } from 'pinia'
import { buildApiUrl } from '@/config/api.js'
import { useAuthStore } from '@/stores/auth.js'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    // Loading states
    loading: false,
    lastLoaded: null,
    loadedForUserKey: null,
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
    efficiencyTimeGrid: {
      rows: [],
      currentRow: null,
      referenceTime: null,
      optimizationContext: null,
      latestOptimizationResult: null,
      loading: false,
      error: null,
      loadedBuildingId: null,
      lastLoaded: null
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
    getCurrentUserKey() {
      const authStore = useAuthStore()
      return (
        authStore.userProfile?.wallet ||
        authStore.userProfile?.user ||
        authStore.walletAddress ||
        authStore.getJwtToken?.() ||
        null
      )
    },

    getAuthHeaders() {
      const authStore = useAuthStore()
      const headers = {
        'Content-Type': 'application/json',
      }

      const jwtToken = authStore.getJwtToken ? authStore.getJwtToken() : authStore.jwtToken
      if (jwtToken) {
        headers.Authorization = `Bearer ${jwtToken}`
      }

      return headers
    },

    // Load dashboard data from API
    async loadDashboardData(force = false) {
      const currentUserKey = this.getCurrentUserKey()

      // Don't reload if data is fresh unless forced
      if (
        !force &&
        this.isDataFresh &&
        this.loadedForUserKey &&
        this.loadedForUserKey === currentUserKey
      ) {
        console.log('Dashboard data is fresh, skipping reload')
        return
      }

      if (this.loadedForUserKey && this.loadedForUserKey !== currentUserKey) {
        this.clearDashboardData()
      }

      this.loading = true
      this.error = null
      
      try {
        const response = await fetch(buildApiUrl('/dashboard/'), {
          method: 'GET',
          headers: this.getAuthHeaders(),
          credentials: 'include',
        })
        
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
        this.loadedForUserKey = currentUserKey
        
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

    setEfficiencyTimeGrid(payload, buildingId) {
      this.efficiencyTimeGrid = {
        ...this.efficiencyTimeGrid,
        rows: payload?.rows || [],
        currentRow: payload?.current_row || null,
        referenceTime: payload?.reference_time || null,
        optimizationContext: payload?.optimization_context || null,
        latestOptimizationResult: payload?.latest_optimization_result || null,
        error: null,
        loadedBuildingId: buildingId ?? null,
        lastLoaded: new Date().toISOString()
      }
    },

    clearEfficiencyTimeGrid() {
      this.efficiencyTimeGrid = {
        rows: [],
        currentRow: null,
        referenceTime: null,
        optimizationContext: null,
        latestOptimizationResult: null,
        loading: false,
        error: null,
        loadedBuildingId: null,
        lastLoaded: null
      }
    },

    async loadEfficiencyTimeGrid(buildingId, { force = false } = {}) {
      if (!buildingId) {
        this.clearEfficiencyTimeGrid()
        return null
      }

      const hasCachedRows =
        this.efficiencyTimeGrid.loadedBuildingId === buildingId &&
        Array.isArray(this.efficiencyTimeGrid.rows) &&
        this.efficiencyTimeGrid.rows.length > 0

      if (!force && hasCachedRows) {
        return {
          rows: this.efficiencyTimeGrid.rows,
          current_row: this.efficiencyTimeGrid.currentRow,
          reference_time: this.efficiencyTimeGrid.referenceTime,
          optimization_context: this.efficiencyTimeGrid.optimizationContext,
          latest_optimization_result: this.efficiencyTimeGrid.latestOptimizationResult
        }
      }

      this.efficiencyTimeGrid = {
        ...this.efficiencyTimeGrid,
        loading: true,
        error: null
      }

      try {
        const response = await fetch(buildApiUrl(`/dashboard/time-grid/${buildingId}`), {
          method: 'GET',
          headers: this.getAuthHeaders(),
          credentials: 'include',
        })

        if (!response.ok) {
          throw new Error(`Failed to load dashboard time grid: ${response.status}`)
        }

        const payload = await response.json()
        this.setEfficiencyTimeGrid(payload, buildingId)
        return payload
      } catch (error) {
        this.efficiencyTimeGrid = {
          ...this.efficiencyTimeGrid,
          error: error.message,
        }
        throw error
      } finally {
        this.efficiencyTimeGrid = {
          ...this.efficiencyTimeGrid,
          loading: false,
        }
      }
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
      this.clearEfficiencyTimeGrid()
      this.lastLoaded = null
      this.loadedForUserKey = null
      this.error = null
    },

    // Get fresh statistics (can be used for real-time updates)
    async loadStats() {
      try {
        const response = await fetch(buildApiUrl('/dashboard/stats'), {
          method: 'GET',
          headers: this.getAuthHeaders(),
          credentials: 'include',
        })
        
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
