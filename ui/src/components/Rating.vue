<template>
  <div>
    <CButton color="primary" @click="show = true">
      {{ isOccupant ? 'Rate Comfort' : 'Rate Services' }}
    </CButton>

    <CModal :visible="show" @close="show = false">
      <template #header>
        <h5 class="modal-title">
          {{ isOccupant ? 'Thermal Comfort Rating' : 'Service Quality Rating' }}
        </h5>
      </template>

      <CCard class="mb-3 mx-auto" style="width: 90%; margin-top: 1.5rem;">
        <CCardBody>

          <!-- ── OCCUPANT: thermal comfort slider 1-10 ── -->
          <template v-if="isOccupant">
            <h5 class="mb-1 text-center">How comfortable is the temperature?</h5>
            <p class="text-center text-muted mb-4" style="font-size:0.85rem;">
              1 = too cold &nbsp;·&nbsp; 5-6 = comfortable &nbsp;·&nbsp; 10 = too hot
            </p>

            <div v-for="service in services" :key="service.id" class="mb-4">
              <div class="fw-bold mb-2">{{ service.name }}</div>
              <div class="d-flex align-items-center gap-2">
                <span class="comfort-label cold">❄️ Cold</span>
                <div class="slider-wrapper flex-grow-1">
                  <input
                    type="range"
                    class="comfort-slider"
                    min="1" max="10" step="1"
                    v-model.number="service.rating"
                    :style="sliderStyle(service.rating)"
                  />
                  <div class="tick-labels">
                    <span v-for="n in 10" :key="n">{{ n }}</span>
                  </div>
                </div>
                <span class="comfort-label hot">🔥 Hot</span>
              </div>
              <div class="text-center mt-1">
                <span class="comfort-badge" :style="badgeStyle(service.rating)">
                  {{ comfortLabel(service.rating) }}
                </span>
              </div>
            </div>
          </template>

          <!-- ── MANAGER / ADMIN: star rating 1-5 ── -->
          <template v-else>
            <h5 class="mb-4 text-center">Rate the Weather &amp; Forecast Services</h5>

            <div v-for="service in services" :key="service.id" class="d-flex align-items-center mb-3">
              <div class="flex-grow-1 fw-bold">{{ service.name }}</div>
              <div>
                <span
                  v-for="n in 5" :key="n"
                  @click="service.rating = n"
                  style="cursor:pointer; font-size:2rem; color: gold;"
                >
                  <span v-if="n <= service.rating">&#9733;</span>
                  <span v-else>&#9734;</span>
                </span>
              </div>
            </div>
          </template>

        </CCardBody>
      </CCard>

      <div v-if="submitError" class="alert alert-danger mx-auto" style="width: 90%;">
        {{ submitError }}
      </div>
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
import { ref, computed, onMounted } from 'vue'
import { useRatesStore } from '@/stores/rates.js'
import { useServicesStore } from '@/stores/services.js'
import { useAuthStore } from '@/stores/auth.js'
import { CButton, CModal, CCard, CCardBody } from '@coreui/vue'

const show = ref(false)
const services = ref([])
const submitting = ref(false)
const submitError = ref(null)

const ratesStore = useRatesStore()
const servicesStore = useServicesStore()
const authStore = useAuthStore()

// Role detection
const isOccupant = computed(() => authStore.userProfile?.role === 'OCCUPANT')
const ratingType = computed(() => isOccupant.value ? 'thermal_comfort' : 'service_quality')
const defaultRating = computed(() => isOccupant.value ? 5 : 0)

onMounted(async () => {
  try {
    if (servicesStore.services.length === 0) {
      await servicesStore.fetchServices()
    }
    services.value = servicesStore.services.map(service => ({
      id: service.id,
      name: service.name,
      rating: defaultRating.value,
    }))
  } catch (error) {
    console.error('❌ Failed to load services for rating:', error)
    submitError.value = 'Failed to load services. Please refresh the page.'
  }
})

