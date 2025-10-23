const express = require('express');
const router = express.Router();
const { handleHealthRequest } = require('../utils/index');

/**
 * @swagger
 * /health:
 *   get:
 *     summary: System health check
 *     description: Check the health status of all system components including Vault, IPFS, and weather APIs.
 *     responses:
 *       200:
 *         description: All systems healthy
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 jobRunID:
 *                   type: string
 *                   description: Unique job run identifier
 *                 overall_status:
 *                   type: string
 *                   enum: [healthy, degraded, error]
 *                   description: Overall system health status
 *                 timestamp:
 *                   type: string
 *                   format: date-time
 *                   description: Health check timestamp
 *                 services:
 *                   type: object
 *                   properties:
 *                     vault:
 *                       type: object
 *                       properties:
 *                         status:
 *                           type: string
 *                           enum: [healthy, unhealthy, disabled, error]
 *                         endpoint:
 *                           type: string
 *                         enabled:
 *                           type: boolean
 *                     ipfs:
 *                       type: object
 *                       properties:
 *                         status:
 *                           type: string
 *                           enum: [healthy, unhealthy, error]
 *                         endpoint:
 *                           type: string
 *                         version:
 *                           type: string
 *                     openweather:
 *                       type: object
 *                       properties:
 *                         status:
 *                           type: string
 *                           enum: [healthy, unhealthy, not_configured]
 *                         api_key_configured:
 *                           type: boolean
 *                     openmeteo:
 *                       type: object
 *                       properties:
 *                         status:
 *                           type: string
 *                           enum: [healthy, unhealthy]
 *       503:
 *         description: One or more services degraded
 *       500:
 *         description: Health check failed
 */
router.get('/', (req, res) => handleHealthRequest(req, res));

module.exports = router;
