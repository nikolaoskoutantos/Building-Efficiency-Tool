const express = require('express');
const router = express.Router();
const { handleWeatherRequest } = require('../utils/index');

/**
 * @swagger
 * /:
 *   post:
 *     summary: Fetch current weather data
 *     description: Fetch current weather data from OpenWeather and Open-Meteo.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - id
 *               - data
 *             properties:
 *               id:
 *                 type: string
 *                 description: Job Run ID
 *               data:
 *                 type: object
 *                 required:
 *                   - service
 *                   - lat
 *                   - lon
 *                 properties:
 *                   service:
 *                     type: string
 *                     description: The weather service to fetch data from.
 *                     enum: [openweather, openmeteo]
 *                   lat:
 *                     type: number
 *                     description: Latitude of the location.
 *                   lon:
 *                     type: number
 *                     description: Longitude of the location.
 *     responses:
 *       200:
 *         description: Weather data fetched successfully from both OpenWeather and Open-Meteo
 *       400:
 *         description: Bad request due to missing parameters.
 *       500:
 *         description: Error fetching weather data
 */
router.post('/', (req, res) => handleWeatherRequest(req, res));

module.exports = router;