// ── Thermal comfort helpers ──────────────────────────────────────
function comfortLabel(val) {
  if (val <= 2) return `${val} — Very Cold`
  if (val <= 4) return `${val} — Cool`
  if (val <= 6) return `${val} — Comfortable`
  if (val <= 8) return `${val} — Warm`
  return `${val} — Very Hot`
}

function sliderColor(val) {
  const pct = (val - 1) / 9
  const r = Math.round(pct < 0.5 ? 0 : (pct - 0.5) * 2 * 220)
  const g = Math.round(pct < 0.5 ? pct * 2 * 180 : (1 - (pct - 0.5) * 2) * 180)
  const b = Math.round(pct < 0.5 ? (1 - pct * 2) * 220 : 0)
  return `rgb(${r},${g},${b})`
}

function sliderStyle(val) {
  return {
    '--thumb-color': sliderColor(val),
    background: 'linear-gradient(to right, #3a86ff 0%, #06d6a0 50%, #ef233c 100%)',
  }
}

function badgeStyle(val) {
  return {
    backgroundColor: sliderColor(val),
    color: '#fff',
    padding: '2px 12px',
    borderRadius: '12px',
    fontSize: '0.85rem',
  }
}

// ── Submit ───────────────────────────────────────────────────────
async function submitRating() {
  if (!authStore.isAuthenticated) {
    submitError.value = 'Please connect your wallet first'
    return
  }

  // Manager must have rated at least one service
  if (!isOccupant.value && services.value.every(s => s.rating === 0)) {
    submitError.value = 'Please rate at least one service'
    return
  }

  submitting.value = true
  submitError.value = null

  try {
    const toSubmit = isOccupant.value
      ? services.value                             // occupant always submits all
      : services.value.filter(s => s.rating > 0)  // manager only submits rated ones

    const results = await Promise.allSettled(
      toSubmit.map(s => ratesStore.submitRating(s.id, s.rating, null, ratingType.value))
    )

    const failed = results.filter(r => r.status === 'rejected')
    const succeeded = results.filter(r => r.status === 'fulfilled')

    if (succeeded.length > 0) {
      services.value.forEach(s => s.rating = defaultRating.value)
      show.value = false
    }
    if (failed.length > 0) {
      submitError.value = `Some submissions failed: ${failed.map(r => r.reason?.message || 'Unknown').join(', ')}`
    }
  } catch (error) {
    submitError.value = error.message || 'Failed to submit'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
:deep(.modal-dialog) {
  max-width: 520px !important;
  margin: 0 auto;
}

.comfort-label {
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
  min-width: 56px;
}
.comfort-label.cold { color: #3a86ff; text-align: right; }
.comfort-label.hot  { color: #ef233c; text-align: left; }

.slider-wrapper {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.comfort-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
}
.comfort-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--thumb-color, #06d6a0);
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  cursor: pointer;
  transition: background 0.2s;
}
.comfort-slider::-moz-range-thumb {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--thumb-color, #06d6a0);
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  cursor: pointer;
}

.tick-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
  font-size: 0.7rem;
  color: #888;
}

.comfort-badge {
  display: inline-block;
  font-weight: 600;
}

/* Alert styles */
.alert {
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border: 1px solid transparent;
  border-radius: 0.375rem;
}
.alert-danger  { color: #721c24; background-color: #f8d7da; border-color: #f5c2c7; }
.alert-warning { color: #664d03; background-color: #fff3cd; border-color: #ffecb5; }

/* Spinner */
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
.spinner-border-sm { width: 0.875rem; height: 0.875rem; border-width: 0.125em; }
@keyframes spinner-border { to { transform: rotate(360deg); } }

@media (max-width: 600px) {
  :deep(.modal-dialog) { max-width: 95vw !important; }
  .comfort-label { min-width: 44px; font-size: 0.72rem; }
}
</style>
