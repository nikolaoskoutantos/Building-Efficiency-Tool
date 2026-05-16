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
                    {{ device.building_name }} — {{ device.name }} ({{ device.unit_type }})
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
                >
                  <CCardBody>
                    <div class="d-flex justify-content-between align-items-start mb-3">
                      <div>
                        <h6 class="mb-1">Sensor {{ index + 1 }}</h6>
                        <small class="text-muted">{{ sensor.sensor_type || 'Type not selected' }}</small>
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
                          <CFormLabel>Sensor Name <span class="text-danger">*</span></CFormLabel>
                          <CFormInput
                            v-model="sensor.name"
                            type="text"
                            required
                            :disabled="loading"
                            placeholder="e.g. Supply Air Temp"
                          />
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Sensor Type *</CFormLabel>
                          <CFormSelect
                            v-model="sensor.sensor_type"
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
                            <option value="motion">Motion / Occupancy</option>
                            <option value="light">Light</option>
                            <option value="power">Power</option>
                            <option value="flow">Airflow</option>
                            <option value="setpoint">Setpoint</option>
                            <option value="status">Status / Mode</option>
                          </CFormSelect>
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Unit *</CFormLabel>
                          <CFormSelect
                            v-model="sensor.unit"
                            required
                            :disabled="loading || !sensor.sensor_type"
                          >
                            <option value="">{{ sensor.sensor_type ? 'Select unit' : 'Select sensor type first' }}</option>
                            <option 
                              v-for="unit in getAvailableUnits(sensor.sensor_type)" 
                              :key="unit" 
                              :value="unit"
                            >
                              {{ unit }}
                            </option>
                          </CFormSelect>
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Payload Path <span class="text-muted">(Optional)</span></CFormLabel>
                          <CFormInput
                            v-model="sensor.payload_path"
                            type="text"
                            :disabled="loading"
                            placeholder="e.g. temperature, sensors.temp"
                          />
                          <small class="text-muted">JSON key path in the MQTT message.</small>
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>External Sensor ID <span class="text-muted">(Optional)</span></CFormLabel>
                          <CFormInput
                            v-model="sensor.external_sensor_id"
                            type="text"
                            :disabled="loading"
                            placeholder="BMS or external system ID"
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
        async loadBuildings() {
          try {
            const jwtToken = this.getJwtToken()
            const headers = { 'Content-Type': 'application/json' }
            if (jwtToken) headers['Authorization'] = `Bearer ${jwtToken}`
            await axios.get(
              `${import.meta.env.VITE_API_BASE_URL}/buildings`,
              {
                headers,
                withCredentials: true
              }
            )
            // You can handle the response as needed, e.g. store in this.buildings
            // this.buildings = response.data
          } catch (error) {
            console.error('Failed to load buildings:', error)
            this.showAlert('danger', 'Failed to load buildings. Please refresh the page.')
          }
        },
    async loadDevices() {
      try {
        const jwtToken = this.getJwtToken()
        const headers = { 'Content-Type': 'application/json' }
        if (jwtToken) headers['Authorization'] = `Bearer ${jwtToken}`
        const response = await axios.get(
          `${import.meta.env.VITE_API_BASE_URL}/devices`,
          {
            headers,
            withCredentials: true
          }
        )
        this.devices = response.data.map(device => ({
          ...device
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
        name: '',
        sensor_type: '',
        unit: '',
        payload_path: '',
        external_sensor_id: ''
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
      for (let i = 0; i < this.form.sensors.length; i++) {
        const sensor = this.form.sensors[i]
        if (!sensor.name || !sensor.name.trim()) {
          this.showAlert('warning', `Please enter a name for Sensor ${i + 1}.`)
          return
        }
        if (!sensor.sensor_type || !sensor.unit) {
          this.showAlert('warning', `Please fill all required fields for Sensor ${i + 1} (type and unit).`)
          return
        }
      }
      this.loading = true
      this.alert.show = false
      try {
        const payload = {
          device_id: Number.parseInt(this.form.device_id),
          sensors: this.form.sensors.map(s => ({
            name: s.name.trim(),
            sensor_type: s.sensor_type,
            unit: s.unit || null,
            payload_path: s.payload_path || null,
            external_sensor_id: s.external_sensor_id || null
          }))
        }
        const jwtToken = this.getJwtToken()
        const headers = { 'Content-Type': 'application/json' }
        if (jwtToken) headers['Authorization'] = `Bearer ${jwtToken}`
        await axios.post(
          `${import.meta.env.VITE_API_BASE_URL}/devices/sensors`,
          payload,
          {
            headers,
            withCredentials: true
          }
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
    getJwtToken() {
      try {
        const authStore = globalThis.$authStore || null
        if (authStore && typeof authStore.getJwtToken === 'function') {
          return authStore.getJwtToken()
        }
        const token = localStorage.getItem('jwtToken')
        return token || null
      } catch (error) {
        console.warn('Could not get JWT token:', error)
        return null
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
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.06);
  transition: all 0.2s ease;
}

.sensor-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.09);
}

.sensor-card :deep(.card-body) {
  background:
    radial-gradient(circle at top right, rgba(32, 201, 151, 0.09), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
}

.sensor-card h6 {
  color: #132238;
  font-weight: 700;
}

.sensor-card :deep(.form-label) {
  color: #445066;
  font-weight: 600;
}

.sensor-card :deep(.form-control),
.sensor-card :deep(.form-select) {
  border-radius: 12px;
  border-color: rgba(19, 34, 56, 0.12);
}

.text-muted {
  color: #6c757d !important;
}
</style>
