const { Requester, Validator } = require('@chainlink/external-adapter');
const { uploadToIPFS } = require('./ipfs.js');
const { encryptStreamToIpfs, storeCidMapping, healthCheck, getCidMapping, decryptFromIpfsToStream } = require('./vault');
const { Readable } = require('node:stream');
const { v4: uuidv4 } = require('uuid'); // Import the uuid library
const fs = require('node:fs');
const path = require('node:path');
require('dotenv').config();

// Define custom parameters to be used by the adapter
const customParams = {
  lat: ['lat', 'latitude'],
  lon: ['lon', 'longitude'],
  service: ['service'], // Accepts "openweather", "openmeteo", or null (both)
};

// Helper function to fetch OpenWeather data
const fetchOpenWeatherData = async (lat, lon, forecast) => {
  const appID = process.env.OPENWEATHER_API_KEY;
  if (!appID) {
    console.warn("Skipping OpenWeather request: API key missing.");
    return null;
  }

  try {
    const openWeatherConfig = {
      url: forecast
        ? `https://api.openweathermap.org/data/2.5/forecast`
        : `https://api.openweathermap.org/data/2.5/weather`,
      params: {
        lat,
        lon,
        appid: appID,
        units: 'metric', // Use metric system
      },
    };
    console.log("Fetching OpenWeather data...");
    const openWeatherResponse = await Requester.request(openWeatherConfig);
    return { service: 'openweather', data: openWeatherResponse.data };
  } catch (error) {
    console.warn("Failed to fetch OpenWeather data:", error.message);
    return null;
  }
};

// Helper function to fetch OpenMeteo data
const fetchOpenMeteoData = async (lat, lon, forecast) => {
  try {
    const openMeteoConfig = {
      url: `https://api.open-meteo.com/v1/forecast`,
      params: {
        latitude: lat,
        longitude: lon,
        current_weather: !forecast, // Fetch current weather if not a forecast
        hourly: forecast ? 'temperature_2m' : undefined,
      },
    };
    console.log("Fetching OpenMeteo data...");
    const openMeteoResponse = await Requester.request(openMeteoConfig);
    return { service: 'openmeteo', data: openMeteoResponse.data };
  } catch (error) {
    console.warn("Failed to fetch OpenMeteo data:", error.message);
    return null;
  }
};

// Helper function to fetch dummy QoE data
const fetchQoeData = () => {
  try {
    const dummyPath = path.resolve(__dirname, '../data/qoe.json');
    if (fs.existsSync(dummyPath)) {
      const dummyRaw = fs.readFileSync(dummyPath, 'utf8');
      const dummyData = JSON.parse(dummyRaw);
      return { service: 'qoe', data: dummyData };
    }
    return null;
  } catch (err) {
    console.warn('Could not read or parse dummy data:', err.message);
    return null;
  }
};

// Helper function to collect API responses
const collectApiResponses = async (lat, lon, service, forecast) => {
  const fetchBothServices = !service || service.trim() === "";
  const responses = [];

  if (fetchBothServices || service.toLowerCase() === 'openweather') {
    const openWeatherData = await fetchOpenWeatherData(lat, lon, forecast);
    if (openWeatherData) responses.push(openWeatherData);
  }

  if (fetchBothServices || service.toLowerCase() === 'openmeteo') {
    const openMeteoData = await fetchOpenMeteoData(lat, lon, forecast);
    if (openMeteoData) responses.push(openMeteoData);
  }

  // Always add QoE data
  const qoeData = fetchQoeData();
  if (qoeData) responses.push(qoeData);

  return responses;
};

