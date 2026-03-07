<template>
  <CContainer>
    <CRow>
      <CCol :xs="12">
        <CCard>
          <CCardHeader>
            <h4 class="mb-0">
              <CIcon name="cilSettings" class="me-2" />
              User Settings
            </h4>
          </CCardHeader>
          <CCardBody>
            <!-- Alert -->
            <CAlert
              v-if="alert.show"
              :color="alert.color"
              dismissible
              @close="alert.show = false"
            >
              {{ alert.message }}
            </CAlert>

            <form @submit.prevent="saveSettings">
              <!-- Personal Information Section -->
              <CCard class="mb-4">
                <CCardHeader class="bg-light">
                  <h6 class="mb-0">
                    <CIcon name="cilUser" class="me-2" />
                    Personal Information
                    <small class="text-muted ms-2">(Stored locally on your device)</small>
                  </h6>
                </CCardHeader>
                <CCardBody>
                  <CAlert color="info" class="mb-3">
                    <CIcon name="cilShieldAlt" class="me-2" />
                    <strong>Privacy Notice:</strong> Personal information is stored locally in your browser and not sent to our servers.
                  </CAlert>
                  
                  <CRow>
                    <CCol :md="6">
                      <div class="mb-3">
                        <CFormLabel for="phone">Phone Number</CFormLabel>
                        <CInputGroup>
                          <CInputGroupText>
                            <CIcon name="cilPhone" />
                          </CInputGroupText>
                          <CFormInput
                            id="phone"
                            v-model="settings.phone"
                            type="tel"
                            placeholder="+1 (555) 123-4567"
                            :disabled="loading"
                          />
                        </CInputGroup>
                      </div>
                    </CCol>
                    <CCol :md="6">
                      <div class="mb-3">
                        <CFormLabel for="email">Email Address</CFormLabel>
                        <CInputGroup>
                          <CInputGroupText>
                            <CIcon name="cilEnvelopeClosed" />
                          </CInputGroupText>
                          <CFormInput
                            id="email"
                            v-model="settings.email"
                            type="email"
                            placeholder="user@example.com"
                            :disabled="loading"
                          />
                        </CInputGroup>
                      </div>
                    </CCol>
                  </CRow>

                  <div class="mb-3">
                    <CFormLabel for="address">Physical Address</CFormLabel>
                    <CInputGroup>
                      <CInputGroupText>
                        <CIcon name="cilLocationPin" />
                      </CInputGroupText>
                      <CFormTextarea
                        id="address"
                        v-model="settings.address"
                        rows="3"
                        placeholder="123 Main Street, City, State, ZIP Code"
                        :disabled="loading"
                      />
                    </CInputGroup>
                  </div>
                </CCardBody>
              </CCard>

              <!-- Building Management Section -->
              <CCard class="mb-4">
                <CCardHeader class="bg-light">
                  <h6 class="mb-0">
                    <CIcon name="cilBuilding" class="me-2" />
                    Building Management
                  </h6>
                </CCardHeader>
                <CCardBody>
                  <div class="mb-3">
                    <CFormLabel for="default-building">Default Building</CFormLabel>
                    <CFormSelect
                      id="default-building"
                      v-model="settings.default_building_id"
                      :disabled="loading || buildings.length === 0"
                    >
                      <option value="">{{ buildings.length === 0 ? 'No buildings available' : 'Select default building' }}</option>
                      <option 
                        v-for="building in buildings" 
                        :key="building.id" 
                        :value="building.id"
                      >
                        {{ building.name }}{{ building.address ? ` - ${building.address}` : '' }}{{ (building.lat && building.lon) ? ` (${building.lat}, ${building.lon})` : '' }}
                      </option>
                    </CFormSelect>
                    <div class="form-text">
                      This building will be pre-selected when creating new devices and sensors. If not set, the first building (by ID) will be used automatically.
                    </div>
                  </div>

                  <div class="d-flex justify-content-between align-items-center">
                    <div>
                      <strong>Manage Buildings</strong>
                      <div class="text-muted small">
                        Add or edit your buildings 
                        <span v-if="loading" class="text-info">(Loading...)</span>
                        <span v-else-if="buildings.length === 0" class="text-warning">(No buildings found)</span>
                        <span v-else class="text-success">({{ buildings.length }} buildings loaded)</span>
                      </div>
                    </div>
                    <CButton
                      color="outline-primary"
                      size="sm"
                      @click="showBuildingModal = true"
                    >
                      <CIcon name="cilPlus" class="me-1" />
                      Add Building
                    </CButton>
                  </div>
                </CCardBody>
              </CCard>

              <!-- Blockchain/Wallet Section -->
              <CCard class="mb-4">
                <CCardHeader class="bg-light">
                  <h6 class="mb-0">
                    <CIcon name="cilWallet" class="me-2" />
                    Blockchain & Wallet Settings
                  </h6>
                </CCardHeader>
                <CCardBody>
                  <div class="mb-3">
                    <CFormLabel for="wallet-address">Wallet Address</CFormLabel>
                    <CInputGroup>
                      <CInputGroupText>
                        <CIcon name="cilWallet" />
                      </CInputGroupText>
                      <CFormInput
                        id="wallet-address"
                        v-model="settings.wallet_address"
                        type="text"
                        placeholder="0x1234567890abcdef..."
                        :disabled="loading"
                      />
                      <CButton
                        v-if="settings.wallet_address"
                        color="outline-secondary"
                        @click="copyWalletAddress"
                      >
                        <CIcon name="cilCopy" />
                      </CButton>
                    </CInputGroup>
                    <div class="form-text">
                      Your blockchain wallet address for receiving payments and transactions.
                      <span v-if="isWalletConnected" class="text-success">
                        <br>✅ Wallet connected: Auto-filled from {{ useAuthStore().walletAddress }}
                      </span>
                      <span v-else class="text-warning">
                        <br>⚠️ No wallet connected. Connect your wallet to auto-fill this field.
                      </span>
                    </div>
                  </div>

                  <div class="mb-3">
                    <CFormLabel for="public-key">Public Key</CFormLabel>
                    <CInputGroup>
                      <CInputGroupText>
                        <CIcon name="cilShieldAlt" />
                      </CInputGroupText>
                      <CFormTextarea
                        id="public-key"
                        v-model="settings.public_key"
                        rows="4"
                        placeholder="-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----"
                        :disabled="loading"
                      />
                      <CInputGroupText class="flex-column">
                        <CButton
                          v-if="settings.public_key"
                          color="outline-secondary"
                          size="sm"
                          class="mb-1"
                          @click="copyPublicKey"
                          title="Copy public key to clipboard"
                        >
                          <CIcon name="cilCopy" />
                        </CButton>
                        <CButton
                          color="outline-success"
                          size="sm"
                          class="mb-1"
                          @click="extractPublicKeyFromWallet"
                          :disabled="loading || !isWalletConnected"
                          :title="!isWalletConnected ? 'Connect your wallet first' : 'Extract public key from connected wallet signature'"
                        >
                          <CIcon name="cilWallet" />
                        </CButton>
                      </CInputGroupText>
                    </CInputGroup>
                    <div class="form-text">
                      Your public key for encryption and digital signatures. Options:
                      <br>• <strong>Wallet Key:</strong> Extract public key from MetaMask signature
                      <br>• <strong>Wallet Address:</strong> Use wallet address as public identifier  
                    </div>
                  </div>
                </CCardBody>
              </CCard>


              <!-- Save Button -->
              <div class="d-flex justify-content-end gap-2">
                <CButton
                  color="danger"
                  variant="outline"
                  @click="deletePersonalData"
                  :disabled="loading"
                >
                  <CIcon name="cilTrash" class="me-1" />
                  Delete Personal Data
                </CButton>
                <CButton
                  color="secondary"
                  variant="outline"
                  @click="resetSettings"
                  :disabled="loading"
                >
                  <CIcon name="cilReload" class="me-1" />
                  Reset
                </CButton>
                <CButton
                  color="primary"
                  type="submit"
                  :disabled="loading"
                >
                  <CSpinner v-if="loading" size="sm" class="me-2" />
                  <CIcon v-if="!loading" name="cilSave" class="me-1" />
                  {{ loading ? 'Saving...' : 'Save Settings' }}
                </CButton>
              </div>
            </form>
          </CCardBody>
        </CCard>
      </CCol>
    </CRow>

    <!-- Building Management Modal -->
    <CModal
      :visible="showBuildingModal"
      alignment="center"
      size="lg"
      @close="closeBuildingModal"
    >
      <CModalHeader @close-click="closeBuildingModal">
        <CModalTitle>{{ buildingForm.editing ? 'Edit Building' : 'Add New Building' }}</CModalTitle>
      </CModalHeader>
      <CModalBody>
        <form @submit.prevent="saveBuilding">
          <div class="mb-3">
            <CFormLabel for="building-name">Building Name *</CFormLabel>
            <CFormInput
              id="building-name"
              v-model="buildingForm.name"
              required
              placeholder="e.g. Main Office, Warehouse A"
              :disabled="buildingForm.loading"
            />
          </div>

          <div class="mb-3">
            <CFormLabel for="building-address">Address</CFormLabel>
            <CFormTextarea
              id="building-address"
              v-model="buildingForm.address"
              rows="3"
              placeholder="Optional building address"
              :disabled="buildingForm.loading"
            />
          </div>

          <CRow>
            <CCol :md="6">
              <div class="mb-3">
                <CFormLabel for="building-lat">Latitude</CFormLabel>
                <CFormInput
                  id="building-lat"
                  v-model="buildingForm.lat"
                  type="text"
                  placeholder="e.g. 40.7128"
                  pattern="^-?([1-8]?\d(?:\.\d+)?|90(?:\.0+)?)$"
                  :disabled="buildingForm.loading"
                />
                <small class="form-text text-muted">Latitude coordinate (-90 to 90)</small>
              </div>
            </CCol>
            <CCol :md="6">
              <div class="mb-3">
                <CFormLabel for="building-lon">Longitude</CFormLabel>
                <CFormInput
                  id="building-lon"
                  v-model="buildingForm.lon"
                  type="text"
                  placeholder="e.g. -74.0060"
                  pattern="^-?(180(?:\.0+)?|1[0-7]\d(?:\.\d+)?|\d{1,2}(?:\.\d+)?)$"
                  :disabled="buildingForm.loading"
                />
                <small class="form-text text-muted">Longitude coordinate (-180 to 180)</small>
              </div>
            </CCol>
          </CRow>
        </form>
      </CModalBody>
      <CModalFooter>
        <CButton
          color="secondary"
          @click="closeBuildingModal"
          :disabled="buildingForm.loading"
        >
          <CIcon name="cilXCircle" class="me-1" />
          Cancel
        </CButton>
        <CButton
          color="primary"
          @click="saveBuilding"
          :disabled="buildingForm.loading"
        >
          <CSpinner v-if="buildingForm.loading" size="sm" class="me-2" />
          <CIcon v-if="!buildingForm.loading" :name="buildingForm.editing ? 'cilPencil' : 'cilPlus'" class="me-1" />
          {{ buildingForm.loading ? 'Saving...' : (buildingForm.editing ? 'Update' : 'Add Building') }}
        </CButton>
      </CModalFooter>
    </CModal>
  </CContainer>
