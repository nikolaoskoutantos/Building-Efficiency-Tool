import { ref } from 'vue'
import { defineStore } from 'pinia'
import { buildApiUrl } from '@/config/api.js'
import { useAuthStore } from '@/stores/auth.js'

export const useRatesStore = defineStore('rates', () => {
  // State
  const rates = ref([])
  const myRatings = ref([])
  const serviceScores = ref({})
  const loading = ref(false)
  const error = ref(null)

  // Get auth store for JWT token
  const authStore = useAuthStore()

  // Helper function to get auth headers
  function getAuthHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    }
    
    if (authStore.jwtToken) {
      headers.Authorization = `Bearer ${authStore.jwtToken}`
    }
    
    return headers
  }

  // Submit or update a rating (authenticated endpoint)
  async function submitRating(serviceId, rating, feedback = null) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl('/rates/submit'), {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify({
          service_id: serviceId,
          rating: rating,
          feedback: feedback
        })
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      
      if (result.success) {
        console.log('✅ Rating submitted successfully:', result)
        // Refresh user's ratings after successful submission
        await fetchMyRatings()
        // Refresh service score
        await fetchServiceScore(serviceId)
        return result
      } else {
        throw new Error(result.message || 'Failed to submit rating')
      }
    } catch (err) {
      error.value = err.message
      console.error('❌ Failed to submit rating:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Get user's own ratings (authenticated endpoint)
  async function fetchMyRatings() {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl('/rates/my-ratings'), {
        method: 'GET',
        headers: getAuthHeaders(),
        credentials: 'include'
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in.')
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      myRatings.value = result
      console.log('✅ Fetched my ratings:', result)
      return result
    } catch (err) {
      error.value = err.message
      console.error('❌ Failed to fetch my ratings:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Get service score/ratings (public endpoint)
  async function fetchServiceScore(serviceId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await fetch(buildApiUrl(`/rates/service/${serviceId}/score`), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      serviceScores.value[serviceId] = result
      console.log(`✅ Fetched service ${serviceId} score:`, result)
      return result
    } catch (err) {
      error.value = err.message
      console.error(`❌ Failed to fetch service ${serviceId} score:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // Get multiple service scores
  async function fetchMultipleServiceScores(serviceIds) {
    const promises = serviceIds.map(id => fetchServiceScore(id))
    return Promise.allSettled(promises)
  }

  // Check if user has rated a specific service
  function hasRatedService(serviceId) {
    return myRatings.value.some(rating => rating.service_id === serviceId)
  }

  // Get user's rating for a specific service
  function getUserRatingForService(serviceId) {
    return myRatings.value.find(rating => rating.service_id === serviceId)
  }

  // Clear error
  function clearError() {
    error.value = null
  }

  // Legacy methods for compatibility
  function setRates(newRates) {
    rates.value = newRates
  }

  function addRate(rate) {
    rates.value.push(rate)
  }

  return { 
    // State
    rates, 
    myRatings,
    serviceScores,
    loading,
    error,
    
    // Actions
    submitRating,
    fetchMyRatings,
    fetchServiceScore,
    fetchMultipleServiceScores,
    hasRatedService,
    getUserRatingForService,
    clearError,
    
    // Legacy
    setRates, 
    addRate 
  }
})
