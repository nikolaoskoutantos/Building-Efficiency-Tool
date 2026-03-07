<template>
  <CContainer>
    <CRow>
      <CCol :md="8" :lg="6" class="mx-auto">
        <CCard class="mb-4">
          <CCardHeader>
            <strong>Sensor Registration</strong>
            <small class="ms-2">Register sensors for an existing device</small>
          </CCardHeader>
          <CCardBody>
            <CAlert 
              v-if="alert.show" 
              :color="alert.color" 
              :visible="alert.show"
              @close="alert.show = false"
            >
              {{ alert.message }}
            </CAlert>

            <CForm @submit.prevent="registerSensors">
              <!-- Device Selection -->
              <div class="mb-3">
                <CFormLabel for="device-select">HVAC Device</CFormLabel>
                <CFormSelect
                  id="device-select"
                  v-model="form.device_id"
                  required
                  :disabled="loading"
                >
                  <option value="">Select a device</option>
                  <option 
                    v-for="device in devices" 
                    :key="device.id" 
                    :value="device.id"
                  >
                    {{ device.building_name }} - {{ device.location }}
                  </option>
                </CFormSelect>
              </div>

              <!-- Sensors Section -->
              <div class="mb-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <h6 class="mb-0">Sensors to Register</h6>
                  <CButton
                    color="secondary"
                    variant="outline"
                    size="sm"
                    @click="addSensor"
                    :disabled="loading"
                  >
                    <CIcon name="cilPlus" class="me-1" />
                    Add Sensor
                  </CButton>
                </div>

                <div 
                  v-if="form.sensors.length === 0" 
                  class="text-muted text-center p-4"
                >
                  <CIcon name="cilSensors" size="lg" class="mb-2" />
                  <p>No sensors added yet. Click "Add Sensor" to add sensors to this device.</p>
                </div>

                <CCard 
                  v-for="(sensor, index) in form.sensors" 
                  :key="index"
                  class="mb-3 sensor-card"
                  style="border-left: 4px solid #20c997;"
                >
                  <CCardBody>
                    <div class="d-flex justify-content-between align-items-start mb-3">
                      <div>
                        <h6 class="mb-1">Sensor {{ index + 1 }}</h6>
                        <small class="text-muted">{{ sensor.type || 'Type not selected' }}</small>
                      </div>
                      <CButton
                        color="danger"
                        variant="ghost"
                        size="sm"
                        @click="removeSensor(index)"
                        :disabled="loading"
                      >
                        <CIcon name="cilTrash" />
                      </CButton>
                    </div>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Sensor Type *</CFormLabel>
                          <CFormSelect
                            v-model="sensor.type"
                            required
                            :disabled="loading"
                          >
                            <option value="">Select type</option>
                            <option value="temperature">Temperature</option>
                            <option value="humidity">Humidity</option>
                            <option value="energy">Energy</option>
                            <option value="pressure">Pressure</option>
                            <option value="air_quality">Air Quality</option>
                            <option value="co2">CO2</option>
                            <option value="motion">Motion</option>
                            <option value="light">Light</option>
                          </CFormSelect>
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Unit *</CFormLabel>
                          <CFormSelect
                            v-model="sensor.unit"
                            required
                            :disabled="loading || !sensor.type"
                          >
                            <option value="">{{ sensor.type ? 'Select unit' : 'Select sensor type first' }}</option>
                            <option 
                              v-for="unit in getAvailableUnits(sensor.type)" 
                              :key="unit" 
                              :value="unit"
                            >
                              {{ unit }}
                            </option>
                          </CFormSelect>
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Latitude *</CFormLabel>
                          <CFormInput
                            v-model.number="sensor.lat"
                            type="number"
                            step="0.000001"
                            required
                            :disabled="loading"
                            placeholder="37.9755"
                          />
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Longitude *</CFormLabel>
                          <CFormInput
                            v-model.number="sensor.lon"
                            type="number"
                            step="0.000001"
                            required
                            :disabled="loading"
                            placeholder="23.7348"
                          />
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Raw Data ID *</CFormLabel>
                          <CFormInput
                            v-model.number="sensor.raw_data_id"
                            type="number"
                            min="1"
                            required
                            :disabled="loading"
                            placeholder="1"
                          />
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Description</CFormLabel>
                          <CFormInput
                            v-model="sensor.description"
                            type="text"
                            :disabled="loading"
                            placeholder="Optional sensor description"
                          />
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="4">
                        <div class="mb-3">
                          <CFormLabel>Room</CFormLabel>
                          <CFormInput
                            v-model="sensor.room"
                            type="text"
                            :disabled="loading"
                            placeholder="e.g. 101"
                          />
                        </div>
                      </CCol>
                      <CCol :md="4">
                        <div class="mb-3">
                          <CFormLabel>Zone</CFormLabel>
                          <CFormInput
                            v-model="sensor.zone"
                            type="text"
                            :disabled="loading"
                            placeholder="e.g. Zone A"
                          />
                        </div>
                      </CCol>
                      <CCol :md="4">
                        <div class="mb-3">
                          <CFormLabel>Central Unit</CFormLabel>
                          <CFormInput
                            v-model="sensor.central_unit"
                            type="text"
                            :disabled="loading"
                            placeholder="e.g. CU1"
                          />
                        </div>
                      </CCol>
                    </CRow>
                  </CCardBody>
                </CCard>
              </div>

              <!-- Submit Button -->
              <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                <CButton
                  color="secondary"
                  variant="outline"
                  @click="resetForm"
                  :disabled="loading"
                >
                  Clear Form
                </CButton>
                <CButton
                  color="success"
                  type="submit"
                  :disabled="loading || !form.device_id || form.sensors.length === 0"
                >
                  <CSpinner
                    v-if="loading"
                    size="sm"
                    class="me-2"
                  />
                  {{ loading ? 'Registering...' : `Register ${form.sensors.length} Sensor${form.sensors.length !== 1 ? 's' : ''}` }}
                </CButton>
              </div>
            </CForm>
          </CCardBody>
        </CCard>

        <!-- Success Modal -->
        <CModal
          :visible="successModal.show"
          @close="successModal.show = false"
          alignment="center"
        >
          <CModalHeader>
            <CModalTitle>
              <CIcon name="cilCheckCircle" class="me-2 text-success" />
              Sensors Registered Successfully!
            </CModalTitle>
          </CModalHeader>
          <CModalBody>
            <CAlert color="success">
              Successfully registered {{ successModal.count }} sensor{{ successModal.count !== 1 ? 's' : '' }} 
              to the selected device.
            </CAlert>
            
            <p class="mb-0">
              The sensors are now active and ready to collect data. You can view them in the 
              device management section.
            </p>
          </CModalBody>
          <CModalFooter>
            <CButton
              color="secondary"
              variant="outline"
              @click="successModal.show = false"
            >
              Close
            </CButton>
            <CButton
              color="success"
              @click="registerAnother"
            >
              Register More Sensors
            </CButton>
          </CModalFooter>
        </CModal>
      </CCol>
    </CRow>
  </CContainer>
