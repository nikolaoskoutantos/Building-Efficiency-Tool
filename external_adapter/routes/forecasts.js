const express = require('express');
const router = express.Router();
const { handleForecastRequest } = require('../utils/index');

/**
 * @swagger
 * /forecasts:
 *   post:
 *     summary: Fetch weather forecast data
 *     description: Fetch weather forecast data using Open-Meteo.
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
 *                     description: The weather service to fetch forecast data from.
 *                     enum: [openmeteo]
 *                   lat:
 *                     type: number
 *                     description: Latitude of the location.
 *                   lon:
 *                     type: number
 *                     description: Longitude of the location.
 *     responses:
 *       200:
 *         description: Forecast data fetched successfully
 *       400:
 *         description: Bad request due to missing parameters.
 *       500:
 *         description: Error fetching forecast data
 */
// Utility for timestamped logs
function logWithTimestamp(...args) {
	console.log(`[${new Date().toISOString()}]`, ...args);
}

router.post('/', async (req, res) => {
	// Avoid logging raw user-controlled data to prevent injection attacks
	logWithTimestamp('POST /forecasts called');
	try {
		// Call the async handler and await result
		await require('../utils/index').handleForecastRequestWithLogging(req, res, logWithTimestamp);
	} catch (err) {
		logWithTimestamp('❌ Unhandled error in /forecasts:', err.message);
		res.status(500).json({ status: 'errored', error: 'Internal server error', statusCode: 500 });
	}
});

module.exports = router;
