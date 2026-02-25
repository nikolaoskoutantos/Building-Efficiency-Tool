const express = require('express');
const router = express.Router();
const { handleHistoricalRequest } = require('../utils/historicalRequest');

/**
 * @swagger
 * /historical:
 *   post:  
 *     summary: Fetch historical weather data
 *     description: Fetch historical weather data from OpenMeteo for a given date range.
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
 *                     description: The weather service to fetch historical data from.
 *                     enum: [openmeteo]
 *                   lat:
 *                     type: number
 *                     description: Latitude of the location.
 *                   lon:
 *                     type: number
 *                     description: Longitude of the location.
 *                   start_date:
 *                     type: string
 *                     format: date
 *                     description: Start date for historical data (YYYY-MM-DD). Optional.
 *                   end_date:
 *                     type: string
 *                     format: date
 *                     description: End date for historical data (YYYY-MM-DD). Optional.
 *     responses:
 *       200:
 *         description: Historical weather data fetched successfully
 *       400:
 *         description: Bad request due to missing parameters.
 *       500:
 *         description: Error fetching historical data
 */
router.post('/', (req, res) => handleHistoricalRequest(req, res));

module.exports = router;
