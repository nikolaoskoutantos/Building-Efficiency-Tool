/*
  Script: encrypt_and_upload_excel.js
  Purpose: Read cost data (Excel file or later other source) from a data source, encrypt it using Vault envelope encryption via encryptStreamToIpfs, store KV mapping, and print the CID.

  Usage:
    # from repository root
    cd external_adapter
    # Preferred: set COST_DATA_SOURCE environment variable to the file path
    $env:COST_DATA_SOURCE='..\data\cost_controller.xlsx'
    node scripts/encrypt_and_upload_excel.js

    # Or pass path as CLI arg (fallback):
    node scripts/encrypt_and_upload_excel.js <relative-path-to-excel>

  Environment variables required when VAULT_ENABLED=true:
    VAULT_ENABLED=true, VAULT_ENDPOINT, VAULT_TOKEN, VAULT_ENCRYPTION_KEY (optional), VAULT_KV_MOUNT (optional)
    IPFS_URL, IPFS_AUTH_TOKEN
    COST_DATA_SOURCE (optional) - path to Excel or other data source
*/

const path = require('path');
const fs = require('fs');
const { Readable } = require('stream');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const { encryptStreamToIpfs, storeCidMapping, getDataKey, healthCheck } = require('../utils/vault');

async function main() {
  try {
  // Priority: COST_DATA_SOURCE env var > CLI arg > default file
  const envPath = process.env.COST_DATA_SOURCE;
  const arg = process.argv[2];
  const defaultFile = path.resolve(__dirname, '../../data/cost_controller.xlsx');
  const filePath = envPath ? path.resolve(process.cwd(), envPath) : (arg ? path.resolve(process.cwd(), arg) : defaultFile);

    if (!fs.existsSync(filePath)) {
      console.error('File not found:', filePath);
      process.exit(2);
    }

    const vaultEnabled = process.env.VAULT_ENABLED === 'true';
    const ipfsUrl = process.env.IPFS_URL || 'http://127.0.0.1:5001';
    const ipfsApiUrl = ipfsUrl.replace('/api/v0', '');
    const filename = path.basename(filePath);

    const fileStream = fs.createReadStream(filePath);

    if (!vaultEnabled) {
      console.error('Vault is not enabled. This script requires Vault to perform envelope encryption. Set VAULT_ENABLED=true');
      process.exit(3);
    }

    const vaultHealthy = await healthCheck();
    if (!vaultHealthy) {
      console.error('Vault appears unhealthy. Check VAULT_ENDPOINT and VAULT_TOKEN.');
      process.exit(4);
    }

    console.log('Encrypting and uploading', filename);

    const result = await encryptStreamToIpfs(fileStream, ipfsApiUrl, process.env.VAULT_ENCRYPTION_KEY || 'cost-controller');

    // Store mapping in KV
    await storeCidMapping(result.cid, {
      wrapped_dek: result.wrapped_dek,
      key_version: result.key_version,
      algorithm: result.alg,
      chunk_bytes: result.chunk_bytes,
      nonce_mode: result.nonce_mode,
      timestamp: Date.now(),
      filename,
      job_id: `local-script-${Date.now()}`,
      data_type: 'excel_upload'
    });

    console.log('Upload complete. CID:', result.cid);
    process.exit(0);
  } catch (err) {
    console.error('Script failed:', err.message);
    console.error(err.stack);
    process.exit(1);
  }
}

main();
