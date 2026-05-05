const express = require('express');
const router = express.Router();
const { getBuildingLatLon } = require('../utils/buildchain_dkg');
const { handleWeatherRequestWithLogging, handleForecastRequestWithLogging } = require('../utils/index');
const { handleHistoricalRequest } = require('../utils/historicalRequest');

function logWithTimestamp(...args) {
  console.log(`[${new Date().toISOString()}]`, ...args);
}

// Resolves the buildingDID to lat/lon and injects them into req.body.data.
// Returns false and sends an error response if resolution fails.
async function resolveDID(req, res) {
  const { buildingDID } = req.body?.data || {};

  if (!buildingDID || typeof buildingDID !== 'string') {
    res.status(400).json({
      status: 'errored',
      error: 'Missing or invalid "buildingDID" in data object',
      statusCode: 400,
    });
    return false;
  }

  let lat, lon;
  try {
    ({ lat, lon } = await getBuildingLatLon(buildingDID));
  } catch (err) {
    logWithTimestamp(`[WeatherByDID] Failed to resolve DID: ${err.message}`);
    res.status(502).json({
      status: 'errored',
      error: `Could not resolve building location for DID: ${err.message}`,
      statusCode: 502,
    });
    return false;
  }

  req.body.data = { ...req.body.data, lat, lon };
  return true;
}

/**
 * @swagger
 * /weather/building/:
 *   post:
 *     summary: Fetch current weather by building DID
 *     description: Resolves the building's lat/lon from its DID, then fetches current weather from OpenWeather and Open-Meteo.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [id, data]
 *             properties:
 *               id:
 *                 type: string
 *               data:
 *                 type: object
 *                 required: [buildingDID]
 *                 properties:
 *                   buildingDID:
 *                     type: string
 *                     description: DID of the building.
 *                   service:
 *                     type: string
 *                     enum: [openweather, openmeteo]
 *     responses:
 *       200:
 *         description: Current weather data fetched successfully
 *       400:
 *         description: Missing or invalid buildingDID
 *       502:
 *         description: Could not resolve building location from Buildchain API
 *       500:
 *         description: Internal server error
 */
router.post('/', async (req, res) => {
  logWithTimestamp('[WeatherByDID] POST /weather/building/ called');
  if (!await resolveDID(req, res)) return;
  await handleWeatherRequestWithLogging(req, res, logWithTimestamp);
});

/**
 * @swagger
 * /weather/building/forecasts:
 *   post:
 *     summary: Fetch weather forecast by building DID
 *     description: Resolves the building's lat/lon from its DID, then fetches forecast data from Open-Meteo.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [id, data]
 *             properties:
 *               id:
 *                 type: string
 *               data:
 *                 type: object
 *                 required: [buildingDID]
 *                 properties:
 *                   buildingDID:
 *                     type: string
 *                     description: DID of the building.
 *                   service:
 *                     type: string
 *                     enum: [openmeteo]
 *     responses:
 *       200:
 *         description: Forecast data fetched successfully
 *       400:
 *         description: Missing or invalid buildingDID
 *       502:
 *         description: Could not resolve building location from Buildchain API
 *       500:
 *         description: Internal server error
 */
router.post('/forecasts', async (req, res) => {
  logWithTimestamp('[WeatherByDID] POST /weather/building/forecasts called');
  if (!await resolveDID(req, res)) return;
  await handleForecastRequestWithLogging(req, res, logWithTimestamp);
});

/**
 * @swagger
 * /weather/building/historical:
 *   post:
 *     summary: Fetch historical weather by building DID
 *     description: Resolves the building's lat/lon from its DID, then fetches historical weather data from Open-Meteo.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [id, data]
 *             properties:
 *               id:
 *                 type: string
 *               data:
 *                 type: object
 *                 required: [buildingDID]
 *                 properties:
 *                   buildingDID:
 *                     type: string
 *                     description: DID of the building.
 *                   service:
 *                     type: string
 *                     enum: [openmeteo]
 *                   start_date:
 *                     type: string
 *                     format: date
 *                     description: Start date (YYYY-MM-DD). Defaults to 7 days ago.
 *                   end_date:
 *                     type: string
 *                     format: date
 *                     description: End date (YYYY-MM-DD). Defaults to today.
 *     responses:
 *       200:
 *         description: Historical weather data fetched successfully
 *       400:
 *         description: Missing or invalid buildingDID
 *       502:
 *         description: Could not resolve building location from Buildchain API
 *       500:
 *         description: Internal server error
 */
router.post('/historical', async (req, res) => {
  logWithTimestamp('[WeatherByDID] POST /weather/building/historical called');
  if (!await resolveDID(req, res)) return;
  handleHistoricalRequest(req, res);
});

module.exports = router;
