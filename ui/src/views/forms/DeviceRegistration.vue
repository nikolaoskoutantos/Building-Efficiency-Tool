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
        <CCard class="installed-devices-panel">
          <CCardHeader class="installed-devices-panel__header">
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
              <small>Click New to register your first device</small>
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
                          <strong>Name:</strong> 
                          {{ device.name || 'No name' }}
                        </small>
                        <small class="text-muted d-block">
                          <strong>Type:</strong> 
                          {{ device.unit_type || 'Unknown' }}
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
                        <CButton
                          color="danger"
                          variant="outline"
                          size="sm"
                          @click="deleteDevice(device)"
                          :disabled="loading"
                        >
                          <CIcon name="cilTrash" />
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

    <!-- Registration/Edit Sidebar -->
    <COffcanvas
      :visible="showRegistrationForm"
      placement="end"
      :backdrop="false"
      @hide="closeRegistrationForm"
      class="device-registration-panel"
      :style="registrationPanelStyle"
    >
      <div
        class="device-registration-resize-handle"
        @mousedown.prevent="startRegistrationResize"
        @touchstart.prevent="startRegistrationResize"
      />
      <COffcanvasHeader class="border-bottom">
        <COffcanvasTitle>
          <CIcon :name="editMode ? 'cilSettings' : 'cilPlus'" class="me-2" />
          {{ editMode ? 'Edit Device & Sensors' : 'Device & Sensor Registration' }}
        </COffcanvasTitle>
        <CButton class="btn-close" @click="closeRegistrationForm" aria-label="Close" />
      </COffcanvasHeader>
      <COffcanvasBody>
        <p class="text-muted small mb-4">
          {{ editMode ? 'Update the selected HVAC device and manage its sensors from this sidebar.' : 'Register a new HVAC device and configure its sensors from this sidebar.' }}
        </p>

        <CAlert
          v-if="alert.show"
          :color="alert.color"
          :visible="alert.show"
          dismissible
          @close="alert.show = false"
        >
          {{ alert.message }}
        </CAlert>

        <CForm class="registration-form-shell" @submit.prevent="registerDevice">
          <div class="mb-3">
            <CFormLabel for="building-select">Building</CFormLabel>
            <CFormSelect
              id="building-select"
              v-model="form.building_id"
              required
              :disabled="loading || editMode"
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
            <small v-if="editMode" class="text-body-secondary d-block mt-1">
              Building cannot be changed while editing an existing device. Use `New` to register a device under another building.
            </small>
          </div>

          <div class="mb-3">
            <CFormLabel for="device-name">Device Name <span class="text-danger">*</span></CFormLabel>
            <CFormInput
              id="device-name"
              v-model="form.name"
              type="text"
              placeholder="e.g. AHU-1, Rooftop Unit"
              required
              :disabled="loading"
            />
          </div>

          <div class="mb-4">
            <CFormLabel for="unit-type">Unit Type <span class="text-danger">*</span></CFormLabel>
            <CFormSelect
              id="unit-type"
              v-model="form.unit_type"
              required
              :disabled="loading"
            >
              <option value="">Select unit type</option>
              <option value="ahu">Air Handling Unit (AHU)</option>
              <option value="heat_pump">Heat Pump</option>
              <option value="fan_coil">Fan Coil Unit</option>
              <option value="vrf">VRF / VRV</option>
              <option value="chiller">Chiller</option>
              <option value="boiler">Boiler</option>
              <option value="split">Split Unit</option>
              <option value="rooftop">Rooftop Unit</option>
              <option value="other">Other</option>
            </CFormSelect>
          </div>

          <!-- ── Zones Section ── -->
          <div class="registration-zones-section mb-4">
            <button
              type="button"
              class="d-flex justify-content-between align-items-center mb-2 registration-section-toggle"
              @click="zonesOpen = !zonesOpen"
            >
              <div>
                <h6 class="mb-0">
                  <span class="topology-embed-chevron me-2" :class="{ open: zonesOpen }">&#8250;</span>
                  Zones
                  <CBadge color="secondary" class="ms-2">{{ form.zones.length }}</CBadge>
                </h6>
                <small class="text-muted">
                  <template v-if="form.zones.length <= 1">
                    1 zone will be created automatically. Add more for multi-zone (industrial) setups.
                  </template>
                  <template v-else>
                    Each sensor can be assigned to one of these zones.
                  </template>
                </small>
              </div>
              <CButton color="secondary" variant="outline" size="sm" @click.stop="addZone" :disabled="loading">
                <CIcon name="cilPlus" class="me-1" />Add Zone
              </CButton>
            </button>

            <div v-show="zonesOpen">
              <div v-for="(zone, zi) in form.zones" :key="zi" class="d-flex align-items-center gap-2 mb-2">
                <CFormInput
                  v-model="form.zones[zi].name"
                  :placeholder="zi === 0 ? 'Zone name (e.g. Main Zone)' : `Zone ${zi + 1} name`"
                  size="sm"
                  class="flex-grow-1"
                />
                <CFormSelect v-model="form.zones[zi].zone_type" size="sm" style="max-width:140px;">
                  <option value="">Type (optional)</option>
                  <option value="residential">Residential</option>
                  <option value="office">Office</option>
                  <option value="industrial">Industrial</option>
                  <option value="server_room">Server Room</option>
                  <option value="other">Other</option>
                </CFormSelect>
                <CButton
                  v-if="form.zones.length > 1"
                  color="danger"
                  variant="ghost"
                  size="sm"
                  @click="removeZone(zi)"
                >&times;</CButton>
              </div>
            </div>
          </div>

          <div v-if="form.building_id" class="registration-rooms-section mb-4">
            <button
              type="button"
              class="d-flex justify-content-between align-items-center mb-2 registration-section-toggle"
              @click="roomsOpen = !roomsOpen"
            >
              <div>
                <h6 class="mb-0">
                  <span class="topology-embed-chevron me-2" :class="{ open: roomsOpen }">&#8250;</span>
                  Rooms
                  <CBadge color="light" text-color="dark" class="ms-2">{{ topology.rooms.length }}</CBadge>
                </h6>
                <small class="text-muted">
                  Optional. Add rooms here if you want sensor assignments beyond zone-only topology.
                </small>
              </div>
            </button>

            <div v-show="roomsOpen">
              <div class="d-flex align-items-center gap-2 mb-2">
                <CFormSelect
                  v-model="roomDraftZoneId"
                  size="sm"
                  style="max-width:160px;flex-shrink:0;"
                >
                  <option value="">Zone (optional)</option>
                  <optgroup v-if="formDefinedZones.length > 0" label="This device">
                    <option v-for="z in formDefinedZones" :key="'name:'+z.name" :value="'name:'+z.name">{{ z.name }}</option>
                  </optgroup>
                  <optgroup v-if="topology.zones.length > 0" label="Existing">
                    <option v-for="z in topology.zones" :key="z.id" :value="z.id">{{ z.name }}</option>
                  </optgroup>
                </CFormSelect>
                <CFormInput
                  v-model="roomDraftName"
                  placeholder="Room name (e.g. Office 101)"
                  size="sm"
                  class="flex-grow-1"
                  :disabled="loading || roomCreateLoading || topology.loading"
                  @keydown.enter.prevent="createRoom"
                />
                <CButton
                  color="secondary"
                  variant="outline"
                  size="sm"
                  :disabled="loading || roomCreateLoading || topology.loading || !roomDraftName.trim()"
                  @click.stop="createRoom"
                >
                  <CSpinner v-if="roomCreateLoading" size="sm" class="me-1" />
                  <CIcon v-else name="cilPlus" class="me-1" />
                  Add Room
                </CButton>
              </div>

              <div v-if="displayRooms.length > 0" class="d-flex flex-wrap gap-2">
                <CBadge
                  v-for="(room, ri) in displayRooms"
                  :key="room.id || ri"
                  color="info"
                  shape="rounded-pill"
                  class="px-3 py-2"
                >
                  {{ room.name }}{{ room.zone_name ? ` · ${room.zone_name}` : '' }}
                </CBadge>
              </div>
              <div v-else class="text-muted small">
                No rooms configured yet. If you leave it like this, the building behaves as `HVAC 1:N Zones`.
              </div>
            </div>
          </div>

          <div class="registration-sensors-section mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <div>
                <h6 class="mb-0">
                  Device Sensors
                  <CBadge color="info" class="ms-2">{{ form.sensors.length }}</CBadge>
                </h6>
                <small class="text-muted">Add, edit, and remove sensors from the same right sidebar flow.</small>
              </div>
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
              class="text-muted text-center p-3 registration-empty-state"
            >
              No sensors added yet. Click "Add Sensor" to add sensors.
            </div>

            <CCard
              v-for="(sensor, index) in form.sensors"
              :key="index"
              class="mb-3 sensor-card"
            >
              <CCardBody>
                <div class="d-flex justify-content-between align-items-center">
                  <div>
                    <h6 class="mb-0">Sensor {{ index + 1 }}</h6>
                    <small class="text-muted">
                      {{ sensor.sensor_type || 'Type not set' }}
                      <template v-if="sensor.name"> · {{ sensor.name }}</template>
                      <template v-if="sensor.unit"> · {{ sensor.unit }}</template>
                    </small>
                  </div>
                  <div class="d-flex gap-2">
                    <CButton
                      color="primary"
                      variant="outline"
                      size="sm"
                      @click="openSensorEdit(index)"
                      :disabled="loading"
                    >
                      <CIcon name="cilPencil" class="me-1" />
                      Edit
                    </CButton>
                    <CButton
                      color="danger"
                      variant="outline"
                      size="sm"
                      @click="removeSensor(index)"
                      :disabled="loading"
                    >
                      <CIcon name="cilTrash" />
                    </CButton>
                  </div>
                </div>
              </CCardBody>
            </CCard>
          </div>

          <div class="d-flex gap-2">
            <CButton
              color="primary"
              type="submit"
              :disabled="loading || !form.building_id"
              class="flex-grow-1"
            >
              <CSpinner
                v-if="loading"
                size="sm"
                class="me-2"
              />
              {{ loading ? (editMode ? 'Updating...' : 'Registering...') : (editMode ? `Update Device${form.sensors.length > 0 ? ` + ${form.sensors.length} Sensor${form.sensors.length !== 1 ? 's' : ''}` : ''}` : `Register Device${form.sensors.length > 0 ? ` + ${form.sensors.length} Sensor${form.sensors.length !== 1 ? 's' : ''}` : ''}`) }}
            </CButton>
            <CButton
              color="secondary"
              variant="outline"
              @click="closeRegistrationForm"
              :disabled="loading"
            >
              Cancel
            </CButton>
          </div>
        </CForm>
      </COffcanvasBody>
    </COffcanvas>

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

    <!-- Device Details — draggable window -->
    <Transition name="sp-fade">
      <div v-if="deviceDetails.show" class="dd-overlay" @mousedown.self="closeDeviceDetails">
        <div
          class="dd-window"
          :style="deviceDetails.pos ? { left: deviceDetails.pos.x + 'px', top: deviceDetails.pos.y + 'px', transform: 'none' } : {}"
        >
          <div class="dd-window__header" @mousedown="startDetailsDrag">
            <span>Device Details</span>
            <button class="dd-window__close" @click="closeDeviceDetails">&times;</button>
          </div>
          <div class="dd-window__body">
        <div v-if="deviceDetails.device">
          <!-- Device Information -->
          <div class="mb-4">
            <h6 class="text-primary mb-3">
              <CIcon name="cilSettings" class="me-2" />
              Device Information
            </h6>
            <CRow>
              <CCol :md="6">
                <div class="mb-2">
                  <strong class="text-muted d-block">Name:</strong>
                  <span>{{ deviceDetails.device.name || 'No name' }}</span>
                </div>
                <div class="mb-2">
                  <strong class="text-muted d-block">Unit Type:</strong>
                  <span>{{ deviceDetails.device.unit_type || 'Unknown' }}</span>
                </div>
                <div class="mb-2">
                  <strong class="text-muted d-block">Device ID:</strong>
                  <span class="d-inline-flex align-items-center gap-2">
                    <code class="small">{{ deviceDetails.device.id }}</code>
                    <CButton size="sm" variant="ghost" color="secondary" class="p-0 px-1"
                      @click="copyToClipboard(String(deviceDetails.device.id), 'deviceId')">
                      <CIcon :name="deviceDetails.copied.deviceId ? 'cilCheckAlt' : 'cilClone'" size="sm" />
                    </CButton>
                  </span>
                </div>
              </CCol>
              <CCol :md="6">
                <div class="mb-2">
                  <strong class="text-muted d-block">Device Key:</strong>
                  <span class="d-inline-flex align-items-center gap-2 flex-wrap">
                    <code class="small text-break">{{ deviceDetails.device.device_key || 'No Key' }}</code>
                    <CButton size="sm" variant="ghost" color="secondary" class="p-0 px-1"
                      @click="copyToClipboard(deviceDetails.device.device_key, 'deviceKey')">
                      <CIcon :name="deviceDetails.copied.deviceKey ? 'cilCheckAlt' : 'cilClone'" size="sm" />
                    </CButton>
                  </span>
                </div>
                <div class="mb-2">
                  <strong class="text-muted d-block">Building ID:</strong>
                  <span class="d-inline-flex align-items-center gap-2">
                    <code class="small">{{ deviceDetails.device.building_id }}</code>
                    <CButton size="sm" variant="ghost" color="secondary" class="p-0 px-1"
                      @click="copyToClipboard(String(deviceDetails.device.building_id), 'buildingId')">
                      <CIcon :name="deviceDetails.copied.buildingId ? 'cilCheckAlt' : 'cilClone'" size="sm" />
                    </CButton>
                  </span>
                </div>
                <div class="mb-2">
                  <strong class="text-muted d-block">Registered:</strong>
                  <span>{{ deviceDetails.device.created_at ? new Date(deviceDetails.device.created_at).toLocaleDateString() : 'Date unknown' }}</span>
                </div>
              </CCol>
            </CRow>
          </div>

          <!-- Sensors Information -->
          <div class="mb-4">
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
                  <CCard class="h-100 sensor-card">
                    <CCardBody>
                      <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                          <h6 class="mb-1">Sensor {{ index + 1 }}</h6>
                          <CBadge color="info">{{ sensor.sensor_type || 'Unknown' }}</CBadge>
                        </div>
                        <span class="d-inline-flex align-items-center gap-1">
                          <small v-if="sensor.id" class="text-muted">ID: {{ sensor.id }}</small>
                          <small v-else class="text-muted">Auto ID</small>
                          <CButton v-if="sensor.id" size="sm" variant="ghost" color="secondary" class="p-0 px-1"
                            @click="copyToClipboard(String(sensor.id), 'sensor_' + sensor.id)">
                            <CIcon :name="deviceDetails.copied['sensor_' + sensor.id] ? 'cilCheckAlt' : 'cilClone'" size="sm" />
                          </CButton>
                        </span>
                      </div>
                      <div class="small">
                        <strong>Name:</strong> {{ sensor.name || 'No name' }}<br>
                        <strong>Unit:</strong> {{ sensor.unit }}<br>
                        <strong>Path:</strong> <code class="small">{{ sensor.payload_path || 'No path' }}</code><br>
                        <strong>External ID:</strong> {{ sensor.external_sensor_id || '—' }}
                      </div>
                    </CCardBody>
                  </CCard>
                </CCol>
              </CRow>
            </div>
          </div>

          <!-- Technical Documentation -->
          <div v-if="!deviceDetails.loading">
            <!-- Collapsible header -->
            <div
              class="d-flex align-items-center justify-content-between p-2 rounded border mb-0"
              style="cursor:pointer; user-select:none;"
              @click="deviceDetails.techDocsOpen = !deviceDetails.techDocsOpen"
            >
              <h6 class="text-primary mb-0">
                <CIcon name="cilCode" class="me-2" />
                Technical Documentation
              </h6>
              <CIcon :name="deviceDetails.techDocsOpen ? 'cilChevronTop' : 'cilChevronBottom'" size="sm" class="text-muted" />
            </div>

            <div v-show="deviceDetails.techDocsOpen" class="border border-top-0 rounded-bottom p-3 mb-1">
              <!-- Secret section -->
              <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3 p-2 rounded border bg-light">
                <div class="small">
                  <strong>Device Secret:</strong>
                  <template v-if="deviceDetails.device_secret">
                    <code class="ms-2 text-break">{{ deviceDetails.device_secret }}</code>
                    <CButton size="sm" variant="ghost" color="secondary" class="p-0 px-1 ms-1"
                      @click="copyToClipboard(deviceDetails.device_secret, 'secret')">
                      <CIcon :name="deviceDetails.copied.secret ? 'cilCheckAlt' : 'cilClone'" size="sm" />
                    </CButton>
                  </template>
                  <span v-else class="text-muted ms-2">not revealed — rotate key to get it</span>
                </div>

                <!-- Inline confirmation -->
                <div v-if="deviceDetails.confirmRotate" class="d-flex align-items-center gap-2 flex-wrap">
                  <small class="text-danger fw-semibold">
                    <CIcon name="cilWarning" size="sm" class="me-1" />
                    Current key will stop working immediately. Continue?
                  </small>
                  <CButton color="danger" size="sm" :disabled="loading" @click="confirmAndRotate">
                    <CSpinner v-if="loading" size="sm" class="me-1" />
                    Yes, rotate
                  </CButton>
                  <CButton color="secondary" size="sm" variant="outline" @click="deviceDetails.confirmRotate = false">Cancel</CButton>
                </div>
                <CButton v-else color="secondary" size="sm" variant="outline" @click="deviceDetails.confirmRotate = true">
                  <CIcon name="cilSync" class="me-1" />
                  {{ deviceDetails.device_secret ? 'Rotate Again' : 'Rotate & Reveal Secret' }}
                </CButton>
              </div>

              <!-- REST / MQTT toggle -->
              <div class="d-flex gap-2 mb-3">
                <CButton
                  size="sm"
                  :color="deviceDetails.snippetTab === 'rest' ? 'primary' : 'secondary'"
                  :variant="deviceDetails.snippetTab === 'rest' ? '' : 'outline'"
                  @click="deviceDetails.snippetTab = 'rest'; deviceDetails.curlStep = 1"
                >REST</CButton>
                <CButton
                  size="sm"
                  :color="deviceDetails.snippetTab === 'mqtt' ? 'primary' : 'secondary'"
                  :variant="deviceDetails.snippetTab === 'mqtt' ? '' : 'outline'"
                  @click="deviceDetails.snippetTab = 'mqtt'; deviceDetails.curlStep = 1"
                >MQTT</CButton>
              </div>

              <!-- Sensor reference table -->
              <table class="table table-sm table-bordered mb-3">
                <thead class="table-light">
                  <tr>
                    <th>Sensor</th>
                    <th>Type</th>
                    <th>Unit</th>
                    <th>Field sent</th>
                    <th>Simulated value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in deviceDetails.sensors" :key="s.id">
                    <td class="small">{{ s.name || '—' }}</td>
                    <td><code class="small">{{ s.sensor_type }}</code></td>
                    <td class="small">{{ s.unit || '—' }}</td>
                    <td><code class="small">{{ s.sensor_type === 'presence' ? 'value_bool' : 'value' }}</code></td>
                    <td class="small text-muted">{{ sensorSimRange(s.sensor_type) }}</td>
                  </tr>
                </tbody>
              </table>

              <!-- Step tabs — REST -->
              <template v-if="deviceDetails.snippetTab === 'rest'">
                <div class="d-flex gap-1 mb-3 border-bottom pb-2">
                  <CButton size="sm"
                    :color="deviceDetails.curlStep === 1 ? 'primary' : 'secondary'"
                    :variant="deviceDetails.curlStep === 1 ? '' : 'outline'"
                    @click="deviceDetails.curlStep = 1">① Auth</CButton>
                  <CButton size="sm"
                    :color="deviceDetails.curlStep === 2 ? 'primary' : 'secondary'"
                    :variant="deviceDetails.curlStep === 2 ? '' : 'outline'"
                    @click="deviceDetails.curlStep = 2">② Single</CButton>
                  <CButton size="sm"
                    :color="deviceDetails.curlStep === 3 ? 'primary' : 'secondary'"
                    :variant="deviceDetails.curlStep === 3 ? '' : 'outline'"
                    @click="deviceDetails.curlStep = 3">③ Bulk</CButton>
                  <CButton size="sm"
                    :color="deviceDetails.curlStep === 4 ? 'primary' : 'secondary'"
                    :variant="deviceDetails.curlStep === 4 ? '' : 'outline'"
                    @click="deviceDetails.curlStep = 4">④ Notebook</CButton>
                </div>

                <!-- Step 1: Auth -->
                <div v-if="deviceDetails.curlStep === 1">
                  <p class="small text-muted mb-2">Authenticate the device to get a short-lived JWT. Run this once — the token is valid for ~1 hour.</p>
                  <div class="position-relative">
                    <pre class="bg-dark text-light rounded p-3 mb-0 overflow-auto" style="font-size:0.74rem; white-space:pre;">{{ buildCurlAuth() }}</pre>
                    <CButton size="sm" color="secondary" variant="outline" class="position-absolute top-0 end-0 m-2"
                      @click="copyToClipboard(buildCurlAuth(), 'curlAuth')">
                      <CIcon :name="deviceDetails.copied.curlAuth ? 'cilCheckAlt' : 'cilClone'" size="sm" class="me-1" />
                      {{ deviceDetails.copied.curlAuth ? 'Copied!' : 'Copy' }}
                    </CButton>
                  </div>
                </div>

                <!-- Step 2: Single reading — with sensor picker -->
                <div v-if="deviceDetails.curlStep === 2">
                  <p class="small text-muted mb-2">Send one reading for a single sensor. Pick the sensor below:</p>
                  <div class="d-flex gap-1 flex-wrap mb-2">
                    <CButton
                      v-for="(s, i) in deviceDetails.sensors" :key="s.id"
                      size="sm"
                      :color="deviceDetails.curlSensor === i ? 'info' : 'secondary'"
                      :variant="deviceDetails.curlSensor === i ? '' : 'outline'"
                      @click="deviceDetails.curlSensor = i"
                    >{{ s.name || s.sensor_type }}</CButton>
                  </div>
                  <div v-if="deviceDetails.sensors[deviceDetails.curlSensor]" class="position-relative">
                    <pre class="bg-dark text-light rounded p-3 mb-0 overflow-auto" style="font-size:0.74rem; white-space:pre;">{{ buildCurlSingle(deviceDetails.sensors[deviceDetails.curlSensor]) }}</pre>
                    <CButton size="sm" color="secondary" variant="outline" class="position-absolute top-0 end-0 m-2"
                      @click="copyToClipboard(buildCurlSingle(deviceDetails.sensors[deviceDetails.curlSensor]), 'curlSingle')">
                      <CIcon :name="deviceDetails.copied.curlSingle ? 'cilCheckAlt' : 'cilClone'" size="sm" class="me-1" />
                      {{ deviceDetails.copied.curlSingle ? 'Copied!' : 'Copy' }}
                    </CButton>
                  </div>
                </div>

                <!-- Step 3: Bulk -->
                <div v-if="deviceDetails.curlStep === 3">
                  <p class="small text-muted mb-2">Send all {{ deviceDetails.sensors.length }} sensors in one request — ideal for scheduled polling.</p>
                  <div class="position-relative">
                    <pre class="bg-dark text-light rounded p-3 mb-0 overflow-auto" style="font-size:0.74rem; white-space:pre;">{{ buildCurlBulk() }}</pre>
                    <CButton size="sm" color="secondary" variant="outline" class="position-absolute top-0 end-0 m-2"
                      @click="copyToClipboard(buildCurlBulk(), 'curlBulk')">
                      <CIcon :name="deviceDetails.copied.curlBulk ? 'cilCheckAlt' : 'cilClone'" size="sm" class="me-1" />
                      {{ deviceDetails.copied.curlBulk ? 'Copied!' : 'Copy' }}
                    </CButton>
                  </div>
                </div>

                <!-- Step 4: Notebook config -->
                <div v-if="deviceDetails.curlStep === 4">
                  <p class="small text-muted mb-2">Paste this into the <strong>REST Notebook</strong> config cell to run the full simulation.</p>
                  <div class="position-relative">
                    <pre class="bg-dark text-light rounded p-3 mb-0 overflow-auto" style="max-height:240px; font-size:0.74rem; white-space:pre;">{{ buildSimulatorSnippet('rest') }}</pre>
                    <CButton size="sm" color="secondary" variant="outline" class="position-absolute top-0 end-0 m-2"
                      @click="copyToClipboard(buildSimulatorSnippet('rest'), 'snippet')">
                      <CIcon :name="deviceDetails.copied.snippet ? 'cilCheckAlt' : 'cilClone'" size="sm" class="me-1" />
                      {{ deviceDetails.copied.snippet ? 'Copied!' : 'Copy' }}
                    </CButton>
                  </div>
                </div>
              </template>

              <!-- Step tabs — MQTT -->
              <template v-else>
                <div class="d-flex gap-1 mb-3 border-bottom pb-2">
                  <CButton size="sm"
                    :color="deviceDetails.curlStep === 1 ? 'primary' : 'secondary'"
                    :variant="deviceDetails.curlStep === 1 ? '' : 'outline'"
                    @click="deviceDetails.curlStep = 1">① Publish</CButton>
                  <CButton size="sm"
                    :color="deviceDetails.curlStep === 2 ? 'primary' : 'secondary'"
                    :variant="deviceDetails.curlStep === 2 ? '' : 'outline'"
                    @click="deviceDetails.curlStep = 2">② Notebook</CButton>
                </div>

                <!-- MQTT Step 1: publish with sensor picker -->
                <div v-if="deviceDetails.curlStep === 1">
                  <p class="small text-muted mb-2">Publish a sensor reading via MQTT (requires <code>mosquitto_pub</code>). Pick sensor:</p>
                  <div class="d-flex gap-1 flex-wrap mb-2">
                    <CButton
                      v-for="(s, i) in deviceDetails.sensors" :key="s.id"
                      size="sm"
                      :color="deviceDetails.curlSensor === i ? 'info' : 'secondary'"
                      :variant="deviceDetails.curlSensor === i ? '' : 'outline'"
                      @click="deviceDetails.curlSensor = i"
                    >{{ s.name || s.sensor_type }}</CButton>
                  </div>
                  <div v-if="deviceDetails.sensors[deviceDetails.curlSensor]" class="position-relative">
                    <pre class="bg-dark text-light rounded p-3 mb-0 overflow-auto" style="font-size:0.74rem; white-space:pre;">{{ buildMosquittoCmd(deviceDetails.sensors[deviceDetails.curlSensor]) }}</pre>
                    <CButton size="sm" color="secondary" variant="outline" class="position-absolute top-0 end-0 m-2"
                      @click="copyToClipboard(buildMosquittoCmd(deviceDetails.sensors[deviceDetails.curlSensor]), 'mqttCmd')">
                      <CIcon :name="deviceDetails.copied.mqttCmd ? 'cilCheckAlt' : 'cilClone'" size="sm" class="me-1" />
                      {{ deviceDetails.copied.mqttCmd ? 'Copied!' : 'Copy' }}
                    </CButton>
                  </div>
                </div>

                <!-- MQTT Step 2: Notebook config -->
                <div v-if="deviceDetails.curlStep === 2">
                  <p class="small text-muted mb-2">Paste this into the <strong>MQTT Notebook</strong> config cell.</p>
                  <div class="position-relative">
                    <pre class="bg-dark text-light rounded p-3 mb-0 overflow-auto" style="max-height:240px; font-size:0.74rem; white-space:pre;">{{ buildSimulatorSnippet('mqtt') }}</pre>
                    <CButton size="sm" color="secondary" variant="outline" class="position-absolute top-0 end-0 m-2"
                      @click="copyToClipboard(buildSimulatorSnippet('mqtt'), 'snippet')">
                      <CIcon :name="deviceDetails.copied.snippet ? 'cilCheckAlt' : 'cilClone'" size="sm" class="me-1" />
                      {{ deviceDetails.copied.snippet ? 'Copied!' : 'Copy' }}
                    </CButton>
                  </div>
                </div>
              </template>

            </div>
          </div>
        </div>
          </div>
          <div class="dd-window__footer">
            <CButton color="primary" @click="closeDeviceDetails">Close</CButton>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Sensor Edit Sidebar -->
    <COffcanvas
      :visible="sensorEdit.show"
      placement="end"
      :backdrop="false"
      @hide="closeSensorEdit"
      class="sensor-edit-panel"
      :style="sensorPanelStyle"
    >
      <div
        class="sensor-edit-resize-handle"
        @mousedown.prevent="startSensorResize"
        @touchstart.prevent="startSensorResize"
      />
      <COffcanvasHeader class="border-bottom">
        <COffcanvasTitle>
          <CIcon name="cilSpeedometer" class="me-2" />
          Edit Sensor {{ sensorEdit.index !== null ? sensorEdit.index + 1 : '' }}
        </COffcanvasTitle>
        <CButton class="btn-close" @click="closeSensorEdit" aria-label="Close" />
      </COffcanvasHeader>
      <COffcanvasBody v-if="sensorEdit.draft" class="sensor-edit-shell">

        <!-- ── Identity ───────────────────────────────────────── -->
        <div class="se-section">
          <div class="se-section__title">Identity</div>
          <CRow class="mb-3">
            <CCol :xs="12" :sm="6">
              <CFormLabel>Sensor Name <span class="text-danger">*</span></CFormLabel>
              <CFormInput v-model="sensorEdit.draft.name" type="text" placeholder="e.g. Supply Air Temp" />
            </CCol>
            <CCol :xs="12" :sm="6" class="mt-3 mt-sm-0">
              <CFormLabel>Sensor Type <span class="text-danger">*</span></CFormLabel>
              <CFormSelect v-model="sensorEdit.draft.sensor_type" @change="onSensorTypeChange">
                <option value="">Select type</option>
                <option value="thermostat">Thermostat ⚡</option>
                <option value="temperature">Temperature</option>
                <option value="humidity">Humidity</option>
                <option value="energy">Energy</option>
                <option value="pressure">Pressure</option>
                <option value="presence">Presence / Occupancy</option>
                <option value="air_quality">Air Quality</option>
                <option value="co2">CO2</option>
                <option value="power">Power</option>
                <option value="flow">Airflow</option>
                <option value="setpoint">Setpoint</option>
                <option value="status">Status / Mode</option>
              </CFormSelect>
              <small v-if="sensorEdit.draft.sensor_type === 'thermostat'" class="se-type-hint se-type-hint--control">
                ⚡ Receives setpoint commands only. Add a separate Temperature sensor for readings.
              </small>
            </CCol>
          </CRow>
          <CRow>
            <CCol :xs="12" :sm="6">
              <CFormLabel>Unit <span class="text-danger">*</span></CFormLabel>
              <CFormSelect v-model="sensorEdit.draft.unit" :disabled="!sensorEdit.draft.sensor_type">
                <option value="">{{ sensorEdit.draft.sensor_type ? 'Select unit' : 'Select type first' }}</option>
                <option v-for="unit in getAvailableUnits(sensorEdit.draft.sensor_type)" :key="unit" :value="unit">{{ unit }}</option>
              </CFormSelect>
            </CCol>
            <CCol :xs="12" :sm="6" class="mt-3 mt-sm-0">
              <CFormLabel>External Sensor ID <span class="text-muted small">(Optional)</span></CFormLabel>
              <CFormInput v-model="sensorEdit.draft.external_sensor_id" type="text" placeholder="BMS or external ID" />
            </CCol>
          </CRow>
        </div>

        <!-- ── Location ───────────────────────────────────────── -->
        <div class="se-section">
          <div class="se-section__title">Location</div>
          <CRow>
            <CCol :xs="12" :sm="isThermostatSensor ? 6 : 4">
              <CFormLabel>Zone <span class="text-danger">*</span></CFormLabel>
              <CFormSelect :value="sensorZoneValue" @change="onSensorZoneChange" :disabled="availableZones.length === 0">
                <option value="">{{ availableZones.length === 0 ? 'No zones available' : 'Select zone' }}</option>
                <optgroup v-if="formDefinedZones.length > 0" label="This device">
                  <option v-for="z in formDefinedZones" :key="'name:' + z.name" :value="'name:' + z.name">{{ z.name }}</option>
                </optgroup>
                <optgroup v-if="topology.zones.length > 0" label="Existing">
                  <option v-for="z in topology.zones" :key="'id:' + z.id" :value="'id:' + z.id">{{ z.name }}</option>
                </optgroup>
              </CFormSelect>
            </CCol>
            <CCol :xs="12" :sm="isThermostatSensor ? 6 : 4" class="mt-3 mt-sm-0">
              <CFormLabel>Room <span class="text-muted small">(Optional)</span></CFormLabel>
              <!-- Edit mode: room has a real DB id; create mode: reference by name -->
              <CFormSelect
                :value="editMode ? sensorEdit.draft.room_id : sensorEdit.draft.room_name"
                :disabled="!sensorHasZone || roomsForSelectedZone.length === 0"
                @change="e => editMode
                  ? (sensorEdit.draft.room_id = e.target.value ? Number(e.target.value) : null)
                  : (sensorEdit.draft.room_name = e.target.value || null)"
              >
                <option value="">
                  {{ !sensorHasZone ? 'Select a zone first' : roomsForSelectedZone.length === 0 ? 'No rooms in this zone' : 'Select room' }}
                </option>
                <option v-for="r in roomsForSelectedZone" :key="r.id || r.name" :value="editMode ? r.id : r.name">{{ r.name }}</option>
              </CFormSelect>
            </CCol>
          </CRow>
        </div>

        <!-- ── Reads data ─────────────────────────────────────── -->
        <div class="se-section">
          <div class="se-section__title">Reads data</div>
          <CFormCheck
            id="sensor-sends-data"
            :model-value="isThermostatSensor ? false : sensorEdit.draft.sends_data"
            :disabled="isThermostatSensor"
            label="📡 This sensor sends readings"
            class="mb-3"
            @update:model-value="v => { if (!isThermostatSensor) { sensorEdit.draft.sends_data = v; if (!v) sensorEdit.draft.payload_path = '' } }"
          />
          <div v-if="!isThermostatSensor && sensorEdit.draft.sends_data">
            <CFormLabel>Payload Path <span class="text-muted small">(Optional)</span></CFormLabel>
            <CFormInput v-model="sensorEdit.draft.payload_path" type="text" placeholder="e.g. temperature, sensors.temp, data.value" />
            <small class="text-muted">JSON key path in the MQTT message where this sensor's value is found.</small>
          </div>
        </div>

        <!-- ── Receives commands ───────────────────────────────── -->
        <div class="se-section">
          <div class="se-section__title">Receives commands</div>
          <CFormCheck
            id="sensor-controllable"
            :model-value="isThermostatSensor ? true : sensorEdit.draft.is_controllable"
            :disabled="isThermostatSensor"
            label="⚡ This sensor can receive setpoint commands"
            class="mb-3"
            @update:model-value="v => { if (!isThermostatSensor) sensorEdit.draft.is_controllable = v }"
          />
          <div v-if="isThermostatSensor || sensorEdit.draft.is_controllable">
            <CFormLabel>Command Payload Template <span class="text-muted small">(Optional)</span></CFormLabel>
            <CFormTextarea
              v-model="sensorEdit.draft.command_payload_template"
              rows="3"
              placeholder='e.g. {"setpoint": {value}}'
              style="font-family:monospace;font-size:12px;"
            />
            <small class="text-muted">Use <code>{value}</code> as the setpoint placeholder.</small>
            <div v-if="sensorEdit.draft.command_payload_template" class="mt-2 p-2 rounded" style="background:#f0fdf4;border:1px solid #86efac;font-size:11px;">
              <strong>Preview (value = 21.5):</strong>
              <code class="d-block mt-1">{{ previewCommandPayload(sensorEdit.draft.command_payload_template) }}</code>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="d-flex gap-2 mt-2">
          <CButton color="primary" class="flex-grow-1" @click="applySensorEdit">
            <CIcon name="cilCheck" class="me-1" />Apply
          </CButton>
          <CButton color="secondary" variant="outline" @click="closeSensorEdit">Cancel</CButton>
        </div>
      </COffcanvasBody>
    </COffcanvas>


    <!-- System Topology -->
    <CRow class="mt-4 mb-4">
      <CCol>
        <CCard class="topology-embed-card">
          <CCardHeader class="topology-embed-card__header" @click="topologyOpen = !topologyOpen" style="cursor:pointer;">
            <div class="d-flex align-items-center gap-2" style="flex:1; min-width:0;">
              <span class="topology-embed-chevron" :class="{ open: topologyOpen }">&#8250;</span>
              <strong>System Topology</strong>
              <small class="ms-1 text-body-secondary">Live view of HVAC units, zones and sensors</small>
            </div>
            <button
              v-if="topologyOpen"
              class="topology-fullscreen-btn"
              title="Fullscreen"
              @click.stop="openTopologyFullscreen"
            >⤢</button>
          </CCardHeader>
          <div v-show="topologyOpen" ref="topologyWrapRef">
            <CCardBody class="p-0">
              <TopologyCanvas
                ref="topologyCanvasRef"
                :building-id="form.building_id ? Number(form.building_id) : null"
                @edit-device="onTopologyEditDevice"
                @rotate-key="onTopologyRotateKey"
                @set-setpoint="onTopologySetSetpoint"
              />
            </CCardBody>

            <!-- Setpoint overlay — inside topologyWrapRef so position:fixed roots here in fullscreen -->
            <Transition name="sp-fade">
              <div v-if="setpointCmd.show" class="sp-overlay">
                <div class="sp-backdrop" @click="closeSetpointCmd" />
                <div class="sp-panel">
                  <div class="sp-panel__header">
                    <span>⚡ Set Setpoint — {{ setpointCmd.label }}</span>
                    <button class="sp-panel__close" @click="closeSetpointCmd">&times;</button>
                  </div>
                  <div class="sp-panel__body">
                    <div class="sp-panel__topic">
                      <strong>MQTT cmd topic:</strong><br>
                      <code>{{ setpointCmd.cmdTopic }}</code>
                    </div>

                    <div class="sp-panel__toggle">
                      <CFormSwitch
                        v-model="setpointCmd.enabled"
                        size="lg"
                        :color="setpointCmd.enabled ? 'success' : 'danger'"
                      />
                      <span :class="setpointCmd.enabled ? 'sp-toggle-on' : 'sp-toggle-off'">
                        {{ setpointCmd.enabled ? 'On' : 'Off' }}
                      </span>
                    </div>

                    <SetpointSlider
                      v-model="setpointCmd.value"
                      :min="16"
                      :max="30"
                      label="Setpoint"
                      :disabled="!setpointCmd.enabled"
                    />
                    <div v-if="setpointCmd.enabled && setpointCmd.value" class="sp-panel__preview">
                      <strong>Payload that will be sent:</strong><br>
                      <code>{{ previewCommandPayload(setpointCmd.cmdTemplate.replaceAll('{value}', setpointCmd.value)) }}</code>
                    </div>
                    <div v-else-if="!setpointCmd.enabled" class="sp-panel__preview sp-panel__preview--off">
                      HVAC will be turned <strong>Off</strong> for this zone.
                    </div>
                  </div>
                  <div class="sp-panel__footer">
                    <CButton color="secondary" variant="outline" @click="closeSetpointCmd">Cancel</CButton>
                    <CButton color="warning" :disabled="setpointCmd.loading" @click="sendSetpointCmd">
                      <CSpinner v-if="setpointCmd.loading" size="sm" class="me-1" />
                      Set Setpoint
                    </CButton>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </CCard>
      </CCol>
    </CRow>
  </CContainer>
