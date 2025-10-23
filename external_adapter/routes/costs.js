const express = require('express');
const router = express.Router();
const { handleCostsUpload } = require('../utils/uploadCosts');

/**
 * @swagger
 * /costs:
 *   post:
 *     summary: Trigger server-side cost upload
 *     description: Trigger the adapter to read the cost file pointed to by the `COST_DATA_SOURCE` environment variable, encrypt it (Vault required) and upload to IPFS. The caller must provide a `job_id` string in the request body.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - job_id
 *             properties:
 *               job_id:
 *                 type: string
 *                 description: Job identifier to associate with this upload
 *     responses:
 *       200:
 *         description: File encrypted and uploaded to IPFS
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 jobRunID:
 *                   type: string
 *                 cid:
 *                   type: string
 *                 filename:
 *                   type: string
 *                 statusCode:
 *                   type: integer
 *       400:
 *         description: Bad request (missing job_id or COST_DATA_SOURCE)
 *       503:
 *         description: Vault is not healthy or not available
 *       500:
 *         description: Encryption or upload failed
 */
router.post('/', express.json(), (req, res) => handleCostsUpload(req, res));

module.exports = router;
