const { Readable } = require('stream');
const { encryptStreamToIpfs, storeCidMapping, healthCheck } = require('./vault');
const { v4: uuidv4 } = require('uuid');

async function handleCostsUpload(req, res) {
  const jobRunID = uuidv4();
  try {
    const job_id = req.body && req.body.job_id;
    if (!job_id || typeof job_id !== 'string' || job_id.trim() === '') {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'Missing or invalid job_id in request body', statusCode: 400 });
    }

    // Determine the source file from COST_DATA_SOURCE env
    const costSource = process.env.COST_DATA_SOURCE;
    if (!costSource) {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'COST_DATA_SOURCE not configured', statusCode: 400 });
    }

    const fs = require('fs');
    const path = require('path');
    const resolvedPath = path.isAbsolute(costSource) ? costSource : path.resolve(process.cwd(), costSource);
    if (!fs.existsSync(resolvedPath)) {
      return res.status(400).json({ jobRunID, status: 'errored', error: `Cost file not found at ${resolvedPath}`, statusCode: 400 });
    }

    const fileStream = fs.createReadStream(resolvedPath);
    const originalName = path.basename(resolvedPath);

    const vaultEnabled = process.env.VAULT_ENABLED === 'true';
    if (!vaultEnabled) {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'Vault is disabled; cost uploads require encryption', statusCode: 400 });
    }

    const vaultHealthy = await healthCheck();
    if (!vaultHealthy) {
      return res.status(503).json({ jobRunID, status: 'errored', error: 'Vault is not healthy', statusCode: 503 });
    }

    try {
      const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
      const ipfsApiUrl = ipfsUrl.replace('/api/v0', '');
  const result = await encryptStreamToIpfs(fileStream, ipfsApiUrl, process.env.VAULT_ENCRYPTION_KEY || 'cost-controller', undefined, 'costs');

      await storeCidMapping(result.cid, {
        wrapped_dek: result.wrapped_dek,
        key_version: result.key_version,
        algorithm: result.alg,
        chunk_bytes: result.chunk_bytes,
        nonce_mode: result.nonce_mode,
        timestamp: Date.now(),
        filename: originalName,
        job_id: job_id,
        data_type: 'costs'
      });

      return res.status(200).json({ jobRunID, cid: result.cid, filename: originalName, statusCode: 200 });
    } catch (e) {
      console.error('Vault encrypt+upload failed (costs):', e.stack || e.message);
      return res.status(500).json({ jobRunID, status: 'errored', error: `Encryption/upload failed: ${e.message}`, statusCode: 500 });
    }
  } catch (error) {
    console.error('handleCostsUpload failed:', error.message);
    return res.status(500).json({ jobRunID, status: 'errored', error: error.message, statusCode: 500 });
  }
}

module.exports = { handleCostsUpload };