</template>

<script>
import TopologyCanvas from '@/components/topology/TopologyCanvas.vue'
import SetpointSlider from '@/components/SetpointSlider.vue'
import { useDashboardStore } from '@/stores/dashboard.js'
import { useControlStore } from '@/stores/control.js'

export default {
  name: 'DeviceRegistration',
  components: { TopologyCanvas, SetpointSlider },
  setup() {
    return { dashboardStore: useDashboardStore(), controlStore: useControlStore() }
  },
  data() {
    return {
      topologyOpen: false,
      loading: false,
      loadingDevices: false,
      buildings: [],
      existingDevices: [],
      showRegistrationForm: false,
      zonesOpen: false,
      roomsOpen: false,
      editMode: false,
      editingDeviceId: null,
      form: {
        building_id: '',
        name: '',
        unit_type: '',
        sensors: [],
        zones: [{ name: '', zone_type: '' }],
        rooms: [],
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
        loading: false,
        device_secret: '',
        copied: {},
        snippetTab: 'rest',
        techDocsOpen: false,
        confirmRotate: false,
        curlStep: 1,
        curlSensor: 0,
        pos: null,        // {x, y} when dragged, null = CSS-centered
      },
      _dragState: null,   // { startX, startY, startLeft, startTop }
      topology: {
        rooms: [],
        zones: [],
        thermostats: [],
        loading: false
      },
      sensorUnitMapping: {
        thermostat:  ['°C', '°F', 'K'],
        temperature: ['°C', '°F', 'K'],
        humidity:    ['%', 'g/kg', 'g/m³'],
        energy:      ['kWh', 'Wh', 'MWh', 'J', 'kJ', 'MJ'],
        pressure:    ['Pa', 'kPa', 'hPa', 'bar', 'mbar', 'psi', 'mmHg'],
        presence:    ['boolean', 'binary', 'occupancy', '%', 'count'],
        air_quality: ['ppm', 'µg/m³', 'mg/m³', 'AQI', '%'],
        co2:         ['ppm'],
        power:       ['W', 'kW'],
        flow:        ['m³/h', 'l/s', 'CFM'],
        setpoint:    ['°C', '°F', 'K'],
        status:      ['text', 'boolean'],
      },
      mqttConfig: {
        broker_url: '',
        broker_port: 1883,
        topic_prefix: 'qoe',
        client_id_prefix: 'qoe_device',
        use_tls: false,
        loading: false
      },
      showMQTTInfo: false,
      sensorEdit: {
        show: false,
        index: null,
        draft: {}
      },
      roomDraftName: '',
      roomDraftZoneId: '',
      roomCreateLoading: false,
      registrationPanelWidth: 720,
      isResizingRegistrationPanel: false,
      sensorPanelWidth: 460,
      isResizingSensorPanel: false,
      setpointCmd: {
        show: false,
        label: '',
        hvacUnitId: null,
        zoneId: null,
        buildingId: null,
        cmdTemplate: '',
        cmdTopic: '',
        value: 21,
        loading: false,
      }
    }
  },
  computed: {
    apiBaseUrl() {
      return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    },
    registrationPanelStyle() {
      return {
        '--cui-offcanvas-width': `${this.registrationPanelWidth}px`,
        width: `${this.registrationPanelWidth}px`,
      }
    },
    sensorPanelStyle() {
      return {
        '--cui-offcanvas-width': `${this.sensorPanelWidth}px`,
        width: `${this.sensorPanelWidth}px`,
      }
    },
    isZoneOnlyTopology() {
      return !this.topology.loading && this.topology.rooms.length === 0 && this.topology.zones.length > 0
    },
    isThermostatSensor() {
      return this.sensorEdit.draft?.sensor_type === 'thermostat'
    },
    formDefinedZones() {
      const explicit = this.form.zones.filter(z => z.name && z.name.trim())
      if (explicit.length > 0) return explicit
      // No explicit zones — surface the auto-created default so sensors can be assigned to it
      const defaultName = this.form.name?.trim() ? `${this.form.name.trim()} Zone` : 'Default Zone'
      return [{ name: defaultName }]
    },
    availableZones() {
      return [...this.formDefinedZones, ...this.topology.zones]
    },
    sensorZoneValue() {
      if (this.sensorEdit.draft?.zone_id) return `id:${this.sensorEdit.draft.zone_id}`
      if (this.sensorEdit.draft?.zone_name) return `name:${this.sensorEdit.draft.zone_name}`
      return ''
    },
    sensorHasZone() {
      return !!(this.sensorEdit.draft?.zone_id || this.sensorEdit.draft?.zone_name)
    },
    roomsForSelectedZone() {
      const zoneId = this.sensorEdit.draft?.zone_id
      const zoneName = this.sensorEdit.draft?.zone_name
      if (this.editMode) {
        return zoneId ? this.topology.rooms.filter(r => r.zone_id === zoneId) : []
      }
      return (this.form.rooms || []).filter(r =>
        (zoneId && r.zone_id === zoneId) || (zoneName && r.zone_name === zoneName)
      )
    },
    displayRooms() {
      return this.editMode ? this.topology.rooms : (this.form.rooms || [])
    },
    selectedThermostatControllable() {
      const tid = this.sensorEdit.draft?.thermostat_id
      if (!tid) return false
      return this.topology.thermostats.find(t => t.id === Number(tid))?.is_controllable ?? false
    }
  },
  watch: {
    'form.building_id'(newId) {
      this.roomDraftName = ''
      if (newId) {
        this.loadTopology(newId)
        this.dashboardStore.setSelectedBuilding(Number(newId))
      } else {
        this.topology.rooms = []
        this.topology.zones = []
        this.topology.thermostats = []
      }
    }
  },
  mounted() {
    console.log('DeviceRegistration mounted, API Base URL:', this.apiBaseUrl)
    this.loadBuildings()
    this.loadExistingDevices()
    // Don't start with sensors by default anymore - only when editing or user adds
  },
  beforeUnmount() {
    this.stopRegistrationResize()
    this.stopSensorResize()
  },
  methods: {
    openTopologyFullscreen() {
      const el = this.$refs.topologyWrapRef
      if (!el) return
      const req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen
      if (req) req.call(el)
    },
    clampRegistrationPanelWidth(width) {
      const viewportWidth = globalThis.innerWidth || 1280
      const maxWidth = Math.max(560, Math.min(1080, viewportWidth - 24))
      return Math.min(Math.max(width, 560), maxWidth)
    },

    startRegistrationResize(event) {
      this.isResizingRegistrationPanel = true
      this.updateRegistrationPanelWidthFromEvent(event)
      globalThis.addEventListener('mousemove', this.handleRegistrationResize)
      globalThis.addEventListener('mouseup', this.stopRegistrationResize)
      globalThis.addEventListener('touchmove', this.handleRegistrationResize, { passive: false })
      globalThis.addEventListener('touchend', this.stopRegistrationResize)
    },

    handleRegistrationResize(event) {
      if (!this.isResizingRegistrationPanel) return
      if (event.cancelable) event.preventDefault()
      this.updateRegistrationPanelWidthFromEvent(event)
    },

    updateRegistrationPanelWidthFromEvent(event) {
      const point = event.touches?.[0] || event
      if (!point || typeof point.clientX !== 'number') return
      const nextWidth = (globalThis.innerWidth || 0) - point.clientX
      this.registrationPanelWidth = this.clampRegistrationPanelWidth(nextWidth)
    },

    stopRegistrationResize() {
      this.isResizingRegistrationPanel = false
      globalThis.removeEventListener('mousemove', this.handleRegistrationResize)
      globalThis.removeEventListener('mouseup', this.stopRegistrationResize)
      globalThis.removeEventListener('touchmove', this.handleRegistrationResize)
      globalThis.removeEventListener('touchend', this.stopRegistrationResize)
    },

    clampSensorPanelWidth(width) {
      const viewportWidth = globalThis.innerWidth || 1280
      const maxWidth = Math.max(360, Math.min(760, viewportWidth - 24))
      return Math.min(Math.max(width, 360), maxWidth)
    },

    startSensorResize(event) {
      this.isResizingSensorPanel = true
      this.updateSensorPanelWidthFromEvent(event)
      globalThis.addEventListener('mousemove', this.handleSensorResize)
      globalThis.addEventListener('mouseup', this.stopSensorResize)
      globalThis.addEventListener('touchmove', this.handleSensorResize, { passive: false })
      globalThis.addEventListener('touchend', this.stopSensorResize)
    },

    handleSensorResize(event) {
      if (!this.isResizingSensorPanel) return
      if (event.cancelable) event.preventDefault()
      this.updateSensorPanelWidthFromEvent(event)
    },

    updateSensorPanelWidthFromEvent(event) {
      const point = event.touches?.[0] || event
      if (!point || typeof point.clientX !== 'number') return
      const nextWidth = (globalThis.innerWidth || 0) - point.clientX
      this.sensorPanelWidth = this.clampSensorPanelWidth(nextWidth)
    },

    stopSensorResize() {
      this.isResizingSensorPanel = false
      globalThis.removeEventListener('mousemove', this.handleSensorResize)
      globalThis.removeEventListener('mouseup', this.stopSensorResize)
      globalThis.removeEventListener('touchmove', this.handleSensorResize)
      globalThis.removeEventListener('touchend', this.stopSensorResize)
    },

    async loadTopology(buildingId) {
      this.topology.loading = true
      try {
        const jwtToken = this.getJwtToken()
        const response = await fetch(`${this.apiBaseUrl}/buildings/${buildingId}/topology`, {
          headers: {
            'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        })
        if (!response.ok) throw new Error('Failed to fetch topology')
        const data = await response.json()
        this.topology.rooms = data.rooms || []
        this.topology.zones = data.zones || []
        this.topology.thermostats = data.thermostats || []
      } catch (error) {
        console.error('Failed to load building topology:', error)
        this.topology.rooms = []
        this.topology.zones = []
        this.topology.thermostats = []
      } finally {
        this.topology.loading = false
      }
    },

    async loadBuildings() {
      try {
        const jwtToken = this.getJwtToken()
        console.log('[loadBuildings] JWT Token:', jwtToken)
        const headers = {
          'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
          'Content-Type': 'application/json'
        }
        console.log('[loadBuildings] Headers:', headers)
        const response = await fetch(`${this.apiBaseUrl}/buildings/`, {
          headers,
          credentials: 'include'
        })
        if (!response.ok) throw new Error('Failed to fetch buildings')
        this.buildings = await response.json()
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
        const jwtToken = this.getJwtToken()
        console.log('[loadExistingDevices] JWT Token:', jwtToken)
        const headers = {
          'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
          'Content-Type': 'application/json'
        }
        console.log('[loadExistingDevices] Headers:', headers)
        const response = await fetch(`${this.apiBaseUrl}/devices/`, {
          headers,
          credentials: 'include'
        })
        if (!response.ok) throw new Error('Failed to fetch devices')
        const devices = await response.json()
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
        const jwtToken = this.getJwtToken()
        const response = await fetch(`${this.apiBaseUrl}/mqtt/config`, {
          headers: {
            'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        })
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
      if (this.showRegistrationForm) {
        this.closeRegistrationForm()
        return
      }
      this.resetForm()
      this.showRegistrationForm = true
    },

    closeRegistrationForm() {
      this.showRegistrationForm = false
      this.closeSensorEdit()
      this.resetForm()
    },

    onSensorTypeChange() {
      if (this.sensorEdit.draft.sensor_type === 'thermostat') {
        // Thermostat is a controllable temperature sensor — store the measurement type
        this.sensorEdit.draft.sensor_type = 'temperature'
        this.sensorEdit.draft.is_controllable = true
        this.sensorEdit.draft.unit = '°C'
        if (!this.sensorEdit.draft.command_payload_template) {
          this.sensorEdit.draft.command_payload_template = '{"setpoint": {value}}'
        }
      }
    },

    previewCommandPayload(template) {
      if (!template) return ''
      try {
        const rendered = template.replaceAll('{value}', '21.5')
        JSON.parse(rendered)
        return rendered
      } catch {
        return '⚠ Invalid JSON template'
      }
    },

    onTopologyEditDevice(unitId) {
      const device = this.existingDevices.find(d => d.id === unitId)
      if (device) this.editDevice(device)
    },

    onTopologyRotateKey(unitId) {
      const device = this.existingDevices.find(d => d.id === unitId)
      if (device) this.rotateDeviceKey(device)
    },

    async onTopologySetSetpoint(sensorData) {
      const device = this.existingDevices.find(d => d.id === sensorData.hvac_unit_id)
      const deviceKey = device?.device_key || '...'
      const buildingId = device?.building_id || null
      const zoneId = sensorData.zone_id ?? null

      // Start with in-memory value as fallback
      let initialValue = Math.min(30, Math.max(16, this.controlStore.getZoneSetpoint(zoneId) ?? sensorData.setpoint ?? 21))

      // Fetch the most current setpoint from DB — survives page reloads and schedule deletions
      if (buildingId && sensorData.hvac_unit_id && zoneId) {
        try {
          const params = new URLSearchParams()
          params.set('unit_id', String(sensorData.hvac_unit_id))
          params.set('zone_id', String(zoneId))
          const res = await fetch(`${this.apiBaseUrl}/dashboard/hvac-schedule/${buildingId}?${params}`, {
            headers: { Authorization: `Bearer ${this.getJwtToken()}` },
            credentials: 'include',
          })
          if (res.ok) {
            const data = await res.json()
            // Sync the current DB schedule into the store so sendSetpointCmd only
            // updates the setpoint on existing rows, never creates phantom rows.
            if (data.rows) this.controlStore.setRawSchedule(data.rows)
            const firstEnabled = (data.rows || []).find(r => r.enabled && r.setpoint != null)
            if (firstEnabled) {
              initialValue = Math.min(30, Math.max(16, firstEnabled.setpoint))
            }
          }
        } catch { /* silent fallback to in-memory value */ }
      }

      const friendlyName = sensorData.thermostat_name
        || (sensorData.sensor_type || 'Sensor').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
      this.setpointCmd = {
        show: true,
        label: sensorData.zone_name ? `${sensorData.zone_name} — ${friendlyName}` : friendlyName,
        hvacUnitId: sensorData.hvac_unit_id,
        zoneId,
        buildingId,
        cmdTemplate: sensorData.command_payload_template || '{"setpoint": {value}}',
        cmdTopic: `building/${buildingId}/device/${deviceKey}/cmd`,
        value: initialValue,
        enabled: true,
        loading: false,
      }
    },

    closeSetpointCmd() {
      this.setpointCmd.show = false
      this.setpointCmd.value = 21
      this.setpointCmd.loading = false
    },

    async sendSetpointCmd() {
      const { hvacUnitId, zoneId, buildingId, cmdTemplate, value, label } = this.setpointCmd
      const parsed = Number.parseFloat(value)
      if (Number.isNaN(parsed)) {
        this.showAlert('danger', 'Please enter a valid number.')
        return
      }
      let cmdPayload
      try {
        cmdPayload = JSON.parse(cmdTemplate.replaceAll('{value}', String(parsed)))
      } catch {
        this.showAlert('danger', 'Command template is not valid JSON.')
        return
      }
      this.setpointCmd.loading = true
      try {
        // 1. Persist updated setpoint — preserves schedule structure (times, enabled),
        //    only patches the setpoint value on enabled rows.
        if (buildingId) {
          await this.controlStore.saveSetpointToSchedule({
            buildingId,
            unitId: hvacUnitId,
            zoneId,
            value: parsed,
          })
        }

        // 2. Send immediate command to device via MQTT cmd topic
        const res = await fetch(`${this.apiBaseUrl}/devices/${hvacUnitId}/command`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${this.getJwtToken()}`, 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ command_type: 'set_setpoint', payload: cmdPayload }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || `HTTP ${res.status}`)
        }
        this.closeSetpointCmd()
        this.showAlert('success', `Setpoint ${parsed}°C sent to "${label}".`)
        this.$refs.topologyCanvasRef?.load()
      } catch (e) {
        this.showAlert('danger', e.message || 'Failed to send setpoint.')
      } finally {
        this.setpointCmd.loading = false
      }
    },

    async editDevice(device) {
      this.closeSensorEdit()
      this.editMode = true
      this.editingDeviceId = device.id
      this.showRegistrationForm = true
      this.form.building_id = device.building_id
      this.form.name = device.name || ''
      this.form.unit_type = device.unit_type || ''
      try {
        const jwtToken = this.getJwtToken()
        const response = await fetch(`${this.apiBaseUrl}/devices/${device.id}/sensors`, {
          headers: {
            'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        })
        if (response.ok) {
          const sensors = await response.json()
          this.form.sensors = sensors.map(s => ({
            ...s,
            zone_id: s.zone_id ?? null,
            room_id: s.room_id ?? null,
            thermostat_id: s.thermostat_id ?? null,
          }))
        } else {
          this.form.sensors = []
        }
      } catch (error) {
        console.error('Failed to load sensors for editing:', error)
        this.form.sensors = []
      }
      this.loadTopology(device.building_id)
      this.showAlert('info', `Editing device: ${device.building_name}. Update details below.`)
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
        const jwtToken = this.getJwtToken()
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
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
        this.credentials.device_key = newCredentials.device_key
        this.credentials.device_secret = newCredentials.device_secret
        this.credentials.title = 'Device Key Rotated Successfully!'
        this.credentials.isRotation = true
        console.log('About to show modal, credentials.show will be:', true)
        await this.$nextTick()
        this.credentials.show = true
        console.log('Modal show state set to:', this.credentials.show)
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
      this.closeRegistrationForm()
    },

    async viewDeviceDetails(device) {
      console.log('View details for device:', device)
      this.deviceDetails.device = device
      this.deviceDetails.sensors = []
      this.deviceDetails.loading = true
      this.deviceDetails.show = true
      try {
        const jwtToken = this.getJwtToken()
        const response = await fetch(`${this.apiBaseUrl}/devices/${device.id}/sensors`, {
          headers: {
            'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        })
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

    startDetailsDrag(e) {
      const win = e.currentTarget.closest('.dd-window')
      const rect = win.getBoundingClientRect()
      this._dragState = { ox: e.clientX - rect.left, oy: e.clientY - rect.top }
      if (!this.deviceDetails.pos) {
        this.deviceDetails.pos = { x: rect.left, y: rect.top }
      }
      const onMove = (me) => {
        this.deviceDetails.pos = {
          x: Math.max(0, Math.min(window.innerWidth - rect.width, me.clientX - this._dragState.ox)),
          y: Math.max(0, Math.min(window.innerHeight - 60, me.clientY - this._dragState.oy)),
        }
      }
      const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
        this._dragState = null
      }
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    },

    closeDeviceDetails() {
      this.deviceDetails.show = false
      this.deviceDetails.pos = null
      this.deviceDetails.device = null
      this.deviceDetails.sensors = []
      this.deviceDetails.loading = false
      this.deviceDetails.device_secret = ''
      this.deviceDetails.copied = {}
      this.deviceDetails.snippetTab = 'rest'
      this.deviceDetails.techDocsOpen = false
      this.deviceDetails.confirmRotate = false
      this.deviceDetails.curlStep = 1
      this.deviceDetails.curlSensor = 0
    },

    async confirmAndRotate() {
      this.deviceDetails.confirmRotate = false
      await this.rotateKeyInDetails()
    },

    async rotateKeyInDetails() {
      const device = this.deviceDetails.device
      if (!device) return
      this.loading = true
      try {
        const jwtToken = this.getJwtToken()
        const response = await fetch(`${this.apiBaseUrl}/devices/${device.id}/credentials/upsert`, {
          method: 'POST',
          headers: {
            'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({}),
        })
        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          throw new Error(err.detail || 'Failed to rotate key')
        }
        const creds = await response.json()
        this.deviceDetails.device_secret = creds.device_secret
        this.deviceDetails.device = { ...this.deviceDetails.device, device_key: creds.device_key }
        await this.loadExistingDevices()
      } catch (error) {
        this.showAlert('danger', error.message || 'Failed to rotate key.')
      } finally {
        this.loading = false
      }
    },

    buildSimulatorSnippet(mode) {
      const d = this.deviceDetails.device
      const sensors = this.deviceDetails.sensors
      if (!d) return ''
      const secret = this.deviceDetails.device_secret
      const secretVal = secret ? `"${secret}"` : `""  # click "Rotate & Reveal Secret" above`
      const buildingId = d.building_id
      const pad = (s, len) => s + ' '.repeat(Math.max(0, len - s.length))

      const _SIM_RANGE = {
        temperature: '18.0 – 28.0 °C  (float)',
        humidity:    '30.0 – 70.0 %   (float)',
        energy:      '0.5  – 5.0  kWh (float)',
        power:       '100  – 3000 W   (float)',
        current:     '0.5  – 15.0 A   (float)',
        voltage:     '220  – 240  V   (float)',
        presence:    'True / False    (bool)',
      }

      const sensorLines = sensors.map(s => {
        const pathVal = s.payload_path || s.sensor_type
        const unit = s.unit || ''
        const name = s.name || ''
        const simHint = _SIM_RANGE[s.sensor_type] || '0 – 100 (float)'
        if (mode === 'mqtt') {
          return `    {"id": ${s.id}, "name": "${name}", "sensor_type": "${s.sensor_type}", "unit": "${unit}", "building_id": ${buildingId}, "payload_path": "${pathVal}"},  # simulated: ${simHint}`
        }
        return `    {"id": ${s.id}, "name": "${name}", "sensor_type": "${s.sensor_type}", "unit": "${unit}", "building_id": ${buildingId}},  # simulated: ${simHint}`
      }).join('\n')

      if (mode === 'mqtt') {
        return [
          `# ── ${d.name} — MQTT Notebook config ────────────────────────`,
          `${pad('API_BASE', 13)}= "http://localhost:8000"`,
          `${pad('MQTT_HOST', 13)}= "localhost"`,
          `${pad('MQTT_PORT', 13)}= 1883`,
          `${pad('DEVICE_KEY', 13)}= "${d.device_key}"`,
          `${pad('DEVICE_SECRET', 13)}= ${secretVal}`,
          `${pad('ORG_ID', 13)}= 1`,
          `${pad('BUILDING_ID', 13)}= ${buildingId}`,
          `SENSORS = [`,
          sensorLines,
          `]`,
        ].join('\n')
      }

      return [
        `# ── ${d.name} — REST Notebook config ─────────────────────────`,
        `${pad('API_BASE', 13)}= "http://localhost:8000"`,
        `${pad('DEVICE_ID', 13)}= ${d.id}`,
        `${pad('DEVICE_KEY', 13)}= "${d.device_key}"`,
        `${pad('DEVICE_SECRET', 13)}= ${secretVal}`,
        `${pad('BUILDING_ID', 13)}= ${buildingId}`,
        `SENSORS = [`,
        sensorLines,
        `]`,
      ].join('\n')
    },

    sensorSimRange(sensorType) {
      const ranges = {
        temperature: '18.0 – 28.0 °C',
        humidity:    '30.0 – 70.0 %',
        energy:      '0.5 – 5.0 kWh',
        power:       '100 – 3000 W',
        current:     '0.5 – 15.0 A',
        voltage:     '220 – 240 V',
        presence:    'True / False',
      }
      return ranges[sensorType] || 'random 0 – 100'
    },

    _sensorSampleValue(sensorType) {
      const samples = {
        temperature: '24.7',
        humidity:    '52.3',
        energy:      '1.842',
        power:       '1450.0',
        current:     '6.5',
        voltage:     '231.0',
      }
      return samples[sensorType] ?? '42.0'
    },

    buildCurlAuth() {
      const d = this.deviceDetails.device
      if (!d) return ''
      const secret = this.deviceDetails.device_secret || 'YOUR_DEVICE_SECRET'
      return `DEVICE_JWT=$(curl -s -X POST ${this.apiBaseUrl}/auth/device/auth \\
  -H "Content-Type: application/json" \\
  -d '{"device_key": "${d.device_key}", "device_secret": "${secret}"}' \\
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")`
    },

    buildCurlSingle(sensor) {
      const d = this.deviceDetails.device
      if (!d) return ''
      const ts = new Date().toISOString().replace(/\.\d{3}Z$/, '+00:00')
      const isPresence = sensor.sensor_type === 'presence'
      const valueField = isPresence
        ? `"value_bool": true`
        : `"value":      ${this._sensorSampleValue(sensor.sensor_type)}`
      return `# ${sensor.name || sensor.sensor_type} (id=${sensor.id})
curl -X POST ${this.apiBaseUrl}/sensordata/ \\
  -H "Authorization: Bearer $DEVICE_JWT" \\
  -H "Content-Type: application/json" \\
  -d '{
    "sensor_id":   ${sensor.id},
    "building_id": ${d.building_id},
    "ts":          "${ts}",
    "quality":     "valid",
    ${valueField}
  }'`
    },

    buildCurlBulk() {
      const d = this.deviceDetails.device
      const sensors = this.deviceDetails.sensors
      if (!d || !sensors.length) return ''
      const ts = new Date().toISOString().replace(/\.\d{3}Z$/, '+00:00')
      const rows = sensors.map(s => {
        const isPresence = s.sensor_type === 'presence'
        const valueField = isPresence
          ? `"value_bool": true`
          : `"value": ${this._sensorSampleValue(s.sensor_type)}`
        return `    {"sensor_id": ${s.id}, "building_id": ${d.building_id}, "ts": "${ts}", "quality": "valid", ${valueField}}`
      }).join(',\n')
      return `curl -X POST ${this.apiBaseUrl}/sensordata/bulk \\
  -H "Authorization: Bearer $DEVICE_JWT" \\
  -H "Content-Type: application/json" \\
  -d '[
${rows}
  ]'`
    },

    buildMosquittoCmd(sensor) {
      const d = this.deviceDetails.device
      if (!d) return ''
      const ts = new Date().toISOString().replace(/\.\d{3}Z$/, '+00:00')
      const isPresence = sensor.sensor_type === 'presence'
      const valueField = isPresence ? '"value_bool": true' : `"value": ${this._sensorSampleValue(sensor.sensor_type)}`
      const payload = `{"sensor_id": ${sensor.id}, "building_id": ${d.building_id}, "ts": "${ts}", "quality": "valid", ${valueField}}`
      return `# ${sensor.name || sensor.sensor_type} (id=${sensor.id})
mosquitto_pub -h localhost -p 1883 \\
  -u "${d.device_key}" -P "${this.deviceDetails.device_secret || 'YOUR_DEVICE_SECRET'}" \\
  -t "device/${d.device_key}/data" \\
  -m '${payload}'`
    },

    addSensorsToDevice(device) {
      // Pre-fill form with device info to add sensors
      const building = this.buildings.find(b => b.id === device.building_id)
      if (building) {
        this.form.building_id = device.building_id
        this.form.name = device.name || ''
        this.form.unit_type = device.unit_type || ''
        this.form.sensors = [] // Clear sensors to add new ones
        this.addSensor()
        
        this.showAlert('info', `Form pre-filled with ${device.building_name} device info. Add sensors below.`)
        
        // Scroll to form
        document.querySelector('form').scrollIntoView({ behavior: 'smooth' })
      }
    },

    addZone() {
      this.form.zones.push({ name: '', zone_type: '' })
    },

    removeZone(index) {
      this.form.zones.splice(index, 1)
      // Clear zone_name on sensors that referenced the removed zone
      const removedName = this.form.zones[index]?.name
      if (removedName) {
        this.form.sensors.forEach(s => {
          if (s.zone_name === removedName) s.zone_name = null
        })
      }
    },

    addSensor() {
      this.form.sensors.push({
        name: '',
        sensor_type: '',
        unit: '',
        payload_path: '',
        sends_data: true,
        external_sensor_id: '',
        room_id: null,
        zone_id: null,
        zone_name: null,
        thermostat_id: null,
        is_controllable: true,
        command_payload_template: '',
      })
      // Open the sidebar immediately for the newly added sensor
      this.openSensorEdit(this.form.sensors.length - 1)
    },

    openSensorEdit(index) {
      this.sensorEdit.index = index
      const base = { ...this.form.sensors[index] }
      // sends_data is UI-only: true when the sensor has a payload path or is not a thermostat
      if (base.sends_data === undefined) {
        base.sends_data = base.sensor_type !== 'thermostat' && !base.is_controllable
      }
      this.sensorEdit.draft = this.normalizeSensorTopology(base)
      // Always pre-select zone when none is set — prevents orphaned sensors in both create and edit mode
      if (!this.sensorEdit.draft.zone_id && !this.sensorEdit.draft.zone_name) {
        const first = this.formDefinedZones[0] || this.topology.zones[0]
        if (first?.id) this.sensorEdit.draft.zone_id = first.id
        else if (first?.name) this.sensorEdit.draft.zone_name = first.name
      }
      this.sensorEdit.show = true
    },

    closeSensorEdit() {
      this.sensorEdit.show = false
      this.sensorEdit.index = null
      this.sensorEdit.draft = {}
    },

    onSensorZoneChange(e) {
      const val = e.target.value
      if (val.startsWith('name:')) {
        this.sensorEdit.draft.zone_name = val.slice(5)
        this.sensorEdit.draft.zone_id = null
      } else if (val.startsWith('id:')) {
        this.sensorEdit.draft.zone_id = Number(val.slice(3))
        this.sensorEdit.draft.zone_name = null
      } else {
        this.sensorEdit.draft.zone_name = null
        this.sensorEdit.draft.zone_id = null
      }
      this.sensorEdit.draft.room_id = null
    },

    async applySensorEdit() {
      // Capture draft BEFORE closeSensorEdit() clears it
      const draft = { ...this.sensorEdit.draft }
      if (!draft.zone_id && !draft.zone_name) {
        this.showAlert('warning', 'Please select a zone for this sensor.')
        return
      }
      if (this.sensorEdit.index !== null) {
        Object.assign(this.form.sensors[this.sensorEdit.index], this.normalizeSensorTopology(draft))
      }
      this.closeSensorEdit()
      // Immediately upsert thermostat to DB so the dropdown is populated for the next sensor
      const buildingId = this.form.building_id
      if (draft.is_controllable && draft.name && buildingId) {
        try {
          await fetch(`${this.apiBaseUrl}/buildings/${buildingId}/thermostats`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${this.getJwtToken()}` },
            credentials: 'include',
            body: JSON.stringify({ name: draft.name, is_controllable: true }),
          })
          await this.loadTopology(buildingId)
        } catch { /* non-critical — thermostat will be created on full device save anyway */ }
      }
    },

    normalizeSensorTopology(sensor) {
      if (!this.editMode) return sensor

      const normalized = { ...sensor }
      const roomIds = new Set(this.topology.rooms.map(room => Number(room.id)))
      const zoneIds = new Set(this.topology.zones.map(zone => Number(zone.id)))
      const thermostatIds = new Set(this.topology.thermostats.map(thermostat => Number(thermostat.id)))

      const roomId = normalized.room_id == null ? null : Number(normalized.room_id)
      const zoneId = normalized.zone_id == null ? null : Number(normalized.zone_id)
      const thermostatId = normalized.thermostat_id == null ? null : Number(normalized.thermostat_id)

      normalized.room_id = roomId != null && roomIds.has(roomId) ? roomId : null
      normalized.zone_id = zoneId != null && zoneIds.has(zoneId) ? zoneId : null
      normalized.thermostat_id = thermostatId != null && thermostatIds.has(thermostatId) ? thermostatId : null

      return normalized
    },

    async removeSensor(index) {
      const sensor = this.form.sensors[index]
      if (this.editMode && sensor?.id) {
        if (!confirm(`Delete sensor "${sensor.name || sensor.sensor_type}"? This cannot be undone.`)) return
        try {
          const res = await fetch(`${this.apiBaseUrl}/devices/${this.editingDeviceId}/sensors/${sensor.id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${this.getJwtToken()}` },
            credentials: 'include',
          })
          if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            this.showAlert('danger', err.detail || 'Failed to delete sensor.')
            return
          }
          this.$refs.topologyCanvasRef?.load()
        } catch {
          this.showAlert('danger', 'Failed to delete sensor.')
          return
        }
      }
      this.form.sensors.splice(index, 1)
      this.showAlert('success', 'Sensor deleted.')
    },

    async deleteDevice(device) {
      if (!confirm(`Delete device "${device.name}"? All its sensors will be permanently removed.`)) return
      try {
        const res = await fetch(`${this.apiBaseUrl}/devices/${device.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${this.getJwtToken()}` },
          credentials: 'include',
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          this.showAlert('danger', err.detail || 'Failed to delete device.')
          return
        }
        this.showAlert('success', `Device "${device.name}" deleted.`)
        await this.loadExistingDevices()
        this.$refs.topologyCanvasRef?.load()
      } catch {
        this.showAlert('danger', 'Failed to delete device.')
      }
    },

    // Validation helper methods
    validateDeviceForm() {
      if (!this.form.building_id) {
        this.showAlert('warning', 'Please select a building.')
        return false
      }
      if (!this.form.name || !this.form.name.trim()) {
        this.showAlert('warning', 'Please enter a device name.')
        return false
      }
      if (!this.form.unit_type) {
        this.showAlert('warning', 'Please select a unit type.')
        return false
      }
      return true
    },

    validateSensorsForm() {
      for (let i = 0; i < this.form.sensors.length; i++) {
        const sensor = this.form.sensors[i]
        if (!sensor.name || !sensor.name.trim()) {
          this.showAlert('warning', `Please enter a name for Sensor ${i + 1}.`)
          return false
        }
        if (!sensor.sensor_type || !sensor.unit) {
          this.showAlert('warning', `Please fill all required fields for Sensor ${i + 1} (type and unit).`)
          return false
        }
      }
      return true
    },

    prepareSensorPayload() {
      // Sensors with no explicit zone auto-map to the device's default zone in create mode
      const defaultZoneName = !this.editMode && this.form.name?.trim()
        ? `${this.form.name.trim()} Zone`
        : null
      return this.form.sensors.map(sensor => {
        const fallbackZoneName = sensor.zone_name || (sensor.zone_id ? null : defaultZoneName)
        return {
          name: sensor.name.trim(),
          sensor_type: sensor.sensor_type,
          unit: sensor.unit || null,
          payload_path: sensor.payload_path || null,
          external_sensor_id: sensor.external_sensor_id || null,
          room_id: Number.isInteger(sensor.room_id) ? sensor.room_id : null,
          room_name: !this.editMode && sensor.room_name ? sensor.room_name : null,
          zone_id: sensor.zone_id || null,
          zone_name: this.editMode ? null : fallbackZoneName,
          thermostat_id: sensor.thermostat_id || null,
          is_controllable: sensor.sensor_type === 'thermostat' ? true : (sensor.is_controllable || false),
          command_payload_template: sensor.command_payload_template || null,
        }
      })
    },

    buildDevicePayload(cleanedSensors) {
      const payload = {
        building_id: Number.parseInt(this.form.building_id),
        name: this.form.name.trim(),
        unit_type: this.form.unit_type,
        sensors: cleanedSensors.length > 0 ? cleanedSensors : null
      }
      // Only send zones and rooms on create — edit doesn't modify zone topology
      if (!this.editMode) {
        const definedZones = this.form.zones
          .filter(z => z.name && z.name.trim())
          .map(z => ({ name: z.name.trim(), zone_type: z.zone_type || null }))
        payload.zones = definedZones.length > 0 ? definedZones : null
        const definedRooms = (this.form.rooms || [])
          .filter(r => r.name && r.name.trim())
          .map(r => ({ name: r.name.trim(), zone_name: r.zone_name || null }))
        payload.rooms = definedRooms.length > 0 ? definedRooms : null
      }
      return payload
    },

    async makeDeviceApiCall(payload) {
      const url = this.editMode 
        ? `${this.apiBaseUrl}/devices/${this.editingDeviceId}`
        : `${this.apiBaseUrl}/devices/register`
      const method = this.editMode ? 'PUT' : 'POST'
      const jwtToken = this.getJwtToken()
      return await fetch(url, {
        method,
        headers: {
          'Authorization': jwtToken ? `Bearer ${jwtToken}` : '',
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      })
    },
    getJwtToken() {
      try {
        // Dynamically import to avoid circular dependencies
        const authStore = globalThis.$authStore || null
        if (authStore && typeof authStore.getJwtToken === 'function') {
          return authStore.getJwtToken()
        }
        // Fallback: try localStorage
        const token = localStorage.getItem('jwtToken')
        return token || null
      } catch (error) {
        console.warn('Could not get JWT token:', error)
        return null
      }
    },

    async parseApiError(response) {
      const errorResponse = await response.text()

      if (response.status === 401) {
        return 'Authentication required. Please log in again.'
      }

      if (response.status === 403) {
        return 'Your current role does not have permission to manage devices or sensors.'
      }

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

    createRoom() {
      const roomName = this.roomDraftName.trim()
      if (!roomName) return

      if (this.editMode) {
        // Edit mode: existing building → create room in DB immediately
        const buildingId = Number.parseInt(this.form.building_id)
        this.roomCreateLoading = true
        const zoneId = (this.roomDraftZoneId && !String(this.roomDraftZoneId).startsWith('name:'))
          ? Number(this.roomDraftZoneId) : null
        fetch(`${this.apiBaseUrl}/buildings/${buildingId}/rooms`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${this.getJwtToken()}`, 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ name: roomName, zone_id: zoneId }),
        }).then(async r => {
          if (!r.ok) throw new Error(await this.parseApiError(r))
          this.roomDraftName = ''
          await this.loadTopology(buildingId)
          this.showAlert('success', `Room "${roomName}" added.`)
        }).catch(e => {
          this.showAlert('danger', e.message || 'Failed to create room.')
        }).finally(() => { this.roomCreateLoading = false })
        return
      }

      // Create mode: store locally — only committed to DB on device save
      const zoneName = String(this.roomDraftZoneId).startsWith('name:')
        ? this.roomDraftZoneId.slice(5) : null
      const zoneId = (!zoneName && this.roomDraftZoneId) ? Number(this.roomDraftZoneId) : null
      this.form.rooms = [...(this.form.rooms || []), { name: roomName, zone_name: zoneName, zone_id: zoneId }]
      this.roomDraftName = ''
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
      this.$refs.topologyCanvasRef?.load()
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
        name: '',
        unit_type: '',
        sensors: [],
        zones: [{ name: '', zone_type: '' }]
      }
      this.roomDraftName = ''
      this.roomCreateLoading = false
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

    setTransientCopyState(storeName, copyType, duration = 2000) {
      if (!copyType) return

      if (storeName === 'deviceDetails.copied') {
        this.deviceDetails.copied = { ...this.deviceDetails.copied, [copyType]: true }
        setTimeout(() => {
          this.deviceDetails.copied = { ...this.deviceDetails.copied, [copyType]: false }
        }, duration)
        return
      }

      this[storeName] = { ...this[storeName], [copyType]: true }
      setTimeout(() => {
        this[storeName] = { ...this[storeName], [copyType]: false }
      }, duration)
    },

    markCopyState(copyType) {
      if (!copyType) return

      if (copyType === 'brokerUrl' || copyType === 'brokerPort') {
        this.setTransientCopyState('mqttCopyState', copyType)
        return
      }

      if (copyType === 'deviceId' || copyType === 'buildingId' || copyType === 'secret' || copyType === 'snippet' || copyType === 'curlAuth' || copyType === 'curlSingle' || copyType === 'curlBulk' || copyType === 'mqttCmd' || copyType.startsWith('sensor_')) {
        this.setTransientCopyState('deviceDetails.copied', copyType)
        return
      }

      this.setTransientCopyState('copyState', copyType)

      if (copyType === 'deviceKey') {
        this.setTransientCopyState('deviceDetails.copied', copyType)
      }
    },

    // Clipboard helper methods
    copyToClipboard(text, copyType = null) {
      if (!text) return
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
      this.markCopyState(copyType)
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
.installed-devices-panel {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.installed-devices-panel__header {
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
  border-bottom: 1px solid rgba(19, 34, 56, 0.08);
  color: #132238;
}

.installed-devices-panel__header small {
  color: #475569;
}

.installed-devices-panel :deep(.card-body) {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
}

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
    radial-gradient(circle at top right, rgba(111, 66, 193, 0.08), transparent 32%),
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

.device-registration-panel {
  position: relative;
  width: min(var(--cui-offcanvas-width, 720px), calc(100vw - 12px));
  min-width: 560px;
  max-width: calc(100vw - 12px);
  border-left: 1px solid rgba(37, 99, 235, 0.12);
  border-top-left-radius: 24px;
  border-bottom-left-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.10), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.99) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow:
    -28px 0 60px rgba(15, 23, 42, 0.16),
    -10px 0 24px rgba(59, 130, 246, 0.08),
    -2px 0 0 rgba(255, 255, 255, 0.55);
  overflow: hidden;
}

.device-registration-resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  width: 12px;
  height: 100%;
  cursor: ew-resize;
  z-index: 3;
}

.device-registration-resize-handle::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 3px;
  transform: translateY(-50%);
  width: 4px;
  height: 64px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.24);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.5);
}

.device-registration-panel::after,
.sensor-edit-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-top-left-radius: 24px;
  border-bottom-left-radius: 24px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.device-registration-panel :deep(.offcanvas-header) {
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
  box-shadow: inset 0 -1px 0 rgba(19, 34, 56, 0.06);
}

.device-registration-panel :deep(.offcanvas-body) {
  padding: 1.25rem;
  overflow-y: auto;
  background:
    radial-gradient(circle at top right, rgba(148, 163, 184, 0.12), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
}

.device-registration-panel :deep(.form-control),
.device-registration-panel :deep(.form-select),
.device-registration-panel :deep(.btn) {
  border-radius: 12px;
}

.registration-form-shell > .mb-3,
.registration-form-shell > .mb-4:not(.registration-sensors-section) {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 18px;
  padding: 1rem 1rem 0.25rem;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.06), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

.registration-sensors-section {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 18px;
  padding: 1rem;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.06), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.06);
}

.registration-empty-state {
  border: 1px dashed rgba(71, 85, 105, 0.28);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.8);
}

/* Sensor edit right sidebar */
.sensor-edit-panel {
  position: relative;
  width: min(var(--cui-offcanvas-width, 460px), calc(100vw - 12px));
  min-width: 360px;
  max-width: calc(100vw - 12px);
  border-left: 1px solid rgba(37, 99, 235, 0.12);
  border-top-left-radius: 24px;
  border-bottom-left-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.16), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.995) 0%, rgba(244, 248, 255, 0.985) 100%);
  box-shadow:
    -34px 0 72px rgba(15, 23, 42, 0.22),
    -14px 0 32px rgba(59, 130, 246, 0.14),
    -2px 0 0 rgba(255, 255, 255, 0.55);
  overflow: hidden;
}

.sensor-edit-panel::before {
  content: '';
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: 0;
  width: 10px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.85) 0%, rgba(96, 165, 250, 0.35) 100%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.4),
    0 0 20px rgba(59, 130, 246, 0.22);
  z-index: 2;
}

