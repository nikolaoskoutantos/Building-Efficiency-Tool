<template>
  <div class="register-wrapper">
    <!-- Left visual panel -->
    <div class="visual-panel d-none d-md-flex flex-column justify-content-center text-dark p-5">
      <h6 class="small text-uppercase tracking-wide">Web3 Registration</h6>
      <h1 class="display-5 fw-bold mt-4">Request Building Access</h1>
      <p class="mt-3 text-center opacity-75">
        Connect your wallet, register your building details, and submit your request for approval.
      </p>
    </div>

    <!-- Right form panel -->
    <div class="form-panel d-flex flex-column justify-content-center align-items-center p-4 p-md-5">
      <div class="register-card">

        <!-- Card header: back arrow + title -->
        <div class="register-card__header">
          <button type="button" class="register-card__back" @click="goToLogin" :disabled="isBusy" aria-label="Back to login">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <div class="register-card__title-block">
            <h2 class="register-card__title">Register with Wallet</h2>
            <p class="register-card__subtitle">Creates a pending building registration request</p>
          </div>
        </div>

        <!-- Alerts -->
        <div class="register-card__alerts">
          <CAlert v-if="errorMessage" color="danger" class="mb-2">{{ errorMessage }}</CAlert>
          <CAlert v-if="successMessage" color="success" class="mb-2">{{ successMessage }}</CAlert>
          <CAlert v-if="isLocalhost" color="info" class="mb-2">Captcha is disabled on localhost for development.</CAlert>
          <CAlert v-else-if="!turnstileSiteKey" color="warning" class="mb-2">
            Captcha site key is not configured. Registration will rely on backend settings.
          </CAlert>
          <div v-if="statusMessage" class="register-card__status">
            <output class="spinner-border spinner-border-sm me-2"><span class="visually-hidden">Loading...</span></output>
            <span>{{ statusMessage }}</span>
          </div>
        </div>

        <!-- Form body -->
        <CForm novalidate class="register-card__body">

          <!-- Wallet connect -->
          <div class="register-section mb-4">
            <CButton type="button" color="primary" class="w-100 mb-2" @click="connectWallet" :disabled="isBusy">
              {{ walletButtonLabel }}
            </CButton>
            <div class="wallet-badge">
              <span class="wallet-badge__label">Wallet</span>
              <span class="wallet-badge__value">{{ connectedAddress || 'Not connected' }}</span>
            </div>
          </div>

          <!-- Building info -->
          <div class="register-section mb-3">
            <label class="register-field-label">Building Name <span class="text-danger">*</span></label>
            <CFormInput v-model="form.building_name" placeholder="e.g. Office Block A" class="register-input" required />
          </div>

          <div class="register-section mb-3">
            <label class="register-field-label">Street Address</label>
            <CFormInput v-model="form.building_address" placeholder="Building street address" class="register-input" />
          </div>

          <!-- Map search -->
          <div class="register-section mb-3">
            <label class="register-field-label">Find on Map</label>
            <CInputGroup class="mb-1">
              <CFormInput
                v-model="addressSearch"
                placeholder="Search address, city, or place"
                class="register-input"
                @keyup.enter="searchAddress"
              />
              <CButton type="button" color="primary" variant="outline" :disabled="isBusy || isSearchingAddress" @click="searchAddress">
                {{ isSearchingAddress ? 'Searching…' : 'Search' }}
              </CButton>
            </CInputGroup>
            <div class="form-text">Click the map or search to fill in coordinates.</div>
          </div>

          <div class="register-section mb-3">
            <div ref="mapContainer" class="map-host"></div>
          </div>

          <!-- Coordinates -->
          <CRow class="g-3 mb-3">
            <CCol md="6">
              <label class="register-field-label">Latitude <span class="text-danger">*</span></label>
              <CFormInput v-model="form.building_lat" type="number" step="any" placeholder="37.9838" class="register-input" required />
            </CCol>
            <CCol md="6">
              <label class="register-field-label">Longitude <span class="text-danger">*</span></label>
              <CFormInput v-model="form.building_lon" type="number" step="any" placeholder="23.7275" class="register-input" required />
            </CCol>
          </CRow>

          <!-- Metadata -->
          <div class="register-section mb-3">
            <label class="register-field-label">Notes / Metadata</label>
            <CFormTextarea
              v-model="form.building_metadata"
              rows="3"
              placeholder="Optional notes, source information, or onboarding context"
              class="register-input"
            />
          </div>

          <!-- Captcha -->
          <div v-if="shouldUseCaptcha" class="register-section mb-4">
            <label class="register-field-label">Captcha</label>
            <div ref="turnstileContainer" class="turnstile-host"></div>
          </div>

          <!-- Actions -->
          <div class="register-card__actions">
            <CButton type="button" color="success" class="register-btn register-btn--submit" :disabled="isSubmitDisabled" @click="submitRegistration">
              Submit Registration
            </CButton>
          </div>
        </CForm>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { useAppKit, useAppKitAccount, useAppKitProvider, useDisconnect } from '@reown/appkit/vue'
