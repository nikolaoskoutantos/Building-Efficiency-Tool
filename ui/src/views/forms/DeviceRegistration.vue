  computed: {
    isMQTTConfigValid() {
      // Check for required fields from backend
      return (
        this.mqttConfig &&
        typeof this.mqttConfig === 'object' &&
        this.mqttConfig.broker_url &&
        this.mqttConfig.broker_port
      )
    },
  },
<template>
  <CContainer>
    <!-- Existing Devices Section -->
    <CRow class="mb-4">
      <CCol>
        <CCard>
          <CCardHeader>
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <strong>Installed Devices</strong>
                <small class="ms-2">View and manage existing HVAC devices</small>
              </div>
              <div class="d-flex gap-2">
                <CButton
                  color="success"
                  variant="outline"
                  size="sm"
                  @click="toggleRegistrationForm"
                  :disabled="loadingDevices"
                  :title="showRegistrationForm ? '' : 'You can setup a new device and sensors under your registered building'"
                >
                  <CIcon v-if="showRegistrationForm" name="cilMinus" class="me-1" />
                  <CIcon v-else name="cilPlus" class="me-1" />
                  {{ showRegistrationForm ? 'Hide Form' : 'New' }}
                </CButton>
                <CButton
                  color="primary"
                  variant="outline"
                  size="sm"
                  @click="refreshDevices"
                  :disabled="loadingDevices"
                >
                  <CSpinner v-if="loadingDevices" size="sm" class="me-1" />
                  <CIcon v-else name="cilSync" class="me-1" />
                  Refresh
                </CButton>
                <CButton
                  color="info"
                  variant="outline"
                  size="sm"
                  @click="toggleMQTTInfo"
                  :title="mqttShow ? 'Hide MQTT Information' : 'Show MQTT Broker Configuration and Device Prefixes'"
                >
                  <CIcon name="cilInfo" class="me-1" />
                  MQTT Info
                </CButton>
              </div>
            </div>
          </CCardHeader>
          <CCardBody>
            <div v-if="loadingDevices" class="text-center p-4">
              <CSpinner />
              <p class="mt-2 text-muted">Loading devices...</p>
            </div>
            
            <div v-else-if="existingDevices.length === 0" class="text-center p-4 text-muted">
              <CIcon name="cilDevices" size="lg" class="mb-2" />
              <p class="mb-0">No devices installed yet</p>
              <small>Register your first device below</small>
            </div>
            
            <div v-else>
              <CRow>
                <CCol 
                  v-for="device in existingDevices" 
                  :key="device.id"
                  :md="6"
                  :lg="4"
                  class="mb-3"
                >
                  <CCard class="h-100 device-info-card">
                    <CCardBody>
                      <div class="d-flex justify-content-between align-items-start mb-2">
                        <h6 class="mb-1">{{ device.building_name }}</h6>
                        <CBadge 
                          :color="device.sensor_count > 0 ? 'success' : 'secondary'"
                        >
                          {{ device.sensor_count }} sensor{{ device.sensor_count !== 1 ? 's' : '' }}
                        </CBadge>
                      </div>
                      
                      <div class="mb-2">
                        <small class="text-muted d-block">
                          <strong>Location:</strong> 
                          {{ [device.central_unit, device.zone, device.room].filter(Boolean).join(' › ') || 'No location specified' }}
                        </small>
                        <small class="text-muted d-block">
                          <strong>Device Key:</strong> 
                          <code class="small">{{ device.device_key ? device.device_key.substring(0, 8) + '...' : 'No Key' }}</code>
                        </small>
                        <small class="text-muted">
                          <strong>Registered:</strong> 
                          {{ device.created_at ? new Date(device.created_at).toLocaleDateString() : 'Date unknown' }}
                        </small>
                      </div>
                      
                      <div class="d-flex gap-1">
                        <CButton
                          color="info"
                          variant="outline"
                          size="sm"
                          @click="viewDeviceDetails(device)"
                        >
                          <CIcon name="cilInfo" class="me-1" />
                          Details
                        </CButton>
                        <CButton
                          color="warning"
                          variant="outline"
                          size="sm"
                          @click="editDevice(device)"
                        >
                          <CIcon name="cilSettings" class="me-1" />
                          Edit
                        </CButton>
                        <CButton
                          color="secondary"
                          variant="outline"
                          size="sm"
                          @click="rotateDeviceKey(device)"
                          :disabled="loading"
                        >
                          <CIcon name="cilSync" class="me-1" />
                          {{ loading ? 'Processing...' : 'Rotate Key' }}
                        </CButton>
                      </div>
                    </CCardBody>
                  </CCard>
                </CCol>
              </CRow>
            </div>
          </CCardBody>
        </CCard>
      </CCol>
    </CRow>

    <!-- MQTT Broker Information Section -->
    <CRow v-if="showMQTTInfo">
      <CCol :md="10" :lg="8" class="mx-auto">
        <CCard class="mb-4 border-info">
          <CCardHeader class="bg-info text-white">
            <h5 class="mb-0">
              <CIcon icon="cilCloudUpload" size="sm" class="me-2"/>
              MQTT Broker Configuration
            </h5>
          </CCardHeader>
          <CCardBody>
            <div v-if="isMQTTConfigValid">
              <CRow class="mb-3">
                <CCol :md="6">
                  <strong>Broker URL:</strong> {{ mqttConfig.broker_url || 'Not configured' }}
                </CCol>
                <CCol :md="6">
                  <strong>Port:</strong> {{ mqttConfig.broker_port || 'Default (1883)' }}
                </CCol>
              </CRow>
              <CRow class="mb-3">
                <CCol :md="6">
                  <strong>TLS Enabled:</strong>
                  <CBadge :color="mqttConfig.use_tls ? 'success' : 'secondary'">
                    {{ mqttConfig.use_tls ? 'Yes' : 'No' }}
                  </CBadge>
                </CCol>
                <CCol :md="6">
                  <strong>Authentication:</strong>
                  <CBadge :color="mqttConfig.broker_username ? 'success' : 'secondary'">
                    {{ mqttConfig.broker_username ? 'Required' : 'None' }}
                  </CBadge>
                </CCol>
              </CRow>
              
              <!-- Device Publishing Topics -->
              <div v-if="devices.length > 0" class="mt-4">
                <h6 class="text-primary">Device Publishing Topics</h6>
                <CTable responsive striped>
                  <CTableHead>
                    <CTableRow>
                      <CTableHeaderCell>Device</CTableHeaderCell>
                      <CTableHeaderCell>MQTT Topic</CTableHeaderCell>
                      <CTableHeaderCell>Client ID</CTableHeaderCell>
                    </CTableRow>
                  </CTableHead>
                  <CTableBody>
                    <CTableRow v-for="device in devices" :key="device.hvac_unit_id">
                      <CTableDataCell>
                        <strong>{{ device.model }} {{ device.brand }}</strong>
                        <br>
                        <small class="text-muted">ID: {{ device.hvac_unit_id }}</small>
                      </CTableDataCell>
                      <CTableDataCell>
                        <code class="text-info">{{ getMQTTDevicePrefix(device.hvac_unit_id) }}</code>
                      </CTableDataCell>
                      <CTableDataCell>
                        <code class="text-success">{{ getMQTTClientId('device', device.hvac_unit_id) }}</code>
                      </CTableDataCell>
                    </CTableRow>
                  </CTableBody>
                </CTable>
              </div>

              <!-- Sensor Publishing Topics -->
              <div v-if="sensors.length > 0" class="mt-4">
                <h6 class="text-primary">Sensor Publishing Topics</h6>
                <CTable responsive striped>
                  <CTableHead>
                    <CTableRow>
                      <CTableHeaderCell>Sensor</CTableHeaderCell>
                      <CTableHeaderCell>MQTT Topic</CTableHeaderCell>
                      <CTableHeaderCell>Client ID</CTableHeaderCell>
                    </CTableRow>
                  </CTableHead>
                  <CTableBody>
                    <CTableRow v-for="sensor in sensors" :key="sensor.sensor_id">
                      <CTableDataCell>
                        <strong>{{ sensor.sensor_type }}</strong>
                        <br>
                        <small class="text-muted">ID: {{ sensor.sensor_id }} | Location: {{ sensor.location }}</small>
                      </CTableDataCell>
                      <CTableDataCell>
                        <code class="text-info">{{ getMQTTSensorTopic(sensor.hvac_unit_id, sensor.sensor_id) }}</code>
                      </CTableDataCell>
                      <CTableDataCell>
                        <code class="text-success">{{ getMQTTClientId('sensor', sensor.sensor_id) }}</code>
                      </CTableDataCell>
                    </CTableRow>
                  </CTableBody>
                </CTable>
              </div>

              <!-- MQTT Usage Instructions -->
              <div class="mt-4">
                <h6 class="text-primary">Publishing Instructions</h6>
                <CAlert color="info" class="mb-3">
                  <strong>Device Data Publishing:</strong><br>
                  Devices should publish their status and operational data to their assigned topic.<br>
                  <strong>Example payload:</strong> 
                  <code>{"temperature": 22.5, "status": "cooling", "power_consumption": 2.1}</code>
                </CAlert>
                <CAlert color="warning" class="mb-0">
                  <strong>Sensor Data Publishing:</strong><br>
                  Sensors should publish readings to their assigned topic. The payload_path field (optional) can specify a custom data route if needed.<br>
                  <strong>Example payload:</strong> 
                  <code>{"value": 24.3, "timestamp": "2024-01-15T10:30:00", "unit": "°C"}</code>
                </CAlert>
              </div>
            </div>
            <div v-else>
              <CAlert color="warning">
                <CIcon icon="cilInfo" class="me-2"/>
                MQTT broker configuration not available or incomplete.<br>
                Please Contact Support.
              </CAlert>
            </div>
          </CCardBody>
        </CCard>
      </CCol>
    </CRow>

    <!-- Registration/Edit Form Section -->
    <CRow v-if="showRegistrationForm">
      <CCol :md="10" :lg="8" class="mx-auto">
        <CCard class="mb-4">
          <CCardHeader>
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <strong>{{ editMode ? 'Edit Device & Sensors' : 'Device & Sensor Registration' }}</strong>
                <small class="ms-2">{{ editMode ? 'Update existing HVAC device' : 'Register HVAC devices with sensors' }}</small>
              </div>
              <CButton
                color="secondary"
                variant="ghost"
                size="sm"
                @click="cancelEdit"
              >
                <CIcon name="cilX" />
              </CButton>
            </div>
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

            <CForm @submit.prevent="registerDevice">
              <!-- Building Selection -->
              <div class="mb-3">
                <CFormLabel for="building-select">Building</CFormLabel>
                <CFormSelect
                  id="building-select"
                  v-model="form.building_id"
                  required
                  :disabled="loading"
                >
                  <option value="">Select a building</option>
                  <option 
                    v-for="building in buildings" 
                    :key="building.id" 
                    :value="building.id"
                  >
                    {{ building.name }} ({{ building.address }})
                  </option>
                </CFormSelect>
              </div>

              <!-- Device Location Fields -->
              <div class="mb-3">
                <CFormLabel for="central-unit">Central Unit</CFormLabel>
                <CFormInput
                  id="central-unit"
                  v-model="form.central_unit"
                  type="text"
                  placeholder="e.g. CU1, Main Unit"
                  :disabled="loading"
                />
              </div>

              <CRow>
                <CCol :md="6">
                  <div class="mb-3">
                    <CFormLabel for="zone">Zone</CFormLabel>
                    <CFormInput
                      id="zone"
                      v-model="form.zone"
                      type="text"
                      placeholder="e.g. Zone A, North Wing"
                      :disabled="loading"
                    />
                  </div>
                </CCol>
                <CCol :md="6">
                  <div class="mb-3">
                    <CFormLabel for="room">Room</CFormLabel>
                    <CFormInput
                      id="room"
                      v-model="form.room"
                      type="text"
                      placeholder="e.g. 101, Office 1"
                      :disabled="loading"
                    />
                  </div>
                </CCol>
              </CRow>

              <!-- Sensors Section -->
              <div class="mb-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                  <h6 class="mb-0">
                    Device Sensors 
                    <CBadge color="info" class="ms-2">{{ form.sensors.length }}</CBadge>
                  </h6>
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

                <!-- Sensor List -->
                <div 
                  v-if="form.sensors.length === 0" 
                  class="text-muted text-center p-3"
                >
                  No sensors added yet. Click "Add Sensor" to add sensors.
                </div>

                <CCard 
                  v-for="(sensor, index) in form.sensors" 
                  :key="index"
                  class="mb-3"
                  style="border-left: 4px solid #6f42c1;"
                >
                  <CCardBody>
                    <div class="d-flex justify-content-between align-items-start mb-3">
                      <div>
                        <h6 class="mb-1">Sensor {{ index + 1 }}</h6>
                        <small class="text-muted">{{ sensor.type || 'Type not selected' }}</small>
                      </div>
                      <CButtonGroup>
                        <CButton
                          color="danger"
                          variant="outline"
                          size="sm"
                          @click="removeSensor(index)"
                          :disabled="loading"
                          title="Remove this sensor"
                        >
                          <CIcon name="cilTrash" class="me-1" />
                          Remove
                        </CButton>
                      </CButtonGroup>
                    </div>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Sensor Type</CFormLabel>
                          <CFormSelect
                            v-model="sensor.type"
                            :disabled="loading"
                          >
                            <option value="">Select type</option>
                            <option value="temperature">Temperature</option>
                            <option value="humidity">Humidity</option>
                            <option value="energy">Energy</option>
                            <option value="pressure">Pressure</option>
                            <option value="presence">Presence</option>
                            <option value="air_quality">Air Quality</option>
                          </CFormSelect>
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Unit</CFormLabel>
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
                          <CFormLabel>Latitude</CFormLabel>
                          <CFormInput
                            v-model.number="sensor.lat"
                            type="number"
                            step="any"
                            required
                            :disabled="loading"
                          />
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Longitude</CFormLabel>
                          <CFormInput
                            v-model.number="sensor.lon"
                            type="number"
                            step="any"
                            required
                            :disabled="loading"
                          />
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Sensor Room (Optional)</CFormLabel>
                          <CFormInput
                            v-model="sensor.room"
                            type="text"
                            :disabled="loading"
                          />
                        </div>
                      </CCol>
                      <CCol :md="6">
                        <div class="mb-3">
                          <CFormLabel>Sensor Zone (Optional)</CFormLabel>
                          <CFormInput
                            v-model="sensor.zone"
                            type="text"
                            :disabled="loading"
                          />
                        </div>
                      </CCol>
                    </CRow>

                    <CRow>
                      <CCol :md="12">
                        <div class="mb-3">
                          <CFormLabel>Payload Path <span class="text-muted">(Optional)</span></CFormLabel>
                          <CFormInput
                            v-model="sensor.payload_path"
                            type="text"
                            :disabled="loading"
                            placeholder="e.g. /sensor/temperature/data, mqtt/device/temp, api/sensors/1 (leave empty if unknown)"
                          />
                          <small class="text-muted">Optional: Path or endpoint where sensor data is received (MQTT topic, API endpoint, etc.). Can be set later if unknown.</small>
                        </div>
                      </CCol>
                    </CRow>
                  </CCardBody>
                </CCard>
              </div>

              <!-- Submit Button -->
              <div class="d-grid">
                <CButton
                  color="primary"
                  type="submit"
                  :disabled="loading || !form.building_id"
                >
                  <CSpinner
                    v-if="loading"
                    size="sm"
                    class="me-2"
                  />
                  {{ loading ? (editMode ? 'Updating...' : 'Registering...') : (editMode ? `Update Device${form.sensors.length > 0 ? ` + ${form.sensors.length} Sensor${form.sensors.length !== 1 ? 's' : ''}` : ''}` : `Register Device${form.sensors.length > 0 ? ` + ${form.sensors.length} Sensor${form.sensors.length !== 1 ? 's' : ''}` : ''}`) }}
                </CButton>
              </div>
            </CForm>
          </CCardBody>
        </CCard>
      </CCol>
    </CRow>

    <!-- Device Credentials Modal - Always Available -->
    <CModal
      :visible="credentials.show"
      alignment="center"
      backdrop="static"
      keyboard="false"
    >
      <CModalHeader closeButton="false">
        <CModalTitle>{{ credentials.title }}</CModalTitle>
      </CModalHeader>
      <CModalBody>
        <CAlert :color="credentials.isRotation ? 'warning' : 'success'">
          <strong>Important:</strong> {{ credentials.isRotation ? 'New credentials generated! Old credentials are now invalid.' : 'Save these credentials securely. They will not be shown again!' }}
        </CAlert>
        
        <div class="mb-3">
          <CFormLabel>Device Key:</CFormLabel>
          <CInputGroup>
            <CFormInput
              :value="credentials.device_key"
              readonly
            />
            <CButton
              :color="copyState.deviceKey ? 'success' : 'secondary'"
              variant="outline"
              @click="copyToClipboard(credentials.device_key, 'deviceKey')"
            >
              {{ copyState.deviceKey ? 'Copied!' : 'Copy' }}
            </CButton>
          </CInputGroup>
        </div>

        <div class="mb-3">
          <CFormLabel>Device Secret:</CFormLabel>
          <CInputGroup>
            <CFormInput
              :value="credentials.device_secret"
              readonly
            />
            <CButton
              :color="copyState.deviceSecret ? 'success' : 'secondary'"
              variant="outline"
              @click="copyToClipboard(credentials.device_secret, 'deviceSecret')"
            >
              {{ copyState.deviceSecret ? 'Copied!' : 'Copy' }}
            </CButton>
          </CInputGroup>
        </div>
      </CModalBody>
      <CModalFooter>
        <CButton
          :color="copyState.all ? 'success' : 'secondary'"
          variant="outline"
          @click="copyCredentials"
          class="me-2"
        >
          {{ copyState.all ? 'Copied!' : 'Copy All' }}
        </CButton>
        <CButton
          color="primary"
          @click="closeCredentialsModal"
        >
          {{ credentials.isRotation ? 'I have saved the credentials' : 'Close & Register Another' }}
        </CButton>
      </CModalFooter>
    </CModal>

    <!-- MQTT Info Modal -->
    <CModal
      :visible="mqttModal.show"
      alignment="center"
      backdrop="static"
      keyboard="false"
    >
      <CModalHeader closeButton="false">
        <CModalTitle>MQTT Broker Configuration</CModalTitle>
      </CModalHeader>
      <CModalBody>
        <CAlert color="info">
          <strong>MQTT Connection Details:</strong> Copy these values for your device configuration.
        </CAlert>
        
        <div class="mb-3">
          <CFormLabel>Broker URL:</CFormLabel>
          <CInputGroup>
            <CFormInput
              :value="mqttModal.brokerUrl"
              readonly
            />
            <CButton
              :color="mqttCopyState.brokerUrl ? 'success' : 'secondary'"
              variant="outline"
              @click="copyToClipboard(mqttModal.brokerUrl, 'brokerUrl')"
            >
              {{ mqttCopyState.brokerUrl ? 'Copied!' : 'Copy' }}
            </CButton>
          </CInputGroup>
        </div>

        <div class="mb-3">
          <CFormLabel>Port:</CFormLabel>
          <CInputGroup>
            <CFormInput
              :value="mqttModal.brokerPort"
              readonly
            />
            <CButton
              :color="mqttCopyState.brokerPort ? 'success' : 'secondary'"
              variant="outline"
              @click="copyToClipboard(mqttModal.brokerPort, 'brokerPort')"
            >
              {{ mqttCopyState.brokerPort ? 'Copied!' : 'Copy' }}
            </CButton>
          </CInputGroup>
        </div>
      </CModalBody>
      <CModalFooter>
        <CButton color="secondary" @click="mqttModal.show = false">Close</CButton>
      </CModalFooter>
    </CModal>

    <!-- Confirmation Modal -->
    <CModal
      :visible="confirmation.show"
      alignment="center"
      backdrop="static"
      keyboard="false"
    >
      <CModalHeader closeButton="false">
        <CModalTitle>{{ confirmation.title }}</CModalTitle>
      </CModalHeader>
      <CModalBody>
        <div class="d-flex align-items-start">
          <CIcon 
            name="cilWarning" 
            class="text-warning me-3 mt-1" 
            size="lg"
          />
          <div>
            <p class="mb-0" style="white-space: pre-line;">{{ confirmation.message }}</p>
          </div>
        </div>
      </CModalBody>
      <CModalFooter>
        <CButton
          color="secondary"
          variant="outline"
          @click="closeConfirmation"
        >
          Cancel
        </CButton>
        <CButton
          color="warning"
          @click="confirmAction"
        >
          OK
        </CButton>
      </CModalFooter>
    </CModal>

    <!-- Device Details Modal -->
    <CModal
      :visible="deviceDetails.show"
      alignment="center"
      size="lg"
      @close="closeDeviceDetails"
    >
      <CModalHeader @close-click="closeDeviceDetails">
        <CModalTitle>Device Details</CModalTitle>
      </CModalHeader>
      <CModalBody>
        <div v-if="deviceDetails.device">
          <!-- Device Information -->
          <div class="mb-4">
            <h6 class="text-primary mb-3">
              <CIcon name="cilSettings" class="me-2" />
              Device Information
            </h6>
            <CRow>
              <CCol :md="6">
                <div class="mb-3">
                  <strong class="text-muted d-block">Building:</strong>
                  <span>{{ deviceDetails.device.building_name }}</span>
                </div>
                <div class="mb-3">
                  <strong class="text-muted d-block">Location:</strong>
                  <span>{{ [deviceDetails.device.central_unit, deviceDetails.device.zone, deviceDetails.device.room].filter(Boolean).join(' › ') || 'No location specified' }}</span>
                </div>
              </CCol>
              <CCol :md="6">
                <div class="mb-3">
                  <strong class="text-muted d-block">Device Key:</strong>
                  <code class="small">{{ deviceDetails.device.device_key || 'No Key' }}</code>
                </div>
                <div class="mb-3">
                  <strong class="text-muted d-block">Registered:</strong>
                  <span>{{ deviceDetails.device.created_at ? new Date(deviceDetails.device.created_at).toLocaleDateString() : 'Date unknown' }}</span>
                </div>
              </CCol>
            </CRow>
          </div>

          <!-- Sensors Information -->
          <div>
            <h6 class="text-primary mb-3">
              <CIcon name="cilSpeedometer" class="me-2" />
              Sensors ({{ deviceDetails.device.sensor_count }})
            </h6>

            <div v-if="deviceDetails.loading" class="text-center p-3">
              <CSpinner />
              <p class="mt-2 mb-0 text-muted">Loading sensors...</p>
            </div>

            <div v-else-if="deviceDetails.sensors.length === 0" class="text-center p-3 text-muted">
              <CIcon name="cilXCircle" size="lg" class="mb-2" />
              <p class="mb-0">No sensors found for this device</p>
              <small>Sensors may not be registered yet</small>
            </div>

            <div v-else>
              <CRow>
                <CCol 
                  v-for="(sensor, index) in deviceDetails.sensors" 
                  :key="sensor.id || index"
                  :md="6"
                  class="mb-3"
                >
                  <CCard class="h-100" style="border-left: 4px solid #6f42c1;">
                    <CCardBody>
                      <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                          <h6 class="mb-1">Sensor {{ index + 1 }}</h6>
                          <CBadge color="info">{{ sensor.type || 'Unknown' }}</CBadge>
                        </div>
                        <small v-if="sensor.id" class="text-muted">ID: {{ sensor.id }}</small>
                        <small v-else class="text-muted">Auto ID</small>
                      </div>
                      
                      <div class="small">
                        <div class="mb-2">
                          <strong>Unit:</strong> {{ sensor.unit }}<br>
                          <strong>Sampling:</strong> {{ sensor.rate_of_sampling || 5 }} seconds<br>
                          <strong>Path:</strong> <code class="small">{{ sensor.payload_path || 'No path' }}</code><br>
                          <strong>Location:</strong> {{ [sensor.central_unit, sensor.zone, sensor.room].filter(Boolean).join(' › ') || 'No location' }}
                        </div>
                        <div class="mb-2">
                          <strong>Coordinates:</strong> {{ sensor.lat }}, {{ sensor.lon }}
                        </div>
                      </div>
                    </CCardBody>
                  </CCard>
                </CCol>
              </CRow>
            </div>
          </div>
        </div>
      </CModalBody>
      <CModalFooter>
        <CButton
          color="primary"
          @click="closeDeviceDetails"
        >
          Close
        </CButton>
      </CModalFooter>
    </CModal>
  </CContainer>