.sensor-edit-resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  width: 16px;
  height: 100%;
  cursor: ew-resize;
  z-index: 4;
}

.sensor-edit-resize-handle::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 6px;
  transform: translateY(-50%);
  width: 4px;
  height: 56px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.2);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.55);
}

.sensor-edit-panel :deep(.offcanvas-header) {
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.18), transparent 34%),
    linear-gradient(90deg, rgba(219, 234, 254, 0.65) 0%, rgba(255, 255, 255, 0) 16%),
    linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,1) 100%);
  box-shadow: inset 0 -1px 0 rgba(19, 34, 56, 0.06);
}

.sensor-edit-panel :deep(.offcanvas-body) {
  padding: 1.25rem;
  overflow-y: auto;
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.12), transparent 24%),
    linear-gradient(90deg, rgba(239, 246, 255, 0.7) 0%, rgba(255, 255, 255, 0) 14%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
}

.sensor-edit-panel :deep(.form-control),
.sensor-edit-panel :deep(.form-select),
.sensor-edit-panel :deep(.btn) {
  border-radius: 12px;
  border-color: rgba(19, 34, 56, 0.12);
}

.sensor-edit-shell > .mb-3,
.sensor-edit-shell > .mb-4 {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 18px;
  padding: 1rem;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.06), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.96) 100%);
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
}

