const express = require('express');
const bodyParser = require('body-parser');
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');
const dotenv = require('dotenv');
const path = require('path');
const apiKeyAuth = require('./middleware/apiKeyAuth');
const cors = require('cors');

// Load environment variables
dotenv.config();

// Normalize COST_DATA_SOURCE so common .env formatting mistakes (spaces, surrounding quotes,
// backslashes) don't break file resolution. We convert backslashes to forward slashes and
// strip surrounding quotes/whitespace.
if (process.env.COST_DATA_SOURCE) {
  try {
    let s = process.env.COST_DATA_SOURCE;
    s = s.trim();
    // remove surrounding single or double quotes
    s = s.replace(/^['"]+|['"]+$/g, '');
    // normalize Windows backslashes to forward slashes for consistent resolution
    s = s.replace(/\\\\/g, '/').replace(/\\/g, '/');
    process.env.COST_DATA_SOURCE = s;
    const resolved = path.resolve(process.cwd(), s || '');
    console.log('COST_DATA_SOURCE (normalized):', process.env.COST_DATA_SOURCE);
    console.log('COST_DATA_SOURCE resolved path:', resolved);
  } catch (err) {
    console.warn('Failed to normalize COST_DATA_SOURCE:', err && err.message ? err.message : err);
  }
}

const app = express();

// CORS setup
let allowedOrigins = process.env.CORS_ORIGIN || '*';
if (allowedOrigins !== '*') allowedOrigins = allowedOrigins.split(',').map(origin => origin.trim());
app.use(cors({ origin: allowedOrigins }));

// Middleware
app.use(bodyParser.json());
app.use(apiKeyAuth);

// Swagger (minimal setup). Route documentation can be moved into route modules later.
const port = process.env.PORT || 8080;
const swaggerDefinition = {
  openapi: '3.0.0',
  info: {
    title: 'Weather External Adapter API',
    version: '1.0.0',
    description: 'An API to fetch weather information using Chainlink External Adapter.',
  },
  servers: [{ url: `http://localhost:${port}` }],
  components: {
    securitySchemes: {
      ApiKeyAuth: {
        type: 'apiKey',
        in: 'header',
        name: 'x-api-key',
        description: 'API key required to access protected endpoints. Set your key here.'
      }
    }
  },
  security: [ { ApiKeyAuth: [] } ],
};

const options = {
  swaggerDefinition,
  apis: ['./routes/*.js', './app.js'],
};
const swaggerSpec = swaggerJsdoc(options);
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// Expose raw swagger JSON
app.get('/swagger.json', (req, res) => {
  res.json(swaggerSpec);
});

// Mount route modules
const weatherRouter = require('./routes/weather');
const forecastsRouter = require('./routes/forecasts');
const historicalRouter = require('./routes/historical');
const decryptRouter = require('./routes/decrypt');
const healthRouter = require('./routes/health');
const costsRouter = require('./routes/costs');

app.use('/health', healthRouter);
app.use('/', weatherRouter);
app.use('/forecasts', forecastsRouter);
app.use('/historical', historicalRouter);
app.use('/decrypt', decryptRouter);
app.use('/costs', costsRouter);

// Export app for server.js (and tests)
module.exports = app;
