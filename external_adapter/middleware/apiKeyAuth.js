const dotenv = require('dotenv');
dotenv.config();

// API Key Authentication Middleware
function apiKeyAuth(req, res, next) {
  // Exclude Swagger docs and health check from auth
  if (
    req.path === '/api-docs' ||
    req.path === '/swagger.json' ||
    req.path.startsWith('/api-docs/') ||
    req.path === '/health'
  ) {
    return next();
  }
  const apiKey = req.headers['x-api-key'];
  if (!apiKey || apiKey !== process.env.API_KEY) {
    return res.status(401).json({ error: 'Unauthorized: Invalid or missing API key.' });
  }
  next();
}

module.exports = apiKeyAuth;
