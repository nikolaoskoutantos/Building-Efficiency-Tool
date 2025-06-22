const { Requester, Validator } = require('@chainlink/external-adapter');
const { uploadToIPFS } = require('./ipfs.js');   
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

  // Save the combined response to IPFS
  const filename = `weather_data_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  const cid = await uploadToIPFS(JSON.stringify(responses, null, 2), filename);

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

module.exports = {
  handleWeatherRequest,
  handleForecastRequest,
};
