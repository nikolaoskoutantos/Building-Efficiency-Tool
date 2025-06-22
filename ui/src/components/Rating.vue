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
            <div class="flex-grow-1 fw-bold">{{ service.name }}</div>
            <div>
              <span v-for="n in max" :key="n" @click="setServiceRating(service, n)" style="cursor:pointer; font-size:2rem; color: gold;">
                <span v-if="n <= service.rating">&#9733;</span>
                <span v-else>&#9734;</span>
              </span>
            </div>
          </div>
        </CCardBody>
      </CCard>
      <CCard class="mb-3 mx-auto" style="width: 90%;">
        <CCardBody>
          <h5 class="mb-4 text-center">Rate Indoor Temperature</h5>
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span style="font-size: 0.95em; color: #0d6efd; font-weight: 500;">I feel cold</span>
            <span style="font-size: 0.95em; color: #dc3545; font-weight: 500;">I feel hot</span>
          </div>
          <input type="range" min="0" max="100" v-model="slider2" class="form-range w-100" />
          <!-- Comment Text Box -->
          <div class="mt-3">
            <label for="rating-comment" class="form-label">Comments</label>
            <textarea id="rating-comment" v-model="comment" class="form-control" rows="2" placeholder="Add your comments here..."></textarea>
          </div>
        </CCardBody>
      </CCard>
      <div class="d-flex justify-content-center mb-3">
        <CButton color="primary" @click="submitRating">Submit</CButton>
        <CButton color="secondary" class="ms-2" @click="show = false">Close</CButton>
      </div>
    </CModal>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRatesStore } from '@/stores/rates.js'
import { CButton, CModal, CCard, CCardBody } from '@coreui/vue'

const show = ref(false)
const max = 5
const services = ref([
  { name: 'OpenMeteo', rating: 0 },
  { name: 'OpenWeather', rating: 0 },
])
const slider2 = ref(50)
const comment = ref("")

const ratesStore = useRatesStore()

function setServiceRating(service, val) {
  service.rating = val
}

function submitRating() {
  // Update the rates store with the current ratings, slider value, and comment
  ratesStore.setRates({
    services: services.value.map(s => ({ name: s.name, rating: s.rating })),
    slider: slider2.value,
    comment: comment.value
  })
  show.value = false
}
</script>

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