const createRequest = async (input, callback, forecast = false) => {
  // Generate a unique jobRunID
  const jobRunID = uuidv4();

  // Extract and normalize parameters
  const validator = new Validator(callback, input, customParams);
  const lat = validator.validated.data.lat;
  const lon = validator.validated.data.lon;
  const service = validator.validated.data.service;

  // Collect responses from APIs
  const responses = await collectApiResponses(lat, lon, service, forecast);

  if (responses.length === 0) {
    return callback(400, {
      jobRunID,
      status: 'errored',
      error: "No valid service found or API calls failed",
      statusCode: 400,
    });
  }

  // Save the combined response to IPFS with optional encryption
  const filename = `weather_data_${new Date().toISOString().replaceAll(/[:.]/g, '-')}.json`;
  
  let cid;
  const vaultEnabled = process.env.VAULT_ENABLED === 'true';
  
  try {
    if (vaultEnabled) {
      // Check Vault connection first
      const vaultHealthy = await healthCheck();
      
      if (vaultHealthy) {
        console.log('🔐 Using Vault encryption for IPFS upload...');
        
        // Convert JSON to readable stream
        const dataString = JSON.stringify(responses, null, 2);
        const dataStream = Readable.from([dataString]);
        
        // Get IPFS URL from environment
        const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
        const ipfsApiUrl = ipfsUrl.replace('/api/v0', ''); // Remove API path if present
        
        // Encrypt and upload to IPFS
        const result = await encryptStreamToIpfs(dataStream, ipfsApiUrl, 'weather-data');
        
        // Store CID mapping in Vault KV
        await storeCidMapping(result.cid, {
          wrapped_dek: result.wrapped_dek,
          key_version: result.key_version,
          algorithm: result.alg,
          chunk_bytes: result.chunk_bytes,
          nonce_mode: result.nonce_mode,
          timestamp: Date.now(),
          filename: filename,
          job_id: jobRunID,
          data_type: 'weather_data'
        });
        
        cid = result.cid;
        console.log(`✅ Encrypted data uploaded to IPFS: ${cid}`);
      } else {
        console.warn('⚠️ Vault unhealthy, falling back to plain IPFS upload');
        cid = await uploadToIPFS(JSON.stringify(responses, null, 2), filename);
      }
    } else {
      console.log('📁 Vault disabled, using plain IPFS upload');
      cid = await uploadToIPFS(JSON.stringify(responses, null, 2), filename);
    }
  } catch (vaultError) {
    console.error('❌ Vault encryption failed, falling back to plain IPFS:', vaultError.message);
    cid = await uploadToIPFS(JSON.stringify(responses, null, 2), filename);
  }

  // Return only the CID in the response
  callback(200, {
    jobRunID,
    cid: cid, // Return only the CID
    statusCode: 200,
  });
};

// Handle requests for current weather (Fetches from both if service is null)
const handleWeatherRequest = (req, res) => {
  console.log('POST Data: ', req.body);
  createRequest(req.body, (status, result) => {
    console.log('Weather Result: ', result);
    res.status(status).json(result);
  }, false); // Current weather request (not forecast)  
};

// Handle requests for weather forecasts (Fetches from both if service is null)
const handleForecastRequest = (req, res) => {
  console.log('POST Data: ', req.body);
  createRequest(req.body, (status, result) => {
    console.log('Forecast Result: ', result);
    res.status(status).json(result);
  }, true); // Forecast request
};

// Helper function to validate decryption prerequisites
const validateDecryptionRequest = async (cid, jobRunID) => {
  if (!cid) {
    return {
      error: {
        jobRunID,
        status: 'errored',
        error: 'Missing required parameter: cid',
        statusCode: 400,
      }
    };
  }

  const vaultEnabled = process.env.VAULT_ENABLED === 'true';
  if (!vaultEnabled) {
    return {
      error: {
        jobRunID,
        status: 'errored',
        error: 'Vault is disabled. Cannot decrypt data.',
        statusCode: 400,
      }
    };
  }

  const vaultHealthy = await healthCheck();
  if (!vaultHealthy) {
    return {
      error: {
        jobRunID,
        status: 'errored',
        error: 'Vault is not healthy. Cannot decrypt data.',
        statusCode: 503,
      }
    };
  }

  return { success: true };
};