@media (max-width: 576px) {
  .device-registration-panel {
    width: 100vw;
    min-width: 100vw;
    max-width: 100vw;
  }

  .device-registration-resize-handle {
    display: none;
  }

  .sensor-edit-panel {
    width: 100vw;
    min-width: 100vw;
    max-width: 100vw;
  }

  .sensor-edit-resize-handle {
    display: none;
  }
}

.device-info-card {
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.06);
  transition: all 0.2s ease;
}

.device-info-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.09);
}

.device-info-card :deep(.card-body) {
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
}

.device-info-card h6 {
  color: #132238;
  font-weight: 700;
}

.device-info-card small {
  color: #475569;
}

.device-info-card code {
  color: #5b21b6;
  background: #ede9fe;
  border-radius: 8px;
  padding: 0.1rem 0.35rem;
}

.device-info-card :deep(.btn) {
  border-radius: 12px;
}

.registration-section-toggle {
  cursor: pointer;
  user-select: none;
  border-radius: 12px;
  padding: 0.2rem 0.15rem;
  width: 100%;
  background: none;
  border: none;
  text-align: left;
}

.registration-section-toggle:focus-visible {
  outline: 2px solid rgba(37, 99, 235, 0.25);
  outline-offset: 2px;
}

.topology-embed-card {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.topology-embed-card__header {
  background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,1) 100%);
  border-bottom: 1px solid rgba(37, 99, 235, 0.08);
  padding: 0.75rem 1.2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
}

