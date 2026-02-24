const { Requester, Validator } = require('@chainlink/external-adapter');
const { uploadToIPFS } = require('./ipfs.js');
const { encryptStreamToIpfs, storeCidMapping, healthCheck } = require('./vault');
const { Readable } = require('stream');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

// Define custom parameters for historical requests
const customParams = {
  lat: ['lat', 'latitude'],
  lon: ['lon', 'longitude'],
  service: ['service'], // Accepts 'openmeteo' (only service supporting free historical data)
  start_date: ['start_date', 'start'], // Optional
  end_date: ['end_date', 'end'] // Optional
};

// Function to get default historical date range (past 7 days)
const getDefaultDateRange = () => {
  const today = new Date();
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(today.getDate() - 7); // Default to past 7 days

  return {
    defaultStart: sevenDaysAgo.toISOString().split('T')[0], // Format: YYYY-MM-DD
    defaultEnd: today.toISOString().split('T')[0]
  };
};

const createHistoricalRequest = async (input, callback) => {
  // Validate the input
  const validator = new Validator(callback, input, customParams);
  const jobRunID = validator.validated.id || uuidv4();

  // Extract and normalize parameters
  const service = validator.validated.data.service ? validator.validated.data.service.toLowerCase() : 'openmeteo';
  const lat = validator.validated.data.lat;
  const lon = validator.validated.data.lon;
  let startDate = validator.validated.data.start_date;
  let endDate = validator.validated.data.end_date;

  const { defaultStart, defaultEnd } = getDefaultDateRange();
  if (!startDate && !endDate) {
    startDate = defaultStart;
    endDate = defaultEnd;
  } else if (!startDate) {
    startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - 7); // If only end_date is given, default start_date to 7 days before
    startDate = startDate.toISOString().split('T')[0];
  } else if (!endDate) {
    endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 7); // If only start_date is given, default end_date to 7 days after
    endDate = endDate.toISOString().split('T')[0];
  }

  let url, params;

  // OpenMeteo supports free historical weather data
  if (service === 'openmeteo') {
    url = `https://archive-api.open-meteo.com/v1/archive`;
    params = {
      latitude: lat,
      longitude: lon,
      start_date: startDate,
      end_date: endDate,
      hourly: ['temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 'apparent_temperature', 'wind_speed_10m', 'wind_direction_10m'].join(',')
    };
  } else {
    return callback(
      400,
      Requester.errored(jobRunID, `Unsupported service: ${service} (Only OpenMeteo supports free historical data).`)
    );
  }

  const config = { url, params };

  try {
    console.log(`📊 Fetching historical data from ${startDate} to ${endDate}...`);
    const response = await Requester.request(config);

    // Check if Vault encryption is enabled
    const vaultEnabled = process.env.VAULT_ENABLED === 'true';
    let cid, isEncrypted = false;
    
    if (vaultEnabled) {
      try {
        // Check Vault health before attempting encryption
        const vaultHealthy = await healthCheck();
        
        if (vaultHealthy) {
          console.log('🔐 Encrypting historical data with Vault...');
          
          // Create filename with timestamp
          const filename = `historical_weather_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
          
          // Create a readable stream from the weather data
          const weatherDataStream = new Readable({
            read() {
              this.push(JSON.stringify(response.data, null, 2));
              this.push(null); // End of stream
            }
          });
          
          // Encrypt and upload to IPFS
          const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
          const ipfsApiUrl = ipfsUrl.replace('/api/v0', ''); // Remove API path if present
          
          const encryptionResult = await encryptStreamToIpfs(weatherDataStream, ipfsApiUrl, 'weather-data');
          
          // Store CID mapping in Vault
          await storeCidMapping(encryptionResult.cid, {
            wrapped_dek: encryptionResult.wrapped_dek,
            key_version: encryptionResult.key_version,
            algorithm: encryptionResult.alg,
            chunk_bytes: encryptionResult.chunk_bytes,
            nonce_mode: encryptionResult.nonce_mode,
            timestamp: Date.now(),
            filename: filename,
            job_id: jobRunID,
            data_type: 'historical_weather',
            service: service,
            date_range: `${startDate} to ${endDate}`,
            coordinates: { lat, lon }
          });
          
          cid = encryptionResult.cid;
          isEncrypted = true;
          
          console.log(`✅ Historical data encrypted and stored. CID: ${cid}`);
        } else {
          console.log('⚠️ Vault unhealthy, falling back to plain IPFS storage');
          const filename = `historical_weather_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
          cid = await uploadToIPFS(JSON.stringify(response.data, null, 2), filename);
        }
      } catch (vaultError) {
        console.log(`⚠️ Vault encryption failed: ${vaultError.message}, falling back to plain IPFS`);
        const filename = `historical_weather_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
        cid = await uploadToIPFS(JSON.stringify(response.data, null, 2), filename);
      }
    } else {
      console.log('📦 Vault disabled, storing in plain IPFS');
      const filename = `historical_weather_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
      cid = await uploadToIPFS(JSON.stringify(response.data, null, 2), filename);
    }

    // Return response with encryption status
    callback(200, {
      jobRunID,
      cid: cid,
      encrypted: isEncrypted,
      service: service,
      date_range: `${startDate} to ${endDate}`,
      coordinates: { lat, lon },
      statusCode: 200
    });
  } catch (error) {
    callback(500, {
      jobRunID,
      status: 'errored',
      error: error.message || 'An error occurred',
    });
  }
};

// Handle requests for historical weather data
const handleHistoricalRequest = (req, res) => {
  // Avoid logging raw user-controlled data to prevent injection attacks
  console.log('POST /historical called');
  createHistoricalRequest(req.body, (status, result) => {
    console.log('Historical Result: ', result);
    res.status(status).json(result);
  });
};

module.exports = {
  handleHistoricalRequest,
};