import { ethers } from 'ethers'
import { buildApiUrl } from '../../config/api.js'

const router = useRouter()
const { open, close } = useAppKit()
const { disconnect } = useDisconnect()
const accountData = useAppKitAccount()
const appKitProviderState = useAppKitProvider('eip155')

const form = reactive({
  building_name: '',
  building_address: '',
  building_lat: '',
  building_lon: '',
  building_metadata: '',
})

const isConnecting = ref(false)
const isSigning = ref(false)
const isSubmitting = ref(false)
const isSearchingAddress = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const connectedAddress = ref('')
const activeProvider = ref(null)
const turnstileToken = ref('')
const turnstileContainer = ref(null)
const turnstileWidgetId = ref(null)
const turnstileSiteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY || ''
const addressSearch = ref('')
const mapContainer = ref(null)
const leafletMap = ref(null)
const leafletMarker = ref(null)
const leafletReady = ref(false)
const defaultMapCenter = { lat: 37.9838, lon: 23.7275 }
const hostname = globalThis.location?.hostname || ''
const isLocalhost = ['localhost', '127.0.0.1', '::1'].includes(hostname)
const shouldUseCaptcha = !!turnstileSiteKey && !isLocalhost
const activeWalletProvider = computed(() => extractWalletProvider(appKitProviderState?.walletProvider))

const isBusy = computed(() => isConnecting.value || isSigning.value || isSubmitting.value)
const isSubmitDisabled = computed(() => {
  if (isBusy.value || !connectedAddress.value) {
    return true
  }
  if (shouldUseCaptcha && !turnstileToken.value) {
    return true
  }
  return false
})
const statusMessage = computed(() => {
  if (isConnecting.value) return 'Waiting for wallet connection...'
  if (isSigning.value) return 'Please sign the registration message...'
  if (isSubmitting.value) return 'Submitting registration request...'
  return ''
})
const walletButtonLabel = computed(() => {
  if (connectedAddress.value) return `Wallet Connected: ${shortAddress(connectedAddress.value)}`
  if (isConnecting.value) return 'Connecting Wallet...'
  return 'Connect Wallet'
})

function shortAddress(address) {
  return address ? `${address.slice(0, 6)}...${address.slice(-4)}` : ''
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function extractWalletProvider(value) {
  if (!value || typeof value !== 'object') {
    return null
  }
  if ('request' in value && typeof value.request === 'function') {
    return value
  }
  if ('value' in value) {
    const nestedValue = value.value
    if (nestedValue && typeof nestedValue === 'object' && 'request' in nestedValue && typeof nestedValue.request === 'function') {
      return nestedValue
    }
  }
  return null
}

function syncWalletConnectionState() {
  connectedAddress.value = accountData.value.address ?? ''
  activeProvider.value = activeWalletProvider.value
}

function makeNonce() {
  const randomPart = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2)
  return `${randomPart}:${Date.now()}`
}

function buildRegisterMessage(address, nonce) {
  const timestamp = new Date().toISOString()
  return `Welcome to QoE Application!

Click to sign in and accept the Terms of Service.

This request will not trigger a blockchain transaction or cost any gas fees.

Wallet address: ${address}
Nonce: ${nonce}
Issued at: ${timestamp}`
}

function resetMessages() {
  errorMessage.value = ''
  successMessage.value = ''
}

function validateRegistrationForm() {
  const buildingName = form.building_name.trim()
  const lat = Number(form.building_lat)
  const lon = Number(form.building_lon)

  if (!buildingName) {
    return 'Building name is required'
  }
  if (form.building_lat === '' || form.building_lon === '') {
    return 'Building latitude and longitude are required'
  }
  if (Number.isNaN(lat) || Number.isNaN(lon)) {
    return 'Building latitude and longitude must be numeric'
  }
  if (lat < -90 || lat > 90) {
    return 'Building latitude must be between -90 and 90'
  }
  if (lon < -180 || lon > 180) {
    return 'Building longitude must be between -180 and 180'
  }

  return ''
}