.topology-embed-chevron {
  display: inline-block;
  font-size: 18px;
  color: #6b7280;
  transition: transform 0.22s ease;
  transform: rotate(0deg);
  line-height: 1;
}
.topology-embed-chevron.open {
  transform: rotate(90deg);
}

.topology-fullscreen-btn {
  background: none;
  border: 1px solid rgba(37,99,235,0.15);
  border-radius: 8px;
  padding: 2px 8px;
  font-size: 16px;
  color: #6b7280;
  cursor: pointer;
  line-height: 1.4;
  transition: color 0.15s, background 0.15s;
  flex-shrink: 0;
}
.topology-fullscreen-btn:hover {
  color: #1d4ed8;
  background: #eff6ff;
}

/* When the wrap div goes fullscreen, give the canvas full viewport height */
:deep([fullscreen] .topo-canvas-wrap),
:deep(:fullscreen .topo-canvas-wrap) {
  height: 100vh !important;
  border-radius: 0 !important;
}

/* Setpoint overlay — position:fixed re-roots to the fullscreen element */
.sp-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sp-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
}
.sp-panel {
  position: relative;
  z-index: 1;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.22);
  width: 460px;
  max-width: 90vw;
}
.sp-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  font-weight: 700;
  font-size: 14px;
  color: #0f172a;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.sp-panel__close {
  background: none;
  border: none;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: #475569;
  padding: 0 2px;
}
.sp-panel__close:hover { color: #0f172a; }
.sp-panel__body { padding: 20px; }
.sp-panel__topic {
  margin-bottom: 16px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  font-size: 11px;
  color: #0f172a;
}
.sp-panel__preview {
  margin-top: 16px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f0fdf4;
  border: 1px solid #86efac;
  font-size: 11px;
  color: #0f172a;
}
.sp-panel__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}
.dd-overlay {
  position: fixed;
  inset: 0;
  z-index: 1060;
  background: rgba(0, 0, 0, 0.35);
}
.dd-window {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 760px;
  max-width: 96vw;
  max-height: 88vh;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.28);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.dd-window__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  font-weight: 700;
  font-size: 15px;
  color: #0f172a;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  cursor: move;
  user-select: none;
  background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
}
.dd-window__close {
  background: none;
  border: none;
  font-size: 22px;
  line-height: 1;
  color: #475569;
  cursor: pointer;
  padding: 0 2px;
}
.dd-window__close:hover { color: #0f172a; }
.dd-window__body { overflow-y: auto; padding: 20px; flex: 1; }
.dd-window__footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  background: #f8fafc;
}

.se-section {
  background: rgba(248, 250, 252, 0.7);
  border: 1px solid rgba(37, 99, 235, 0.07);
  border-radius: 12px;
  padding: 14px 16px 16px;
  margin-bottom: 14px;
}
.se-section__title {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 12px;
}
.se-type-hint {
  font-size: 11px;
  display: block;
  margin-top: 4px;
}
.se-type-hint--control { color: #b45309; }

.sp-fade-enter-active,
.sp-fade-leave-active { transition: opacity 0.18s ease; }
.sp-fade-enter-from,
.sp-fade-leave-to { opacity: 0; }

.sp-panel__toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.sp-toggle-on  { font-weight: 700; color: #059669; font-size: 13px; }
.sp-toggle-off { font-weight: 700; color: #dc2626; font-size: 13px; }
.sp-panel__preview--off {
  background: #fff7ed;
  border-color: #fed7aa;
  color: #92400e;
}
</style>
