// API Configuration
const config = {
  // Base API URL - automatically loaded from .env files
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
  // API Endpoints
  endpoints: {
    auth: {
      login: '/auth/login',
      logout: '/auth/logout',
      me: '/auth/me'
    },
    health: '/health',
    services: '/services',
    weather: '/weather',
    // Add more endpoints as needed
  },

  // Request configuration (configurable via environment)
  defaultHeaders: {
    'Content-Type': 'application/json',
  },
  
  // Request timeout in milliseconds (from env or default)
  timeout: parseInt(import.meta.env.VITE_API_TIMEOUT) || 10000,
  
  // Whether to include credentials (cookies) in requests
  withCredentials: true,
  
  // Debug mode (from env)
  debug: import.meta.env.VITE_DEBUG_MODE === 'true',
  
  // Environment info
  environment: import.meta.env.VITE_APP_ENV || 'development',
  appName: import.meta.env.VITE_APP_NAME || 'QoE Application'
}

// Helper function to build full URL
export const buildApiUrl = (endpoint) => {
  return `${config.baseURL}${endpoint}`
}

// Helper function to make API requests
export const apiRequest = async (endpoint, options = {}) => {
  const url = buildApiUrl(endpoint)
  
  // Get JWT token from auth store if available
  let jwtToken = null
  try {
    // Dynamically import to avoid circular dependencies
    const { useAuthStore } = await import('../stores/auth.js')
    const authStore = useAuthStore()
    jwtToken = authStore.getJwtToken()
  } catch (error) {
    console.warn('Could not get JWT token:', error)
  }
  
  const defaultOptions = {
    headers: {
      ...config.defaultHeaders,
      // Add JWT token to Authorization header if available
      ...(jwtToken && { 'Authorization': `Bearer ${jwtToken}` })
    },
    credentials: config.withCredentials ? 'include' : 'omit',
    ...options
  }
  
  // Merge headers properly
  if (options.headers) {
    defaultOptions.headers = {
      ...defaultOptions.headers,
      ...options.headers
    }
  }
  
  // Debug logging if enabled
  if (config.debug) {
    console.log(`🔗 API Request: ${options.method || 'GET'} ${url}`)
    console.log('📋 Options:', defaultOptions)
  }
  
  try {
    // Create abort controller for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), config.timeout)
    
    const response = await fetch(url, {
      ...defaultOptions,
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    
    if (config.debug) {
      console.log(`✅ API Response: ${response.status} ${response.statusText}`)
    }
    
    return response
  } catch (error) {
    if (error.name === 'AbortError') {
      console.error(`⏱️ API request timeout after ${config.timeout}ms for ${endpoint}`)
      throw new Error(`Request timeout after ${config.timeout}ms`)
    }
    
    console.error(`❌ API request failed for ${endpoint}:`, error)
    throw error
  }
}

// Helper function to log current configuration (useful for debugging)
export const logConfig = () => {
  console.log('🔧 API Configuration:')
  console.log(`📍 Base URL: ${config.baseURL}`)
  console.log(`🌍 Environment: ${config.environment}`)
  console.log(`📱 App Name: ${config.appName}`)
  console.log(`⏱️ Timeout: ${config.timeout}ms`)
  console.log(`🍪 With Credentials: ${config.withCredentials}`)
  console.log(`🐛 Debug Mode: ${config.debug}`)
}

// Auto-log configuration in development
if (config.debug) {
  logConfig()
}

export default config
