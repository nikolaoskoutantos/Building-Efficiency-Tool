const express = require('express');
const router = express.Router();
const { handleCostsUpload } = require('../utils/uploadCosts');

/**
 * @swagger
 * /costs:
 *   post:
 *     summary: Trigger server-side cost upload
 *     description: Trigger the adapter to read the cost file pointed to by the `COST_DATA_SOURCE` environment variable, optionally filter by productIds, encrypt it (Vault required) and upload to IPFS.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - job_id
 *               - buyer
 *               - pubKey
 *             properties:
 *               job_id:
 *                 type: string
 *                 description: Job identifier to associate with this upload
 *               buyer:
 *                 type: string
 *                 description: Buyer ethereum address
 *               pubKey:
 *                 type: string
 *                 description: Public key for the buyer
 *               productIds:
 *                 type: array
 *                 items:
 *                   type: integer
 *                 description: Optional array of product IDs to filter. If empty or not provided, entire file is uploaded.
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
 *                 filtered:
 *                   type: boolean
 *                 productCount:
 *                   type: integer
 *                 statusCode:
 *                   type: integer
 *       400:
 *         description: Bad request (missing required fields or COST_DATA_SOURCE)
 *       503:
 *         description: Vault is not healthy or not available
 *       500:
 *         description: Encryption or upload failed
 */
router.post('/', express.json(), (req, res) => handleCostsUpload(req, res));

module.exports = router;
