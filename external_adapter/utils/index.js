const { Requester, Validator } = require('@chainlink/external-adapter');
const { uploadToIPFS } = require('./ipfs.js');
const { encryptStreamToIpfs, storeCidMapping, healthCheck, getCidMapping, decryptFromIpfsToStream } = require('./vault');
const { Readable } = require('stream');
const { v4: uuidv4 } = require('uuid'); // Import the uuid library
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Define custom parameters to be used by the adapter
const customParams = {
  lat: ['lat', 'latitude'],
  lon: ['lon', 'longitude'],
  service: ['service'], // Accepts "openweather", "openmeteo", or null (both)
};

const createRequest = async (input, callback, forecast = false) => {
  // Generate a unique jobRunID
  const jobRunID = uuidv4();

  // Extract and normalize parameters
  const validator = new Validator(callback, input, customParams);
  const lat = validator.validated.data.lat;
  const lon = validator.validated.data.lon;
  let service = validator.validated.data.service;

  // If service is null, undefined, or empty → fetch from both services
  const fetchBothServices = !service || service.trim() === "";

  // Store responses from both APIs
  let responses = [];

  if (fetchBothServices || service.toLowerCase() === 'openweather') {
    const appID = process.env.OPENWEATHER_API_KEY;
    if (appID) {
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
        responses.push({ service: 'openweather', data: openWeatherResponse.data });
      } catch (error) {
        console.warn("Failed to fetch OpenWeather data:", error.message);
      }
    } else {
      console.warn("Skipping OpenWeather request: API key missing.");
    }
  }

  if (fetchBothServices || service.toLowerCase() === 'openmeteo') {
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
      responses.push({ service: 'openmeteo', data: openMeteoResponse.data });
    } catch (error) {
      console.warn("Failed to fetch OpenMeteo data:", error.message);
    }
  }

  // Read and merge dummy data from ../data/dummy.json
  try {
    const dummyPath = path.resolve(__dirname, '../data/qoe.json');
    if (fs.existsSync(dummyPath)) {
      const dummyRaw = fs.readFileSync(dummyPath, 'utf8');
      const dummyData = JSON.parse(dummyRaw);
      responses.push({ service: 'qoe', data: dummyData });
    }
  } catch (err) {
    console.warn('Could not read or parse dummy data:', err.message);
  }

  if (responses.length === 0) {
    return callback(400, {
      jobRunID,
      status: 'errored',
      error: "No valid service found or API calls failed",
      statusCode: 400,
    });
  }

  // Save the combined response to IPFS with optional encryption
  const filename = `weather_data_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  
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

// Handle decryption requests
const handleDecryptRequest = async (req, res) => {
  console.log('Decrypt Request Data: ', req.body);
  
  const { cid } = req.body;
  const jobRunID = uuidv4();
  
  // Validate required parameters
  if (!cid) {
    return res.status(400).json({
      jobRunID,
      status: 'errored',
      error: 'Missing required parameter: cid',
      statusCode: 400,
    });
  }
  
  const vaultEnabled = process.env.VAULT_ENABLED === 'true';
  
  try {
    if (!vaultEnabled) {
      return res.status(400).json({
        jobRunID,
        status: 'errored',
        error: 'Vault is disabled. Cannot decrypt data.',
        statusCode: 400,
      });
    }
    
    // Check Vault connection
    const vaultHealthy = await healthCheck();
    if (!vaultHealthy) {
      return res.status(503).json({
        jobRunID,
        status: 'errored',
        error: 'Vault is not healthy. Cannot decrypt data.',
        statusCode: 503,
      });
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
    
    // Get IPFS URL from environment
    const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
    const ipfsApiUrl = ipfsUrl.replace('/api/v0', ''); // Remove API path if present
    
    // Decrypt data from IPFS
    const decryptionMeta = {
      cid,
      ...metadata
    };
    const decryptedStream = await decryptFromIpfsToStream(decryptionMeta, ipfsApiUrl);
    
    // Convert stream to buffer
    const chunks = [];
    for await (const chunk of decryptedStream) {
      chunks.push(chunk);
    }
    const decryptedBuffer = Buffer.concat(chunks);

    // If this payload is a cost file (binary like Excel), return it raw (base64) + filename
    if (metadata && metadata.data_type && metadata.data_type === 'costs') {
      const filename = metadata.filename || 'file';
      const accept = (req.headers && (req.headers.accept || '')) || '';
      const wantsDownload = (req.query && (req.query.download === 'true' || req.query.raw === 'true')) || accept.includes('application/octet-stream') || accept.includes('application/vnd.openxmlformats-officedocument');

      if (wantsDownload) {
        // Determine a sensible content type from filename
        const ext = path.extname(filename).toLowerCase();
        let contentType = 'application/octet-stream';
        if (ext === '.xlsx') contentType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
        else if (ext === '.csv') contentType = 'text/csv';

        res.setHeader('Content-Type', contentType);
        res.setHeader('Content-Disposition', `attachment; filename="${filename.replace(/\"/g,'') }"`);
        // Send raw bytes directly so Postman can save file as binary
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
    }

    // Otherwise assume decrypted content is UTF-8 JSON and parse
    const decryptedString = decryptedBuffer.toString('utf8');
    let decryptedData;
    try {
      decryptedData = JSON.parse(decryptedString);
    } catch (e) {
      throw new Error(`Decrypted payload is not JSON: ${e.message}`);
    }

    // Extract the actual weather content from the response array
    // Filter out QoE data and return only the weather service data
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

// Handle health check requests
const handleHealthRequest = async (req, res) => {
  const jobRunID = uuidv4();
  const healthStatus = {
    timestamp: new Date().toISOString(),
    services: {}
  };
  
  let overallStatus = 'healthy';
  let statusCode = 200;
  
  try {
    // Check Vault health
    const vaultEnabled = process.env.VAULT_ENABLED === 'true';
    if (vaultEnabled) {
      try {
        const vaultHealthy = await healthCheck();
        healthStatus.services.vault = {
          status: vaultHealthy ? 'healthy' : 'unhealthy',
          endpoint: process.env.VAULT_ENDPOINT || 'not configured',
          enabled: true
        };
        if (!vaultHealthy) {
          overallStatus = 'degraded';
          statusCode = 503;
        }
      } catch (error) {
        healthStatus.services.vault = {
          status: 'error',
          error: error.message,
          endpoint: process.env.VAULT_ENDPOINT || 'not configured',
          enabled: true
        };
        overallStatus = 'degraded';
        statusCode = 503;
      }
    } else {
      healthStatus.services.vault = {
        status: 'disabled',
        enabled: false
      };
    }
    
    // Check IPFS health
    try {
      const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
      const testResponse = await fetch(`${ipfsUrl.replace('/api/v0', '')}/api/v0/version`, {
        method: 'POST',
        headers: process.env.IPFS_AUTH_TOKEN ? {
          'Authorization': `Basic ${process.env.IPFS_AUTH_TOKEN}`
        } : {}
      });
      
      healthStatus.services.ipfs = {
        status: testResponse.ok ? 'healthy' : 'unhealthy',
        endpoint: ipfsUrl,
        version: testResponse.ok ? (await testResponse.json()).Version : 'unknown'
      };
      
      if (!testResponse.ok) {
        overallStatus = 'degraded';
        statusCode = 503;
      }
    } catch (error) {
      healthStatus.services.ipfs = {
        status: 'error',
        error: error.message,
        endpoint: process.env.IPFS_URL || 'not configured'
      };
      overallStatus = 'degraded';
      statusCode = 503;
    }
    
    // Check Weather APIs
    try {
      // Test OpenWeather API
      const openWeatherKey = process.env.OPENWEATHER_API_KEY;
      if (openWeatherKey) {
        const testWeatherResponse = await fetch(
          `https://api.openweathermap.org/data/2.5/weather?lat=0&lon=0&appid=${openWeatherKey}`
        );
        healthStatus.services.openweather = {
          status: testWeatherResponse.ok ? 'healthy' : 'unhealthy',
          api_key_configured: !!openWeatherKey
        };
      } else {
        healthStatus.services.openweather = {
          status: 'not_configured',
          api_key_configured: false
        };
      }
      
      // Test OpenMeteo API (no key required)
      const testMeteoResponse = await fetch(
        'https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current_weather=true'
      );
      healthStatus.services.openmeteo = {
        status: testMeteoResponse.ok ? 'healthy' : 'unhealthy'
      };
      
      if (!testWeatherResponse.ok && !testMeteoResponse.ok) {
        overallStatus = 'degraded';
        if (statusCode === 200) statusCode = 503;
      }
    } catch (error) {
      healthStatus.services.weather_apis = {
        status: 'error',
        error: error.message
      };
      overallStatus = 'degraded';
      if (statusCode === 200) statusCode = 503;
    }
    
    // Overall health assessment
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