function setCoordinates(lat, lon) {
  form.building_lat = Number(lat).toFixed(6)
  form.building_lon = Number(lon).toFixed(6)
}

function updateMapMarker(lat, lon, zoom = 15) {
  if (!leafletReady.value || !leafletMap.value || !window.L) {
    return
  }

  const point = [Number(lat), Number(lon)]
  if (!leafletMarker.value) {
    leafletMarker.value = window.L.marker(point, { draggable: true }).addTo(leafletMap.value)
    leafletMarker.value.on('dragend', async (event) => {
      const markerPoint = event.target.getLatLng()
      await handleMapSelection(markerPoint.lat, markerPoint.lng)
    })
  } else {
    leafletMarker.value.setLatLng(point)
  }

  leafletMap.value.setView(point, zoom)
}

async function reverseGeocode(lat, lon) {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&accept-language=en&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
      {
        headers: {
          Accept: 'application/json',
        },
      },
    )
    if (!response.ok) {
      return
    }
    const payload = await response.json()
    if (payload?.display_name) {
      form.building_address = payload.display_name
      addressSearch.value = payload.display_name
    }
  } catch (error) {
    console.warn('Reverse geocoding failed:', error)
  }
}

async function handleMapSelection(lat, lon) {
  setCoordinates(lat, lon)
  updateMapMarker(lat, lon)
  await reverseGeocode(lat, lon)
}

