const express = require('express');
const router = express.Router();
const { handleDecryptRequest } = require('../utils/index');

/**
 * @swagger
 * /decrypt:
 *   post:
 *     summary: Decrypt data from IPFS using Vault
 *     description: Decrypt encrypted weather data stored in IPFS using HashiCorp Vault envelope encryption.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - cid
 *             properties:
 *               cid:
 *                 type: string
 *                 description: IPFS Content Identifier (CID) of the encrypted data
 *                 example: QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG
 *     responses:
 *       200:
 *         description: Data successfully decrypted
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 jobRunID:
 *                   type: string
 *                   description: Unique job run identifier
 *                 cid:
 *                   type: string
 *                   description: IPFS CID of the encrypted data
 *                 data:
 *                   type: object
 *                   description: Decrypted weather data
 *                 metadata:
 *                   type: object
 *                   properties:
 *                     timestamp:
 *                       type: string
 *                       description: Encryption timestamp
 *                     filename:
 *                       type: string
 *                       description: Original filename
 *                     job_id:
 *                       type: string
 *                       description: Original job ID
 *                     data_type:
 *                       type: string
 *                       description: Type of data (e.g., weather)
 *                     algorithm:
 *                       type: string
 *                       description: Encryption algorithm used
 *                 statusCode:
 *                   type: number
 *                   example: 200
 *       400:
 *         description: Bad request - missing CID or Vault disabled
 *       404:
 *         description: No encryption metadata found for given CID
 *       500:
 *         description: Decryption failed
 *       503:
 *         description: Vault service unhealthy
 */
router.post('/', (req, res) => handleDecryptRequest(req, res));

module.exports = router;
