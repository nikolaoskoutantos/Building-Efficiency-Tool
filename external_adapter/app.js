const { handleWeatherRequest, handleForecastRequest,  } = require('./utils/index');
const {handleHistoricalRequest} = require('./utils/historicalRequest')
const express = require('express');
const bodyParser = require('body-parser');
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');
const dotenv = require('dotenv');
const apiKeyAuth = require('./middleware/apiKeyAuth');

const app = express();
const port = process.env.PORT || 8080;

// Load environment variables from .env file
dotenv.config();

// Middleware
app.use(bodyParser.json());
app.use(apiKeyAuth);

// Swagger definition
const swaggerDefinition = {
  openapi: '3.0.0',
  info: {
    title: 'Weather External Adapter API',
    version: '1.0.0',
    description: 'An API to fetch weather information using Chainlink External Adapter with multiple services.',
  },
  servers: [
    {
      url: `http://localhost:${port}`, // Replace with your server's base URL
    },
  ],
  components: {
    securitySchemes: {
      ApiKeyAuth: {
        type: 'apiKey',
        in: 'header',
        name: 'x-api-key',
        description: 'Enter your API key',
      },
    },
  },
  security: [{ ApiKeyAuth: [] }],
};

// Swagger options
const options = {
  swaggerDefinition,
  apis: ['./app.js'], // Path to this file for endpoint documentation
};

// Generate Swagger docs
const swaggerSpec = swaggerJsdoc(options);

// Serve Swagger UI
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// Optional: Serve raw Swagger JSON
app.get('/swagger.json', (req, res) => {
  res.json(swaggerSpec);
});

// Health check endpoint
/**
 * @swagger
 * /health:
 *   get:
 *     summary: Health check for the server
 *     responses:
 *       200:
 *         description: Server is up and running!
 */
app.get('/health', (req, res) => {
  res.status(200).send('Server is up and running!');//Αdd timestamp to the response.
});

// Main POST endpoint for current weather (Fetches from BOTH OpenMeteo & OpenWeather)
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
app.post('/', handleWeatherRequest);

// New POST endpoint for weather forecasts (ONLY OpenMeteo)
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
app.post('/forecasts', handleForecastRequest);

// New POST endpoint for historical weather data (ONLY OpenMeteo)
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
app.post('/historical', handleHistoricalRequest);

// Start the server
app.listen(port, '0.0.0.0', () => {
  console.log(`Server is listening on port ${port}`);
  console.log(`Swagger docs available at http://localhost:${port}/api-docs`);
});