async function searchAddress() {
  const query = addressSearch.value.trim() || form.building_address.trim()
  if (!query) {
    errorMessage.value = 'Enter an address or place to search'
    return
  }

  resetMessages()
  isSearchingAddress.value = true

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=jsonv2&accept-language=en&limit=1&q=${encodeURIComponent(query)}`,
      {
        headers: {
          Accept: 'application/json',
        },
      },
    )
    if (!response.ok) {
      throw new Error('Address search failed')
    }

    const results = await response.json()
    if (!Array.isArray(results) || results.length === 0) {
      throw new Error('No matching address found')
    }

    const first = results[0]
    form.building_address = first.display_name || query
    addressSearch.value = first.display_name || query
    setCoordinates(first.lat, first.lon)
    updateMapMarker(first.lat, first.lon)
  } catch (error) {
    errorMessage.value = error.message || 'Address search failed'
  } finally {
    isSearchingAddress.value = false
  }
}

function initLeafletMap() {
  if (!window.L || !mapContainer.value || leafletMap.value) {
    return
  }

  leafletMap.value = window.L.map(mapContainer.value, {
    zoomControl: true,
  }).setView([defaultMapCenter.lat, defaultMapCenter.lon], 6)

  window.L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
  }).addTo(leafletMap.value)

  leafletMap.value.on('click', async (event) => {
    await handleMapSelection(event.latlng.lat, event.latlng.lng)
  })

  leafletReady.value = true

  if (form.building_lat && form.building_lon) {
    updateMapMarker(form.building_lat, form.building_lon)
  } else {
    updateMapMarker(defaultMapCenter.lat, defaultMapCenter.lon, 6)
  }
}

async function loadLeafletAssets() {
  if (window.L) {
    initLeafletMap()
    return
  }

  const existingCss = document.querySelector('link[data-leaflet="true"]')
  if (!existingCss) {
    const css = document.createElement('link')
    css.rel = 'stylesheet'
    css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    css.dataset.leaflet = 'true'
    document.head.appendChild(css)
  }

  await new Promise((resolve, reject) => {
    const existingScript = document.querySelector('script[data-leaflet="true"]')
    if (existingScript) {
      existingScript.addEventListener('load', resolve, { once: true })
      existingScript.addEventListener('error', reject, { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.async = true
    script.defer = true
    script.dataset.leaflet = 'true'
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })

  initLeafletMap()
}

async function waitForWalletReady(timeoutMs = 12000, stepMs = 250) {
  const startedAt = Date.now()

  while (Date.now() - startedAt < timeoutMs) {
    const address = accountData.value.address ?? ''
    const provider = activeWalletProvider.value

    if (address && provider) {
      return { address, provider }
    }

    await sleep(stepMs)
  }

  throw new Error('Wallet connection timed out')
}

async function connectWallet() {
  if (isBusy.value) return

  resetMessages()
  isConnecting.value = true

  try {
    await open()
    const { address, provider } = await waitForWalletReady()
    await close?.()
    connectedAddress.value = address
    activeProvider.value = provider
  } catch (error) {
    errorMessage.value = error.message || 'Wallet connection failed'
  } finally {
    isConnecting.value = false
  }
}

async function signRegistrationMessage() {
  const providerSource = activeProvider.value || activeWalletProvider.value

  if (!connectedAddress.value || !providerSource) {
    throw new Error('Wallet is not connected')
  }

  isSigning.value = true
  try {
    const provider = new ethers.providers.Web3Provider(providerSource)
    const signer = provider.getSigner()
    const nonce = makeNonce()
    const message = buildRegisterMessage(connectedAddress.value, nonce)
    const signature = await signer.signMessage(message)
    return { nonce, message, signature }
  } finally {
    isSigning.value = false
  }
}

async function submitRegistration() {
  if (isBusy.value) return
  resetMessages()
  syncWalletConnectionState()

  const validationError = validateRegistrationForm()
  if (validationError) {
    errorMessage.value = validationError
    return
  }

  if (!connectedAddress.value || !activeProvider.value) {
    try {
      const { address, provider } = await waitForWalletReady(3000, 150)
      connectedAddress.value = address
      activeProvider.value = provider
    } catch {
      // Fall through to the user-facing validation below.
    }
  }

  if (!connectedAddress.value || !activeProvider.value) {
    errorMessage.value = 'Connect your wallet first'
    return
  }

  if (shouldUseCaptcha && !turnstileToken.value) {
    errorMessage.value = 'Complete the captcha before submitting'
    return
  }

  isSubmitting.value = true
  try {
    const { nonce, message, signature } = await signRegistrationMessage()
    const response = await fetch(buildApiUrl('/auth/register-web3'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address: connectedAddress.value,
        message,
        signature,
        nonce,
        captcha_token: turnstileToken.value || null,
        role: 'occupant',
        ...form,
      }),
    })

    const result = await response.json()
    if (!response.ok) {
      throw new Error(result.detail || result.message || `Registration failed with status ${response.status}`)
    }

    successMessage.value = 'Registration request submitted. BENET will contact you soon.'
    form.building_name = ''
    form.building_address = ''
    form.building_lat = ''
    form.building_lon = ''
    form.building_metadata = ''
    addressSearch.value = ''
    updateMapMarker(defaultMapCenter.lat, defaultMapCenter.lon, 6)
    resetTurnstile()
  } catch (error) {
    errorMessage.value = error.message || 'Registration failed'
  } finally {
    isSubmitting.value = false
  }
}

async function goToLogin() {
  if (connectedAddress.value) {
    try {
      await disconnect()
    } catch (error) {
      console.warn('Wallet disconnect during navigation did not complete cleanly:', error)
    }
  }
  await router.push('/login')
}

function resetTurnstile() {
  turnstileToken.value = ''
  if (turnstileWidgetId.value !== null && window.turnstile) {
    window.turnstile.reset(turnstileWidgetId.value)
  }
}

function renderTurnstile() {
  if (!shouldUseCaptcha || !turnstileContainer.value || !window.turnstile || turnstileWidgetId.value !== null) {
    return
  }

  turnstileWidgetId.value = window.turnstile.render(turnstileContainer.value, {
    sitekey: turnstileSiteKey,
    callback(token) {
      turnstileToken.value = token
    },
    'expired-callback'() {
      turnstileToken.value = ''
    },
    'error-callback'() {
      turnstileToken.value = ''
    },
  })
}

async function loadTurnstileScript() {
  if (!shouldUseCaptcha) {
    return
  }

  if (window.turnstile) {
    renderTurnstile()
    return
  }

  await new Promise((resolve, reject) => {
    const existingScript = document.querySelector('script[data-turnstile="true"]')
    if (existingScript) {
      existingScript.addEventListener('load', resolve, { once: true })
      existingScript.addEventListener('error', reject, { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    script.async = true
    script.defer = true
    script.dataset.turnstile = 'true'
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })

  renderTurnstile()
}

onMounted(async () => {
  syncWalletConnectionState()

  try {
    await loadTurnstileScript()
  } catch (error) {
    console.warn('Turnstile script failed to load:', error)
  }

  try {
    await loadLeafletAssets()
  } catch (error) {
    console.warn('Leaflet failed to load:', error)
  }
})

watchEffect(() => {
  syncWalletConnectionState()
})

onBeforeUnmount(() => {
  if (turnstileWidgetId.value !== null && window.turnstile) {
    window.turnstile.remove(turnstileWidgetId.value)
  }
  if (leafletMap.value) {
    leafletMap.value.remove()
    leafletMap.value = null
    leafletMarker.value = null
  }
})
</script>

<style scoped>
/* ── Layout ── */
.register-wrapper {
  display: flex;
  min-height: 100vh;
  background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 100%);
}

.visual-panel {
  background-image: url('@/assets/images/login.jpg');
  background-size: cover;
  background-position: center;
  width: 42%;
  flex-shrink: 0;
  position: relative;
}

.visual-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(160deg, rgba(30, 58, 138, 0.18), rgba(14, 165, 233, 0.12));
}

.visual-panel > * { position: relative; z-index: 1; }

.tracking-wide { letter-spacing: 0.08em; }

.form-panel {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

/* ── Card shell ── */
.register-card {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  background: linear-gradient(180deg, rgba(249, 251, 255, 0.98) 0%, rgba(241, 247, 255, 0.96) 100%);
  border: 1px solid rgba(172, 199, 255, 0.3);
  border-radius: 24px;
  box-shadow:
    0 20px 48px rgba(15, 23, 42, 0.08),
    0 4px 12px rgba(103, 129, 167, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  overflow: hidden;
}

/* ── Card header ── */
.register-card__header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 1.8rem 1rem;
  border-bottom: 1px solid rgba(172, 199, 255, 0.2);
  background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(249,251,255,0.8));
}

.register-card__back {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(172, 199, 255, 0.4);
  border-radius: 12px;
  background: rgba(234, 243, 255, 0.8);
  color: #334155;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.register-card__back:hover {
  background: #dbeafe;
  color: #1e40af;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
}

.register-card__back:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.register-card__title-block { flex: 1; }

.register-card__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.15rem;
}

.register-card__subtitle {
  font-size: 0.82rem;
  color: #64748b;
  margin: 0;
}

/* ── Alerts strip ── */
.register-card__alerts {
  padding: 0 1.8rem;
  padding-top: 1rem;
}

.register-card__status {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 0 0.25rem;
  font-size: 0.88rem;
  color: #2563eb;
  font-weight: 500;
}

/* ── Form body ── */
.register-card__body {
  padding: 1.2rem 1.8rem 1.8rem;
}

.register-field-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 0.35rem;
  letter-spacing: 0.01em;
}

.register-input {
  border-radius: 12px !important;
  border-color: rgba(172, 199, 255, 0.45) !important;
  background: rgba(248, 250, 255, 0.9) !important;
  font-size: 0.9rem;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.register-input:focus {
  border-color: rgba(37, 99, 235, 0.5) !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

/* ── Wallet badge ── */
.wallet-badge {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(172, 199, 255, 0.35);
  border-radius: 12px;
  background: rgba(241, 247, 255, 0.8);
  word-break: break-all;
  font-size: 0.85rem;
}

.wallet-badge__label {
  font-weight: 700;
  color: #334155;
  flex-shrink: 0;
}

.wallet-badge__value {
  color: #475569;
  font-family: monospace;
}

/* ── Map ── */
.map-host {
  width: 100%;
  min-height: 300px;
  border: 1px solid rgba(172, 199, 255, 0.35);
  border-radius: 14px;
  overflow: hidden;
  background: #eef3f8;
}

/* ── Actions ── */
.register-card__actions {
  margin-top: 1.2rem;
}

.register-btn {
  width: 100%;
  border-radius: 14px !important;
  padding: 0.65rem !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
}

.register-btn--submit {
  box-shadow: 0 8px 20px rgba(22, 163, 74, 0.22);
}

/* ── Captcha ── */
.turnstile-host { min-height: 70px; }

/* ── Mobile ── */
@media (max-width: 768px) {
  .register-wrapper {
    background-image: url('@/assets/images/login.jpg');
    background-size: cover;
    background-position: center;
  }

  .form-panel {
    background: rgba(248, 250, 255, 0.94);
    backdrop-filter: blur(12px);
    padding: 1.5rem 1rem;
    min-height: 100vh;
  }

  .register-card {
    border-radius: 20px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  }

  .register-card__header,
  .register-card__body,
  .register-card__alerts { padding-left: 1.2rem; padding-right: 1.2rem; }
}
</style>