// Helper function to handle cost file response
const handleCostFileResponse = (decryptedBuffer, metadata, req, res, jobRunID, cid) => {
  const filename = metadata.filename || 'file';
  const accept = (req.headers && (req.headers.accept || '')) || '';
  const wantsDownload = (req.query && (req.query.download === 'true' || req.query.raw === 'true')) || 
                       accept.includes('application/octet-stream') || 
                       accept.includes('application/vnd.openxmlformats-officedocument');

  if (wantsDownload) {
    // Determine a sensible content type from filename
    const ext = path.extname(filename).toLowerCase();
    let contentType = 'application/octet-stream';
    if (ext === '.xlsx') contentType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    else if (ext === '.csv') contentType = 'text/csv';

    res.setHeader('Content-Type', contentType);
    res.setHeader('Content-Disposition', `attachment; filename="${filename.replaceAll('"', '')}"`);
    return res.status(200).send(decryptedBuffer);
  }

  // Default: return base64 JSON for backward compatibility
  const b64 = decryptedBuffer.toString('base64');
  console.log(`✅ Decrypted binary cost file for CID: ${cid}, filename: ${filename}`);
  return res.status(200).json({
    jobRunID,
    cid,
    data: {
      filename: filename,
      content_base64: b64,
      encoding: 'base64'
    },
    metadata: {
      timestamp: metadata.timestamp,
      filename: filename,
      job_id: metadata.job_id,
      data_type: metadata.data_type,
      algorithm: metadata.algorithm
    },
    statusCode: 200,
  });
};

// Helper function to decrypt and parse data from IPFS
const decryptDataFromIpfs = async (cid, metadata) => {
  const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
  const ipfsApiUrl = ipfsUrl.replace('/api/v0', ''); // Remove API path if present
  
  const decryptionMeta = { cid, ...metadata };
  const decryptedStream = await decryptFromIpfsToStream(decryptionMeta, ipfsApiUrl);
  
  // Convert stream to buffer
  const chunks = [];
  for await (const chunk of decryptedStream) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
};

// Handle decryption requests
const handleDecryptRequest = async (req, res) => {
  console.log('Decrypt Request Data: ', req.body);
  
  const { cid } = req.body;
  const jobRunID = uuidv4();
  
  try {
    // Validate prerequisites
    const validation = await validateDecryptionRequest(cid, jobRunID);
    if (validation.error) {
      return res.status(validation.error.statusCode).json(validation.error);
    }

    console.log(`🔓 Decrypting data for CID: ${cid}`);
    
    // Get CID mapping from Vault
    const metadata = await getCidMapping(cid);
    if (!metadata) {
      return res.status(404).json({
        jobRunID,
        status: 'errored',
        error: `No encryption metadata found for CID: ${cid}`,
        statusCode: 404,
      });
    }

    // Decrypt data from IPFS
    const decryptedBuffer = await decryptDataFromIpfs(cid, metadata);

    // Handle cost files differently
    if (metadata?.data_type === 'costs') {
      return handleCostFileResponse(decryptedBuffer, metadata, req, res, jobRunID, cid);
    }

    // Parse JSON data for non-cost files
    const decryptedString = decryptedBuffer.toString('utf8');
    let decryptedData;
    try {
      decryptedData = JSON.parse(decryptedString);
    } catch (e) {
      throw new Error(`Decrypted payload is not JSON: ${e.message}`);
    }

    // Extract weather data (filter out QoE data)
    const weatherData = decryptedData.filter(item => 
      item.service && (item.service === 'openweather' || item.service === 'openmeteo')
    );
    
    console.log(`✅ Successfully decrypted data for CID: ${cid}`);
    
    res.status(200).json({
      jobRunID,
      cid,
      data: weatherData.length === 1 ? weatherData[0].data : weatherData.map(item => ({ service: item.service, data: item.data })),
      metadata: {
        timestamp: metadata.timestamp,
        filename: metadata.filename,
        job_id: metadata.job_id,
        data_type: metadata.data_type,
        algorithm: metadata.algorithm,
        services: weatherData.map(item => item.service)
      },
      statusCode: 200,
    });
    
  } catch (error) {
    console.error('❌ Decryption failed:', error.message);
    res.status(500).json({
      jobRunID,
      status: 'errored',
      error: `Decryption failed: ${error.message}`,
      statusCode: 500,
    });
  }
};

