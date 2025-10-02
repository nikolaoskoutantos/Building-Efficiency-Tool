<template>
  <div>
    <CButton color="primary" @click="show = true">Rate</CButton>
    <CModal :visible="show" @close="show = false">
      <template #header>
        <h5 class="modal-title">Rate Forecast Services</h5>
      </template>
      <CCard class="mb-3 mx-auto" style="width: 90%; margin-top: 2rem;">
        <CCardBody>
          <h5 class="mb-4 text-center">Rate the Weather Forecasts</h5>
          <div v-for="service in services" :key="service.name" class="d-flex align-items-center mb-3">
            <div class="flex-grow-1 fw-bold">{{ service.name === 'Weather Data Service' ? 'Service 1' : service.name === 'Environmental Data' ? 'Service 2' : service.name }}</div>
            <div>
              <span v-for="n in max" :key="n" @click="setServiceRating(service, n)" style="cursor:pointer; font-size:2rem; color: gold;">
                <span v-if="n <= service.rating">&#9733;</span>
                <span v-else>&#9734;</span>
              </span>
            </div>
          </div>
        </CCardBody>
      </CCard>
      <!--
      -->
      
      <!-- Error Message -->
      <div v-if="submitError" class="alert alert-danger mx-auto" style="width: 90%;">
        {{ submitError }}
      </div>
      
      <!-- Authentication Warning -->
      <div v-if="!authStore.isAuthenticated" class="alert alert-warning mx-auto" style="width: 90%;">
        Please connect your wallet to submit ratings
      </div>
      
      <div class="d-flex justify-content-center mb-3">
        <CButton 
          color="primary" 
          @click="submitRating" 
          :disabled="submitting || !authStore.isAuthenticated"
        >
          <span v-if="submitting">
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            Submitting...
          </span>
          <span v-else>Submit</span>
        </CButton>
        <CButton color="secondary" class="ms-2" @click="show = false">Close</CButton>
      </div>
    </CModal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRatesStore } from '@/stores/rates.js'
import { useServicesStore } from '@/stores/services.js'
import { useAuthStore } from '@/stores/auth.js'
import { CButton, CModal, CCard, CCardBody } from '@coreui/vue'

const show = ref(false)
const max = 5
// Services will be loaded from database
const services = ref([])
const slider2 = ref(50)
const comment = ref("")
const submitting = ref(false)
const submitError = ref(null)

const ratesStore = useRatesStore()
const servicesStore = useServicesStore()
const authStore = useAuthStore()

// Initialize services from the services store when component mounts
onMounted(async () => {
  try {
    // Fetch services from database if not already loaded
    if (servicesStore.services.length === 0) {
      await servicesStore.fetchServices()
    }
    
    // Use actual services from database
    services.value = servicesStore.services.map(service => ({
      id: service.id,
      name: service.name,
      rating: 0
    }))
    
    console.log('✅ Rating component loaded services:', services.value)
  } catch (error) {
    console.error('❌ Failed to load services for rating:', error)
    submitError.value = "Failed to load services. Please refresh the page."
  }
})

function setServiceRating(service, val) {
  service.rating = val
}

async function submitRating() {
  if (!authStore.isAuthenticated) {
    submitError.value = "Please connect your wallet first"
    return
  }

  submitting.value = true
  submitError.value = null
  
  try {
    // Submit separate ratings for each service that has been rated
    const ratingPromises = services.value
      .filter(service => service.rating > 0)
      .map(service => {
        // Include temperature comfort and comments in feedback
        const fullFeedback = [
          comment.value,
          `Temperature comfort: ${slider2.value}%`
        ].filter(Boolean).join(' | ')
        
        return ratesStore.submitRating(
          service.id, 
          service.rating, 
          fullFeedback || null
        )
      })
    
    if (ratingPromises.length === 0) {
      submitError.value = "Please rate at least one weather service"
      return
    }

    // Wait for all ratings to be submitted
    const results = await Promise.allSettled(ratingPromises)
    
    // Check if any submissions failed
    const failed = results.filter(result => result.status === 'rejected')
    const succeeded = results.filter(result => result.status === 'fulfilled')
    
    if (succeeded.length > 0) {
      console.log(`✅ Successfully submitted ${succeeded.length} rating(s)`)
      
      // Reset form after successful submission
      services.value.forEach(service => service.rating = 0)
      slider2.value = 50
      comment.value = ""
      show.value = false
      
      // Show success message
      if (failed.length === 0) {
        console.log("🎉 All weather service ratings submitted successfully!")
      } else {
        console.warn(`⚠️ ${succeeded.length} ratings succeeded, ${failed.length} failed`)
      }
    }
    
    if (failed.length > 0) {
      const errorMessages = failed.map(result => result.reason?.message || 'Unknown error')
      submitError.value = `Some ratings failed: ${errorMessages.join(', ')}`
    }
    
  } catch (error) {
    console.error('❌ Error submitting weather service ratings:', error)
    submitError.value = error.message || 'Failed to submit ratings'
  } finally {
    submitting.value = false
  }
}</script>

<style scoped>
/* Responsive modal and card styles */
:deep(.modal-dialog) {
  max-width: 500px !important;
  width: 100vw !important;
  margin: 0 auto;
}
:deep(.modal-content) {
  width: 100% !important;
  min-width: 0;
  box-sizing: border-box;
}

/* Alert styles */
.alert {
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border: 1px solid transparent;
  border-radius: 0.375rem;
}
.alert-danger {
  color: #721c24;
  background-color: #f8d7da;
  border-color: #f5c2c7;
}
.alert-warning {
  color: #664d03;
  background-color: #fff3cd;
  border-color: #ffecb5;
}

/* Spinner styles */
.spinner-border {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  vertical-align: -0.125em;
  border: 0.125em solid currentcolor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spinner-border 0.75s linear infinite;
}
.spinner-border-sm {
  width: 0.875rem;
  height: 0.875rem;
  border-width: 0.125em;
}

@keyframes spinner-border {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 600px) {
  :deep(.modal-dialog) {
    max-width: 90vw !important;
    width: 90vw !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    margin: 0 !important;
    padding: 0 !important;
    position: fixed !important;
    top: 5vw !important;
    box-sizing: border-box;
  }
  :deep(.modal-content) {
    width: 90vw !important;
    border-radius: 8px !important;
    min-width: 0;
    box-sizing: border-box;
    padding: 0.5rem !important;
  }
  .mb-3.mx-auto {
    width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  .form-control, .form-range {
    font-size: 1em;
  }
  .modal-title {
    font-size: 1.1em;
  }
  .d-flex.justify-content-center.mb-3 {
    margin-bottom: 1rem !important;
  }
}
</style>
