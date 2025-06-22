const { Requester, Validator } = require('@chainlink/external-adapter');
const { uploadToIPFS } = require('./ipfs.js');
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
  const jobRunID = validator.validated.id;

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
    console.log(`Fetching historical data from ${startDate} to ${endDate}...`);
    const response = await Requester.request(config);

    // Save the result to IPFS
    const filename = `historical_weather_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    const cid = await uploadToIPFS(JSON.stringify(response.data, null, 2), filename);

    // Return only the CID in the response
    callback(200, {
      jobRunID,
      cid: cid, // Only the CID
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
  console.log('POST Data (Historical): ', req.body);
  createHistoricalRequest(req.body, (status, result) => {
    console.log('Historical Result: ', result);
    res.status(status).json(result);
  });
};

module.exports = {
  handleHistoricalRequest,
};
