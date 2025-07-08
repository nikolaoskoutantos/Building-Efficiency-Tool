import { defineStore } from 'pinia'
import { ref } from 'vue'
import { buildApiUrl } from '@/config/api.js'
import { useAuthStore } from '@/stores/auth.js'

export const useServicesStore = defineStore('services', () => {
  // State
  const services = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Get auth store for potential authenticated operations
  const authStore = useAuthStore()

  // Helper function to get auth headers (for future authenticated operations)
  function getAuthHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    }
    
    if (authStore.jwtToken) {
      headers.Authorization = `Bearer ${authStore.jwtToken}`
    }
    
    return headers
  }

  // Fetch all services from API (public endpoint)
  async function fetchServices() {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl('/services'), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      
      // Add UI-specific properties to each service
      services.value = result.map(service => ({
        ...service,
        checked: false // For UI selection state
      }))
      
      console.log('✅ Fetched services from API:', services.value)
      return services.value
    } catch (err) {
      error.value = err.message
      console.error('❌ Failed to fetch services:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Get a specific service by ID
  async function fetchServiceById(id) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl(`/services/${id}`), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const service = await response.json()
      console.log(`✅ Fetched service ${id}:`, service)
      return service
    } catch (err) {
      error.value = err.message
      console.error(`❌ Failed to fetch service ${id}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Create a new service (authenticated)
  async function createService(serviceData) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl('/services'), {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(serviceData)
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const newService = await response.json()
      
      // Add to local state
      services.value.push({
        ...newService,
        checked: false
      })
      
      console.log('✅ Created new service:', newService)
      return newService
    } catch (err) {
      error.value = err.message
      console.error('❌ Failed to create service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Update a service (authenticated)
  async function updateService(id, serviceData) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl(`/services/${id}`), {
        method: 'PUT',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(serviceData)
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const updatedService = await response.json()
      
      // Update in local state
      const index = services.value.findIndex(s => s.id === id)
      if (index !== -1) {
        services.value[index] = {
          ...updatedService,
          checked: services.value[index].checked // Preserve UI state
        }
      }
      
      console.log('✅ Updated service:', updatedService)
      return updatedService
    } catch (err) {
      error.value = err.message
      console.error('❌ Failed to update service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Delete a service (authenticated)
  async function deleteService(id) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl(`/services/${id}`), {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include'
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      // Remove from local state
      services.value = services.value.filter(s => s.id !== id)
      
      console.log(`✅ Deleted service ${id}`)
      return true
    } catch (err) {
      error.value = err.message
      console.error(`❌ Failed to delete service ${id}:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // UI helper methods
  function toggleChecked(id) {
    const service = services.value.find(s => s.id === id)
    if (service) {
      service.checked = !service.checked
    }
  }

  function getCheckedServices() {
    return services.value.filter(s => s.checked)
  }

  function clearChecked() {
    services.value.forEach(s => s.checked = false)
  }

  function getServiceById(id) {
    return services.value.find(s => s.id === id)
  }

  // Clear error
  function clearError() {
    error.value = null
  }

  return {
    // State
    services,
    loading,
    error,
    
    // API Actions
    fetchServices,
    fetchServiceById,
    createService,
    updateService,
    deleteService,
    
    // UI Actions
    toggleChecked,
    getCheckedServices,
    clearChecked,
    getServiceById,
    clearError
  }
})