</template>

<script>
import axios from 'axios'

export default {
  name: 'SensorRegistration',
  data() {
    return {
      loading: false,
      devices: [],
      form: {
        device_id: '',
        sensors: []
      },
      alert: {
        show: false,
        color: 'danger',
        message: ''
      },
      successModal: {
        show: false,
        count: 0
      },
      sensorUnitMapping: {
        temperature: ['°C', '°F', 'K'],
        humidity: ['%', 'g/kg', 'g/m³'],
        energy: ['kWh', 'Wh', 'MWh', 'J', 'kJ', 'MJ'],
        pressure: ['Pa', 'kPa', 'hPa', 'bar', 'mbar', 'psi', 'mmHg'],
        air_quality: ['ppm', 'µg/m³', 'mg/m³', 'AQI', '%'],
        co2: ['ppm', 'µg/m³', 'mg/m³'],
        motion: ['motion', 'presence', 'occupied'],
        light: ['lux', 'cd/m²', '%']
      }
    }
  },
  mounted() {
    this.loadDevices()
    this.addSensor() // Start with one sensor
  },
  methods: {
    async loadDevices() {
      try {
        // Note: You might need to create this endpoint in your API
        const response = await axios.get(`${import.meta.env.VITE_API_BASE_URL}/devices`)
        this.devices = response.data.map(device => ({
          ...device,
          location: `${device.central_unit || 'No Unit'} - ${device.zone || 'No Zone'} - ${device.room || 'No Room'}`
        }))
      } catch (error) {
        console.error('Failed to load devices:', error)
        this.showAlert('danger', 'Failed to load devices. Please refresh the page.')
      }
    },

    getAvailableUnits(sensorType) {
      return this.sensorUnitMapping[sensorType] || []
    },

    addSensor() {
      this.form.sensors.push({
        type: '',
        lat: 37.9755,
        lon: 23.7348,
        raw_data_id: this.form.sensors.length + 1,
        unit: '',
        room: '',
        zone: '',
        central_unit: '',
        description: ''
      })
    },

    removeSensor(index) {
      this.form.sensors.splice(index, 1)
    },

    async registerSensors() {
      if (!this.form.device_id) {
        this.showAlert('warning', 'Please select a device.')
        return
      }

      if (this.form.sensors.length === 0) {
        this.showAlert('warning', 'Please add at least one sensor.')
        return
      }

      // Validate required fields
      for (let i = 0; i < this.form.sensors.length; i++) {
        const sensor = this.form.sensors[i]
        if (!sensor.type || !sensor.unit || !sensor.lat || !sensor.lon || !sensor.raw_data_id) {
          this.showAlert('warning', `Please fill all required fields for Sensor ${i + 1}.`)
          return
        }
      }

      this.loading = true
      this.alert.show = false

      try {
        // Note: You might need to create this endpoint or modify the existing one
        const payload = {
          device_id: Number.parseInt(this.form.device_id),
          sensors: this.form.sensors
        }

        await axios.post(
          `${import.meta.env.VITE_API_BASE_URL}/devices/sensors`,
          payload
        )

        this.successModal.count = this.form.sensors.length
        this.successModal.show = true

      } catch (error) {
        console.error('Sensor registration failed:', error)
        let message = 'Failed to register sensors. Please try again.'
        
        if (error.response?.data?.detail) {
          message = error.response.data.detail
        }
        
        this.showAlert('danger', message)
      } finally {
        this.loading = false
      }
    },

    resetForm() {
      this.form = {
        device_id: '',
        sensors: []
      }
      this.addSensor() // Add one default sensor
      this.alert.show = false
    },

    registerAnother() {
      this.resetForm()
      this.successModal.show = false
    },

    showAlert(color, message) {
      this.alert.color = color
      this.alert.message = message
      this.alert.show = true
      
      // Auto-hide success alerts
      if (color === 'success') {
        setTimeout(() => {
          this.alert.show = false
        }, 5000)
      }
    }
  }
}
</script>

<style scoped>
.sensor-card {
  transition: all 0.2s ease;
}

.sensor-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.text-muted {
  color: #6c757d !important;
}
</style>