// Helper function to check Vault health status
const checkVaultHealth = async () => {
  const vaultEnabled = process.env.VAULT_ENABLED === 'true';
  
  if (!vaultEnabled) {
    return {
      status: 'disabled',
      enabled: false
    };
  }

  try {
    const vaultHealthy = await healthCheck();
    return {
      status: vaultHealthy ? 'healthy' : 'unhealthy',
      endpoint: process.env.VAULT_ENDPOINT || 'not configured',
      enabled: true
    };
  } catch (error) {
    return {
      status: 'error',
      error: error.message,
      endpoint: process.env.VAULT_ENDPOINT || 'not configured',
      enabled: true
    };
  }
};

// Helper function to check IPFS health status
const checkIpfsHealth = async () => {
  try {
    const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
    const testResponse = await fetch(`${ipfsUrl.replace('/api/v0', '')}/api/v0/version`, {
      method: 'POST',
      headers: process.env.IPFS_AUTH_TOKEN ? {
        'Authorization': `Basic ${process.env.IPFS_AUTH_TOKEN}`
      } : {}
    });
    
    return {
      status: testResponse.ok ? 'healthy' : 'unhealthy',
      endpoint: ipfsUrl,
      version: testResponse.ok ? (await testResponse.json()).Version : 'unknown'
    };
  } catch (error) {
    return {
      status: 'error',
      error: error.message,
      endpoint: process.env.IPFS_URL || 'not configured'
    };
  }
};

// Helper function to check weather APIs health status
const checkWeatherApisHealth = async () => {
  const results = {};
  
  // Test OpenWeather API
  const openWeatherKey = process.env.OPENWEATHER_API_KEY;
  if (openWeatherKey) {
    try {
      const testWeatherResponse = await fetch(
        `https://api.openweathermap.org/data/2.5/weather?lat=0&lon=0&appid=${openWeatherKey}`
      );
      results.openweather = {
        status: testWeatherResponse.ok ? 'healthy' : 'unhealthy',
        api_key_configured: Boolean(openWeatherKey)
      };
    } catch (error) {
      results.openweather = {
        status: 'error',
        error: error.message,
        api_key_configured: Boolean(openWeatherKey)
      };
    }
  } else {
    results.openweather = {
      status: 'not_configured',
      api_key_configured: false
    };
  }
  
  // Test OpenMeteo API (no key required)
  try {
    const testMeteoResponse = await fetch(
      'https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current_weather=true'
    );
    results.openmeteo = {
      status: testMeteoResponse.ok ? 'healthy' : 'unhealthy'
    };
  } catch (error) {
    results.openmeteo = {
      status: 'error',
      error: error.message
    };
  }
  
  return results;
};

// Helper function to determine overall health status
const determineOverallStatus = (services) => {
  const hasUnhealthyService = Object.values(services).some(service => 
    service.status === 'unhealthy' || service.status === 'error'
  );
  
  if (hasUnhealthyService) {
    return { status: 'degraded', code: 503 };
  }
  
  return { status: 'healthy', code: 200 };
};

// Handle health check requests
const handleHealthRequest = async (req, res) => {
  const jobRunID = uuidv4();
  const healthStatus = {
    timestamp: new Date().toISOString(),
    services: {}
  };
  
  try {
    // Check all services
    const [vaultHealth, ipfsHealth, weatherHealth] = await Promise.all([
      checkVaultHealth(),
      checkIpfsHealth(),
      checkWeatherApisHealth()
    ]);
    
    // Aggregate results
    healthStatus.services.vault = vaultHealth;
    healthStatus.services.ipfs = ipfsHealth;
    healthStatus.services = { ...healthStatus.services, ...weatherHealth };
    
    // Determine overall status
    const { status: overallStatus, code: statusCode } = determineOverallStatus(healthStatus.services);
    healthStatus.overall_status = overallStatus;
    healthStatus.jobRunID = jobRunID;
    
    console.log(`🎡 Health check completed: ${overallStatus}`);
    res.status(statusCode).json(healthStatus);
    
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
    res.status(500).json({
      jobRunID,
      overall_status: 'error',
      error: error.message,
      timestamp: new Date().toISOString(),
      statusCode: 500
    });
  }
};

module.exports = {
  handleWeatherRequest,
  handleForecastRequest,
  handleDecryptRequest,
  handleHealthRequest,
};