</template>

<script>
export default {
  name: 'DeviceRegistration',
  data() {
    return {
      loading: false,
      loadingDevices: false,
      buildings: [],
      existingDevices: [],
      showRegistrationForm: false,
      editMode: false,
      editingDeviceId: null,
      form: {
        building_id: '',
        central_unit: '',
        zone: '',
        room: '',
        sensors: []
      },
      alert: {
        show: false,
        color: 'danger',
        message: ''
      },
      credentials: {
        show: false,
        device_key: '',
        device_secret: '',
        title: 'Device Registered Successfully!',
        isRotation: false
      },
      copyState: {
        deviceKey: false,
        deviceSecret: false,
        all: false
      },
      mqttModal: {
        show: false,
        brokerUrl: '',
        brokerPort: ''
      },
      mqttCopyState: {
        brokerUrl: false,
        brokerPort: false
      },
      confirmation: {
        show: false,
        title: '',
        message: '',
        device: null,
        action: null
      },
      deviceDetails: {
        show: false,
        device: null,
        sensors: [],
        loading: false
      },
      sensorUnitMapping: {
        temperature: ['°C', '°F', 'K'],
        humidity: ['%', 'g/kg', 'g/m³'],
        energy: ['kWh', 'Wh', 'MWh', 'J', 'kJ', 'MJ'],
        pressure: ['Pa', 'kPa', 'hPa', 'bar', 'mbar', 'psi', 'mmHg'],
        presence: ['boolean', 'binary', 'occupancy', '%', 'count'],
        air_quality: ['ppm', 'µg/m³', 'mg/m³', 'AQI', '%']
      },
      mqttConfig: {
        broker_url: '',
        broker_port: 1883,
        topic_prefix: 'qoe',
        client_id_prefix: 'qoe_device',
        use_tls: false,
        loading: false
      },
      showMQTTInfo: false
    }
  },
  computed: {
    apiBaseUrl() {
      return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    }
  },
  mounted() {
    console.log('DeviceRegistration mounted, API Base URL:', this.apiBaseUrl)
    this.loadBuildings()
    this.loadExistingDevices()
    // Don't start with sensors by default anymore - only when editing or user adds
  },
  methods: {
    async loadBuildings() {
      try {
        const response = await fetch(`${this.apiBaseUrl}/buildings`)
        if (!response.ok) throw new Error('Failed to fetch buildings')
        this.buildings = await response.json()
        
        // Auto-select default building from user settings
        await this.setDefaultBuilding()
      } catch (error) {
        console.error('Failed to load buildings:', error)
        this.showAlert('danger', 'Failed to load buildings. Please refresh the page.')
      }
    },

    async setDefaultBuilding() {
      if (this.form.building_id || this.buildings.length === 0) return
      
      try {
        let defaultBuildingId = null
        
        // Get user's default building from localStorage since backend endpoint doesn't exist yet
        const savedSettings = localStorage.getItem('userSettings')
        if (savedSettings) {
          const settings = JSON.parse(savedSettings)
          defaultBuildingId = settings.default_building_id
        }
        
        // Backend endpoint for user settings is not yet implemented. Fetch logic will be added when available.
        
        // If no saved default, use first building (minimum ID)
        if (!defaultBuildingId && this.buildings.length > 0) {
          this.buildings.sort((a, b) => a.id - b.id)
          defaultBuildingId = this.buildings[0].id
        }
        
        // Set the default building
        if (defaultBuildingId) {
          const building = this.buildings.find(b => b.id === defaultBuildingId)
          if (building) {
            this.form.building_id = defaultBuildingId.toString()
          }
        }
      } catch (error) {
        console.error('Failed to set default building:', error)
        // Fallback: use first building if available
        if (this.buildings.length > 0) {
          this.buildings.sort((a, b) => a.id - b.id)
          this.form.building_id = this.buildings[0].id.toString()
        }
      }
    },

    async loadExistingDevices() {
      this.loadingDevices = true
      try {
        const response = await fetch(`${this.apiBaseUrl}/devices`)
        if (!response.ok) throw new Error('Failed to fetch devices')
        const devices = await response.json()
        
        // Devices now come with real sensor counts from backend
        this.existingDevices = devices
      } catch (error) {
        console.error('Failed to load existing devices:', error)
        this.showAlert('danger', 'Failed to load existing devices.')
        this.existingDevices = []
      } finally {
        this.loadingDevices = false
      }
    },

    getAvailableUnits(sensorType) {
      return this.sensorUnitMapping[sensorType] || []
    },

    async loadMQTTConfig() {
      this.mqttConfig.loading = true
      console.log('Loading MQTT config from API:', `${this.apiBaseUrl}/mqtt/config`)
      try {
        const response = await fetch(`${this.apiBaseUrl}/mqtt/config`)
        if (!response.ok) throw new Error('Failed to fetch MQTT config')
        const config = await response.json()
        console.log('MQTT config response:', config)
        this.mqttConfig = {
          ...this.mqttConfig,
          ...config,
          loading: false
        }
      } catch (error) {
        console.error('Failed to load MQTT config:', error)
        this.mqttConfig.loading = false
        this.showAlert('warning', 'Failed to load MQTT configuration.')
      }
    },

    getMQTTDevicePrefix(deviceId) {
      return `${this.mqttConfig.topic_prefix}/devices/${deviceId}`
    },

    getMQTTSensorTopic(deviceId, sensorId) {
      return `${this.mqttConfig.topic_prefix}/devices/${deviceId}/sensors/${sensorId}`
    },

    getMQTTClientId(deviceId) {
      return `${this.mqttConfig.client_id_prefix}_${deviceId}`
    },

    async toggleMQTTInfo() {
      // Load MQTT config if not already loaded
      if (!this.mqttConfig.broker_url) {
        await this.loadMQTTConfig()
      }
      // Set modal data and show
      this.mqttModal.brokerUrl = this.mqttConfig.broker_url || ''
      this.mqttModal.brokerPort = this.mqttConfig.broker_port ? String(this.mqttConfig.broker_port) : ''
      this.mqttModal.show = true
    },

    async refreshDevices() {
      await this.loadExistingDevices()
      this.showAlert('success', 'Device list refreshed.')
    },

    toggleRegistrationForm() {
      this.showRegistrationForm = !this.showRegistrationForm
      if (this.showRegistrationForm && !this.editMode) {
        this.resetForm()
        // resetForm() already adds one sensor, no need to add another
      }
    },

    async editDevice(device) {
      this.editMode = true
      this.editingDeviceId = device.id
      this.showRegistrationForm = true
      
      // Pre-fill form with device data
      this.form.building_id = device.building_id
      this.form.central_unit = device.central_unit || ''
      this.form.zone = device.zone || ''
      this.form.room = device.room || ''
      
      // Load existing sensors for this device
      try {
        const response = await fetch(`${this.apiBaseUrl}/devices/${device.id}/sensors`)
        if (response.ok) {
          const sensors = await response.json()
          // No need to add rate_of_sampling or raw_data_id - handled by database
          this.form.sensors = sensors
        } else {
          this.form.sensors = []
        }
      } catch (error) {
        console.error('Failed to load sensors for editing:', error)
        this.form.sensors = []
      }
      
      this.showAlert('info', `Editing device: ${device.building_name}. Update details below.`)
      
      // Scroll to form
      setTimeout(() => {
        document.querySelector('.card .card-header').scrollIntoView({ behavior: 'smooth' })
      }, 100)
    },

    async rotateDeviceKey(device) {
      console.log('Rotate key clicked for device:', device)
      
      // Show custom confirmation modal instead of browser confirm
      this.confirmation.title = 'Rotate Device Key'
      this.confirmation.message = `Rotate device key for ${device.building_name}?\n\nThis will generate new credentials and invalidate the old ones.`
      this.confirmation.device = device
      this.confirmation.action = 'rotate'
      this.confirmation.show = true
    },

    async confirmAction() {
      if (this.confirmation.action === 'rotate') {
        await this.performKeyRotation(this.confirmation.device)
      }
      this.closeConfirmation()
    },

    closeConfirmation() {
      this.confirmation.show = false
      this.confirmation.title = ''
      this.confirmation.message = ''
      this.confirmation.device = null
      this.confirmation.action = null
    },

    async performKeyRotation(device) {
      console.log('Starting key rotation...')
      this.loading = true
      
      try {
        const url = `${this.apiBaseUrl}/devices/${device.id}/credentials/upsert`
        console.log('Calling API:', url)
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include',
          body: JSON.stringify({})
        })
        
        console.log('API Response status:', response.status)
        
        if (!response.ok) {
          const errorText = await response.text()
          console.error('API Error response:', errorText)
          let errorData
          try {
            errorData = JSON.parse(errorText)
          } catch {
            errorData = { detail: errorText || `HTTP Error ${response.status}` }
          }
          throw new Error(errorData.detail || 'Failed to rotate key')
        }
        
        const newCredentials = await response.json()
        console.log('New credentials received:', { 
          device_key: newCredentials.device_key ? '***received***' : 'missing',
          device_secret: newCredentials.device_secret ? '***received***' : 'missing'
        })
        
        // Show new credentials in modal
        console.log('Setting credentials data...')
        this.credentials.device_key = newCredentials.device_key
        this.credentials.device_secret = newCredentials.device_secret
        this.credentials.title = 'Device Key Rotated Successfully!'
        this.credentials.isRotation = true
        console.log('About to show modal, credentials.show will be:', true)
        
        // Use nextTick to ensure Vue has processed the data changes
        await this.$nextTick()
        this.credentials.show = true
        console.log('Modal show state set to:', this.credentials.show)
        
        // Refresh device list to show updated key
        await this.loadExistingDevices()
        console.log('Key rotation completed successfully')
        
      } catch (error) {
        console.error('Key rotation failed:', error)
        this.showAlert('danger', error.message || 'Failed to rotate device key.')
      } finally {
        this.loading = false
      }
    },
    closeCredentialsModal() {
      const shouldResetForm = !this.credentials.isRotation
      
      this.credentials.show = false
      this.credentials.device_key = ''
      this.credentials.device_secret = ''
      this.credentials.isRotation = false
      
      // Reset copy states
      this.copyState.deviceKey = false
      this.copyState.deviceSecret = false
      this.copyState.all = false
      
      if (shouldResetForm) {
        // Only reset form for new registrations, not key rotations
        this.resetForm()
      }
    },

    copyCredentials() {
      const credentialsText = `Device Key: ${this.credentials.device_key}\nDevice Secret: ${this.credentials.device_secret}`
      this.copyToClipboard(credentialsText, 'all')
    },
    
    cancelEdit() {
      this.editMode = false
      this.editingDeviceId = null
      this.showRegistrationForm = false
      this.resetForm()
    },

    async viewDeviceDetails(device) {
      console.log('View details for device:', device)
      
      // Set device and show modal
      this.deviceDetails.device = device
      this.deviceDetails.sensors = []
      this.deviceDetails.loading = true
      this.deviceDetails.show = true
      
      try {
        // Fetch sensors for this device
        const response = await fetch(`${this.apiBaseUrl}/devices/${device.id}/sensors`)
        if (response.ok) {
          this.deviceDetails.sensors = await response.json()
        } else {
          console.warn('Failed to fetch sensors for device:', device.id)
        }
      } catch (error) {
        console.error('Error fetching device sensors:', error)
        this.deviceDetails.sensors = []
      } finally {
        this.deviceDetails.loading = false
      }
    },

    closeDeviceDetails() {
      this.deviceDetails.show = false
      this.deviceDetails.device = null
      this.deviceDetails.sensors = []
      this.deviceDetails.loading = false
    },

    addSensorsToDevice(device) {
      // Pre-fill form with device info to add sensors
      const building = this.buildings.find(b => b.id === device.building_id)
      if (building) {
        this.form.building_id = device.building_id
        this.form.central_unit = device.central_unit || ''
        this.form.zone = device.zone || ''
        this.form.room = device.room || ''
        this.form.sensors = [] // Clear sensors to add new ones
        this.addSensor()
        
        this.showAlert('info', `Form pre-filled with ${device.building_name} device info. Add sensors below.`)
        
        // Scroll to form
        document.querySelector('form').scrollIntoView({ behavior: 'smooth' })
      }
    },

    addSensor() {
      this.form.sensors.push({
        type: '',
        lat: 37.9755,
        lon: 23.7348,
        unit: '',
        room: '',
        zone: '',
        central_unit: '',
        payload_path: ''
        // rate_of_sampling and raw_data_id are handled automatically by the database
      })
    },

    removeSensor(index) {
      this.form.sensors.splice(index, 1)
      this.showAlert('success', 'Sensor removed successfully.')
    },

    // Validation helper methods
    validateDeviceForm() {
      if (!this.form.building_id) {
        this.showAlert('warning', 'Please select a building.')
        return false
      }

      if (this.editMode && (!this.form.central_unit || !this.form.zone || !this.form.room)) {
        this.showAlert('warning', 'Please fill in all device identification fields.')
        return false
      }

      return true
    },

    validateSensorsForm() {
      for (let i = 0; i < this.form.sensors.length; i++) {
        const sensor = this.form.sensors[i]
        if (!sensor.type || !sensor.unit) {
          this.showAlert('warning', `Please fill all required fields for Sensor ${i + 1} (type and unit).`)
          return false
        }
        
        const coordinatesValid = this.validateSensorCoordinates(sensor, i + 1)
        if (!coordinatesValid) {
          return false
        }
      }
      return true
    },

    validateSensorCoordinates(sensor, sensorNumber) {
      const lat = Number(sensor.lat)
      const lon = Number(sensor.lon)
      
      if (Number.isNaN(lat) || Number.isNaN(lon)) {
        this.showAlert('warning', `Please enter valid coordinates for Sensor ${sensorNumber}.`)
        return false
      }
      if (lat < -90 || lat > 90) {
        this.showAlert('warning', `Latitude must be between -90 and 90 for Sensor ${sensorNumber}.`)
        return false
      }
      if (lon < -180 || lon > 180) {
        this.showAlert('warning', `Longitude must be between -180 and 180 for Sensor ${sensorNumber}.`)
        return false
      }
      return true
    },

    prepareSensorPayload() {
      return this.form.sensors.map(sensor => {
        const cleanedSensor = {
          type: sensor.type || '',
          lat: Number(sensor.lat) || 0,
          lon: Number(sensor.lon) || 0,
          unit: sensor.unit || '',
          payload_path: sensor.payload_path || ''
        }
        
        // Only add optional fields if they have values
        if (sensor.room && sensor.room.trim()) {
          cleanedSensor.room = sensor.room.trim()
        }
        if (sensor.zone && sensor.zone.trim()) {
          cleanedSensor.zone = sensor.zone.trim()
        }
        if (sensor.central_unit && sensor.central_unit.trim()) {
          cleanedSensor.central_unit = sensor.central_unit.trim()
        }
        
        return cleanedSensor
      })
    },

    buildDevicePayload(cleanedSensors) {
      return {
        building_id: Number.parseInt(this.form.building_id),
        central_unit: this.form.central_unit || null,
        zone: this.form.zone || null,
        room: this.form.room || null,
        sensors: cleanedSensors.length > 0 ? cleanedSensors : null
      }
    },

    async makeDeviceApiCall(payload) {
      const url = this.editMode 
        ? `${this.apiBaseUrl}/devices/${this.editingDeviceId}`
        : `${this.apiBaseUrl}/devices/register`
      
      const method = this.editMode ? 'PUT' : 'POST'
      
      return await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      })
    },

    async parseApiError(response) {
      const errorResponse = await response.text()
      let errorMessage = 'Unknown error occurred'
      
      try {
        const errorData = JSON.parse(errorResponse)
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail.map(err => {
              if (typeof err === 'object') {
                return `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg || err.message || err}`
              }
              return err
            }).join('; ')
          } else if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail
          } else {
            errorMessage = JSON.stringify(errorData.detail)
          }
        } else {
          errorMessage = errorData.message || JSON.stringify(errorData)
        }
      } catch {
        errorMessage = errorResponse || `HTTP ${response.status}: ${response.statusText}`
      }
      
      return errorMessage
    },

    async handleDeviceSuccess(result) {
      if (this.editMode) {
        // Success message for updates
        this.showAlert('success', 'Device updated successfully!')
      } else {
        // Only show credentials for new registrations
        this.credentials.device_key = result.device_key
        this.credentials.device_secret = result.device_secret
        this.credentials.title = 'Device Registered Successfully!'
        this.credentials.isRotation = false
        this.credentials.show = true
      }

      // Refresh the device list and reset form
      await this.loadExistingDevices()
      if (this.editMode) {
        this.cancelEdit()
      }
    },

    async registerDevice() {
      if (!this.validateDeviceForm() || !this.validateSensorsForm()) {
        return
      }

      this.loading = true
      this.alert.show = false

      try {
        const cleanedSensors = this.prepareSensorPayload()
        const payload = this.buildDevicePayload(cleanedSensors)

        console.log('Sending payload:', JSON.stringify(payload, null, 2))

        const response = await this.makeDeviceApiCall(payload)

        if (!response.ok) {
          const errorMessage = await this.parseApiError(response)
          console.error('API Error Response:', errorMessage)
          throw new Error(errorMessage)
        }

        const result = await response.json()
        await this.handleDeviceSuccess(result)

      } catch (error) {
        console.error('Device operation failed:', error)
        const message = this.editMode 
          ? 'Failed to update device. Please try again.' 
          : 'Failed to register device. Please try again.'
        
        this.showAlert('danger', error.message || message)
      } finally {
        this.loading = false
      }
    },

    resetForm() {
      // Clear edit mode completely
      this.editMode = false
      this.editingDeviceId = null
      
      this.form = {
        building_id: '',
        central_unit: '',
        zone: '',
        room: '',
        sensors: []
      }
      this.addSensor() // Add one default sensor
      this.credentials.show = false
      this.alert.show = false
      
      // Set default building after reset
      this.setDefaultBuilding()
    },

    showAlert(color, message) {
      this.alert.color = color
      this.alert.message = message
      this.alert.show = true
    },

    // Clipboard helper methods
    copyToClipboard(text, copyType = null) {
      if (navigator.clipboard && globalThis.isSecureContext) {
        this.copyWithModernApi(text, copyType)
      } else {
        this.fallbackCopyToClipboard(text, copyType)
      }
    },

    copyWithModernApi(text, copyType) {
      navigator.clipboard.writeText(text).then(() => {
        this.handleCopySuccess(copyType)
      }).catch((err) => {
        console.warn('Clipboard API failed:', err)
        this.fallbackCopyToClipboard(text, copyType)
      })
    },

    handleCopySuccess(copyType) {
      if (copyType) {
        // Handle MQTT copy states
        if (copyType === 'brokerUrl' || copyType === 'brokerPort') {
          this.mqttCopyState[copyType] = true
          // Reset the copy state after 2 seconds
          setTimeout(() => {
            this.mqttCopyState[copyType] = false
          }, 2000)
        } else {
          // Handle regular copy states
          this.copyState[copyType] = true
          // Reset the copy state after 2 seconds
          setTimeout(() => {
            this.copyState[copyType] = false
          }, 2000)
        }
      }
      this.showAlert('success', 'Copied to clipboard!')
    },

    fallbackCopyToClipboard(text, copyType = null) {
      try {
        // Create a temporary textarea element
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.left = '-999999px'
        textarea.style.top = '-999999px'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        
        // Try to copy using execCommand
        const successful = document.execCommand('copy')
        textarea.remove()
        
        if (successful) {
          this.handleCopySuccess(copyType)
        } else {
          this.showAlert('warning', 'Please manually copy the text')
        }
      } catch (err) {
        console.error('Fallback copy failed:', err)
        this.showAlert('warning', 'Copy not supported. Please manually copy the text')
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
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.device-info-card {
  transition: all 0.2s ease;
  border-left: 4px solid #0066cc;
}

.device-info-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
</style>