</template>

<script>
import axios from 'axios';
import { ethers } from 'ethers';
import { useAuthStore } from '@/stores/auth';

export default {
  name: 'Settings',
  setup() {
    // Make auth store available in template
    return {
      useAuthStore
    }
  },
  data() {
    return {
      loading: false,
      alert: {
        show: false,
        color: 'success',
        message: ''
      },
      buildings: [],
      settings: {
        phone: '',
        email: '',
        address: '',
        default_building_id: '',
        wallet_address: '',
        public_key: '',
        api_base_url: ''
      },
      showBuildingModal: false,
      buildingForm: {
        editing: false,
        id: null,
        name: '',
        address: '',
        lat: '',
        lon: '',
        loading: false
      }
    }
  },

  computed: {
    apiBaseUrl() {
      return this.settings.api_base_url || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    },
    
    isWalletConnected() {
      const authStore = useAuthStore()
      return authStore.isAuthenticated && authStore.walletAddress
    }
  },

  watch: {
    // Watch for wallet connection changes
    isWalletConnected: {
      handler(newVal) {
        if (newVal) {
          // Wallet just connected, update the wallet address
          this.populateWalletFromAuthStore()
        }
      },
      immediate: true
    }
  },

  mounted() {
    this.initializeSettings()
  },

  methods: {
    async initializeSettings() {
      // Load user settings first
      await this.loadSettings()
      // Then load buildings and handle default selection
      await this.loadBuildings()
      // Populate wallet address from auth store if connected
      this.populateWalletFromAuthStore()
    },
    async loadSettings() {
      // Load personal data from local storage only (GDPR compliant)
      await this.loadPersonalDataFromStorage()
      
      // Load system preferences from local storage (for now)
      await this.loadSystemPrefsFromStorage()
      
          await this.loadSystemPrefsFromBackend();
    },
    async loadSystemPrefsFromBackend() {
      try {
        const response = await axios.get(`${this.apiBaseUrl}/user/settings?wallet_address=${this.settings.wallet_address}`);
        // Only update system preferences fields
        this.settings.default_building_id = response.data.default_building_id || '';
        this.settings.wallet_address = response.data.wallet_address || '';
        this.settings.api_base_url = response.data.api_base_url || '';
        this.settings.public_key = response.data.public_key || '';
      } catch (error) {
          console.error('Failed to load system preferences from backend:', error);
          this.showAlert('warning', 'Failed to load system preferences from backend. Please check your connection.');
      }
    },

    async loadPersonalDataFromStorage() {
      const personalData = localStorage.getItem('userPersonalData')
      if (personalData) {
        const data = JSON.parse(personalData)
        this.settings = { ...this.settings, ...data }
      }
      
      // Fallback: check old unified storage
      const oldSettings = localStorage.getItem('userSettings')
      if (oldSettings && !personalData) {
        const data = JSON.parse(oldSettings)
        this.settings = { ...this.settings, ...data }
      }
    },

    async loadSystemPrefsFromStorage() {
      const systemPrefs = localStorage.getItem('userSystemPrefs')
      if (systemPrefs) {
        const data = JSON.parse(systemPrefs)
        this.settings = { ...this.settings, ...data }
      }
    },

    async saveSettings() {
      this.loading = true
      this.alert.show = false

      try {
        // Split settings: Personal data stays local, system preferences go to server
        const personalData = {
          phone: this.settings.phone,
          email: this.settings.email,
          address: this.settings.address,
          public_key: this.settings.public_key // User's choice to share public key
        }
        
        const systemPreferences = {
          default_building_id: this.settings.default_building_id,
          wallet_address: this.settings.wallet_address,
          api_base_url: this.settings.api_base_url,
            public_key: this.settings.public_key 
        }
        
        // Always save personal data locally (GDPR compliant - user's device)
        localStorage.setItem('userPersonalData', JSON.stringify(personalData))
        
        // Save system preferences locally for now
        localStorage.setItem('userSystemPrefs', JSON.stringify(systemPreferences))
        
        this.showAlert('success', 'Settings saved successfully!')
        
          // Send system preferences to backend
          try {
            const response = await axios.post(`${this.apiBaseUrl}/user/settings?wallet_address=${this.settings.wallet_address}`, systemPreferences);
            if (response.status !== 200 && response.status !== 201) {
              this.showAlert('danger', `Backend error: ${response.status} ${response.statusText}`);
              console.error('Backend error:', response);
            }
          } catch (error) {
            if (error.response) {
              this.showAlert('danger', `Backend error: ${error.response.status} ${error.response.data.detail || error.response.statusText}`);
              console.error('Backend error:', error.response);
            } else {
              this.showAlert('danger', 'Failed to save settings. Please check your backend connection.');
              console.error('Save error:', error);
            }
          }
      } catch (error) {
        console.error('Failed to save settings:', error)
        this.showAlert('danger', 'Failed to save settings. Please try again.')
      } finally {
        this.loading = false
      }
    },

    populateWalletFromAuthStore() {
      const authStore = useAuthStore()
      if (authStore.isAuthenticated && authStore.walletAddress) {
        // Only populate if wallet field is empty to avoid overwriting user input
        if (!this.settings.wallet_address) {
          this.settings.wallet_address = authStore.walletAddress
        }
      }
    },

    async loadBuildings() {
      this.loading = true
      try {
        console.log('Loading buildings from:', `${this.apiBaseUrl}/buildings`)
        const response = await fetch(`${this.apiBaseUrl}/buildings`, {
          credentials: 'include' // Include session cookies
        })
        
        if (response.ok) {
          const buildingsData = await response.json()
          this.buildings = buildingsData
          console.log('Buildings loaded:', this.buildings)
          
          // Sort buildings by ID to ensure consistent ordering
          this.buildings.sort((a, b) => a.id - b.id)
          
          // Auto-select the first building (minimum ID) if no default is set
          if (this.buildings.length > 0 && !this.settings.default_building_id) {
            this.settings.default_building_id = this.buildings[0].id
            this.showAlert('info', `Default building set to: ${this.buildings[0].name}`)
          }
        } else {
          console.warn('Failed to load buildings:', response.status, response.statusText)
          this.buildings = []
          if (response.status !== 404) { // Don't show error for empty buildings
            this.showAlert('warning', 'Failed to load buildings. You can add buildings using the button below.')
          }
        }
      } catch (error) {
        console.error('Error loading buildings:', error)
        this.buildings = []
        this.showAlert('warning', 'Error connecting to server. Buildings may not be available.')
      } finally {
        this.loading = false
      }
    },

    async deletePersonalData() {
      if (confirm('⚠️ GDPR Data Deletion\n\nThis will permanently delete all your personal information (phone, email, address, public key) from this device.\n\nThis action cannot be undone. Continue?')) {
        try {
          // Clear personal data from local storage
          localStorage.removeItem('userPersonalData')
          localStorage.removeItem('userSettings') // Legacy storage
          
          // Clear personal fields from current session
          this.settings.phone = ''
          this.settings.email = ''
          this.settings.address = ''
          this.settings.public_key = ''
          
          this.showAlert('success', 'Personal data deleted successfully. Your system preferences (building selection, wallet) have been preserved.')
          
            // Call backend to delete personal data
            try {
              await axios.delete(`${this.apiBaseUrl}/user/settings?wallet_address=${this.settings.wallet_address}`);
              } catch (error) {
                console.error('Failed to delete personal data from backend:', error);
                this.showAlert('warning', 'Failed to delete personal data from backend. Please check your connection.');
            }
        } catch (error) {
          console.error('Failed to delete personal data:', error)
          this.showAlert('danger', 'Failed to delete personal data. Please try again.')
        }
      }
    },

    resetSettings() {
      if (confirm('Are you sure you want to reset all settings? This will restore default values.')) {
        this.settings = {
          phone: '',
          email: '',
          address: '',
          default_building_id: '',
          wallet_address: '',
          public_key: '',
          api_base_url: ''
        }
        this.showAlert('info', 'Settings have been reset to defaults.')
      }
    },

    copyWalletAddress() {
      this.copyToClipboard(this.settings.wallet_address, 'Wallet address copied!')
    },

    copyPublicKey() {
      this.copyToClipboard(this.settings.public_key, 'Public key copied!')
    },

    async copyToClipboard(text, successMessage) {
      try {
        if (navigator.clipboard && globalThis.isSecureContext) {
          await navigator.clipboard.writeText(text)
        } else {
          // Fallback for non-secure contexts   
          const textArea = document.createElement('textarea')
          textArea.value = text
          textArea.style.position = 'fixed'
          textArea.style.left = '-999999px'
          document.body.appendChild(textArea)
          textArea.focus()
          textArea.select()
          document.execCommand('copy')
          textArea.remove()
        }
        this.showAlert('success', successMessage)
      } catch (error) {
        console.error('Failed to copy to clipboard:', error)
        this.showAlert('danger', 'Failed to copy to clipboard')
      }
    },

    // Wallet helpers to reduce cognitive complexity
    validateWalletConnection() {
      if (!this.isWalletConnected) {
        this.showAlert('warning', 'Please connect your wallet first.')
        return false
      }
      return true
    },

    confirmPublicKeyExtraction() {
      return confirm('This will extract the public key from your connected wallet and replace your existing public key. Continue?')
    },

    async signWalletMessage(signer, walletAddress) {
      const message = `Extract public key for QoE Application\nWallet: ${walletAddress}\nTimestamp: ${new Date().toISOString()}`
      return await signer.signMessage(message)
    },

    extractPublicKeyFromSignature(message, signature) {
      const messageHash = ethers.utils.hashMessage(message)
      const recoveredPublicKey = ethers.utils.recoverPublicKey(messageHash, signature)
      const publicKeyHex = recoveredPublicKey.substring(2) // Remove '0x' prefix
      
      // Format as PEM-like structure
      return `-----BEGIN ETHEREUM PUBLIC KEY-----\n${publicKeyHex.match(/.{1,64}/g).join('\n')}\n-----END ETHEREUM PUBLIC KEY-----`
    },

    handleWalletExtractionError(error) {
      console.error('Failed to extract public key from wallet:', error)
      
      if (error.code === 4001) {
        this.showAlert('warning', 'Transaction was rejected. Please try again and approve the signature request.')
      } else if (error.message.includes('No Ethereum provider')) {
        this.showAlert('danger', 'MetaMask not found. Please install MetaMask and try again.')
      } else {
        this.showAlert('danger', `Failed to extract public key: ${error.message}`)
      }
    },

    async extractPublicKeyFromWallet() {
      if (!this.validateWalletConnection() || !this.confirmPublicKeyExtraction()) {
        return
      }

      this.loading = true
      try {
        const authStore = useAuthStore()
        const walletAddress = authStore.walletAddress
        
        if (!globalThis.ethereum) {
          throw new Error('No Ethereum provider found. Please make sure MetaMask is installed.')
        }

        const provider = new ethers.providers.Web3Provider(globalThis.ethereum)
        const signer = provider.getSigner()
        const signature = await this.signWalletMessage(signer, walletAddress)
        
        const message = `Extract public key for QoE Application\nWallet: ${walletAddress}\nTimestamp: ${new Date().toISOString()}`
        this.settings.public_key = this.extractPublicKeyFromSignature(message, signature)
        
        this.showAlert('success', `Public key extracted from wallet ${walletAddress}! Make sure to save your settings.`)
        
      } catch (error) {
        this.handleWalletExtractionError(error)
      } finally {
        this.loading = false
      }
    },

    useWalletAddress() {
      if (!this.isWalletConnected) {
        this.showAlert('warning', 'Please connect your wallet first.')
        return
      }

      const authStore = useAuthStore()
      const walletAddress = authStore.walletAddress
      
      if (!confirm(`Use your wallet address (${walletAddress}) as your public identifier? This will replace your existing public key.`)) {
        return
      }

      // Format wallet address in a PEM-like structure for consistency
      const walletPem = `-----BEGIN WALLET ADDRESS-----\n${walletAddress}\n-----END WALLET ADDRESS-----`
      
      this.settings.public_key = walletPem
      this.showAlert('success', `Wallet address set as public identifier! Make sure to save your settings.`)
    },

    closeBuildingModal() {
      this.showBuildingModal = false
      this.buildingForm = {
        editing: false,
        id: null,
        name: '',
        address: '',
        lat: '',
        lon: '',
        loading: false
      }
    },

    // Validation helpers to reduce cognitive complexity
    validateBuildingForm() {
      if (!this.buildingForm.name.trim()) {
        this.showAlert('warning', 'Building name is required.')
        return false
      }
      return this.validateCoordinates()
    },

    validateCoordinates() {
      const latError = this.validateLatitude()
      if (latError) {
        this.showAlert('warning', latError)
        return false
      }
      
      const lonError = this.validateLongitude()
      if (lonError) {
        this.showAlert('warning', lonError)
        return false
      }
      
      return true
    },

    validateLatitude() {
      if (!this.buildingForm.lat || !this.buildingForm.lat.trim()) {
        return null // No validation needed for empty values
      }
      
      const lat = Number.parseFloat(this.buildingForm.lat.trim())
      if (Number.isNaN(lat) || lat < -90 || lat > 90) {
        return 'Latitude must be a valid number between -90 and 90.'
      }
      return null
    },

    validateLongitude() {
      if (!this.buildingForm.lon || !this.buildingForm.lon.trim()) {
        return null // No validation needed for empty values
      }
      
      const lon = Number.parseFloat(this.buildingForm.lon.trim())
      if (Number.isNaN(lon) || lon < -180 || lon > 180) {
        return 'Longitude must be a valid number between -180 and 180.'
      }
      return null
    },

    prepareBuildingPayload() {
      return {
        name: this.buildingForm.name,
        address: this.buildingForm.address || null,
        lat: this.buildingForm.lat || null,
        lon: this.buildingForm.lon || null
      }
    },

    getBuildingApiUrl() {
      return this.buildingForm.editing 
        ? `${this.apiBaseUrl}/buildings/${this.buildingForm.id}`
        : `${this.apiBaseUrl}/buildings`
    },

    async saveBuilding() {
      if (!this.validateBuildingForm()) {
        return
      }

      this.buildingForm.loading = true
      try {
        const method = this.buildingForm.editing ? 'PUT' : 'POST'
        const response = await fetch(this.getBuildingApiUrl(), {
          method,
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(this.prepareBuildingPayload())
        })

        await this.handleBuildingSaveResponse(response)
      } catch (error) {
        this.handleBuildingSaveError(error)
      } finally {
        this.buildingForm.loading = false
      }
    },

    async handleBuildingSaveResponse(response) {
      if (response.ok) {
        const action = this.buildingForm.editing ? 'updated' : 'added'
        this.showAlert('success', `Building ${action} successfully!`)
        this.loadBuildings()
        this.closeBuildingModal()
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to save building')
      }
    },

    handleBuildingSaveError(error) {
      console.error('Failed to save building:', error)
      this.showAlert('danger', error.message || 'Failed to save building')
    },

    showAlert(color, message) {
      this.alert = {
        show: true,
        color,
        message
      }
      setTimeout(() => {
        this.alert.show = false
      }, 5000)
    }
  }
}
</script>

<style scoped>
.form-text {
  font-size: 0.875rem;
  color: #6c757d;
}

.bg-light {
  background-color: #f8f9fa !important;
}

#public-key {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.85rem;
}

.gap-2 {
  gap: 0.5rem !important;
}
</style>