/**
 * HashiCorp Vault + Envelope Encryption (DEK) for IPFS
 * - Gets disposable DEKs from Vault Transit
 * - Encrypts/Decrypts locally with AES-256-GCM (streaming, chunked)
 * - Uploads/reads ciphertext from IPFS
 *
 * npm i node-vault axios form-data dotenv
 */

const vault = require('node-vault');
const axios = require('axios');
const FormData = require('form-data');
const { randomBytes, createCipheriv, createDecipheriv } = require('crypto');
const { Readable, PassThrough } = require('stream');
require('dotenv').config();

const DEFAULT_TRANSIT_KEY = process.env.VAULT_ENCRYPTION_KEY || 'weather-data';
const DEFAULT_KV_MOUNT = process.env.VAULT_KV_MOUNT || 'kv'; // if you use KV v2
const DEFAULT_TRANSIT_MOUNT = process.env.VAULT_TRANSIT_MOUNT || 'transit'; // allow non-default transit mount
const DEFAULT_CHUNK_BYTES = Number(process.env.CHUNK_BYTES) || (4 * 1024 * 1024); // 4MB

class VaultService {
  constructor() {
    this.client = null;
    this.isInitialized = false;
    this.initializeVault();
  }

  initializeVault() {
    try {
      const vaultConfig = {
        endpoint: process.env.VAULT_ENDPOINT || 'http://localhost:8200',
        token: process.env.VAULT_TOKEN || 'qoe-dev-token-2025'
      };
      this.client = vault(vaultConfig);
      this.isInitialized = true;
      console.log('✅ Vault client initialized');
      console.log(`🔗 Vault endpoint: ${vaultConfig.endpoint}`);
    } catch (error) {
      console.error('❌ Failed to initialize Vault client:', error.message);
      this.isInitialized = false;
    }
  }

  async healthCheck() {
    if (!this.isInitialized) return false;
    try {
      const h = await this.client.health();
      return h.initialized && !h.sealed;
    } catch (e) {
      console.error('❌ Vault health check failed:', e.message);
      return false;
    }
  }

  // ---------- SMALL PAYLOAD HELPERS (keep for tiny JSON only) ----------
  async encryptData(data, keyName = null) {
    const encryptionKey = keyName || DEFAULT_TRANSIT_KEY;
    const plaintext = Buffer.from(JSON.stringify(data)).toString('base64');
    const res = await this.client.write(`${DEFAULT_TRANSIT_MOUNT}/encrypt/${encryptionKey}`, { plaintext });
    return res.data.ciphertext; // "vault:vX:..."
  }

  async decryptData(ciphertext, keyName = null) {
    const encryptionKey = keyName || DEFAULT_TRANSIT_KEY;
    const res = await this.client.write(`${DEFAULT_TRANSIT_MOUNT}/decrypt/${encryptionKey}`, { ciphertext });
    return JSON.parse(Buffer.from(res.data.plaintext, 'base64').toString('utf8'));
  }

  // ---------- ENVELOPE ENCRYPTION CORE ----------
  // 1) Get one-time DEK for local crypto
  async getDataKey(keyName = DEFAULT_TRANSIT_KEY) {
    try {
      console.log(`🔑 Requesting DEK from Vault for key: ${keyName}`);
      const res = await this.client.write(`${DEFAULT_TRANSIT_MOUNT}/datakey/plaintext/${keyName}`, {});
      console.log(`✅ DEK generated successfully`);
      return {
        dek: Buffer.from(res.data.plaintext, 'base64'),
        wrappedDek: res.data.ciphertext,      // store next to CID
        keyVersion: res.data.key_version
      };
    } catch (error) {
      console.error(`❌ DEK generation failed: ${error.message}`);
      throw error;
    }
  }

  // 2) Unwrap DEK (to decrypt later)
  async unwrapDek(wrappedDek, keyName = DEFAULT_TRANSIT_KEY) {
    const res = await this.client.write(`${DEFAULT_TRANSIT_MOUNT}/decrypt/${keyName}`, { ciphertext: wrappedDek });
    return Buffer.from(res.data.plaintext, 'base64');
  }

  // 3) Rewrap wrapped DEK after Transit rotation (no file re-encrypt)
  async rewrapDek(wrappedDek, keyName = DEFAULT_TRANSIT_KEY) {
    const res = await this.client.write(`${DEFAULT_TRANSIT_MOUNT}/rewrap/${keyName}`, { ciphertext: wrappedDek });
    return { wrappedDek: res.data.ciphertext, keyVersion: res.data.key_version };
  }

  // 4) (Optional) Rotate the Transit key (admin op)
  async rotateTransitKey(keyName = DEFAULT_TRANSIT_KEY) {
    await this.client.write(`${DEFAULT_TRANSIT_MOUNT}/keys/${keyName}/rotate`, {});
    return true;
  }

  // ---------- KV (CID → wrapped_dek mapping) ----------
  async storeCidMapping(cid, mappingObj) {
    // KV v2 write: <mount>/data/<path>
    const path = `${DEFAULT_KV_MOUNT}/data/files/${cid}`;
    return this.client.write(path, { data: mappingObj });
  }

  async getCidMapping(cid) {
    const path = `${DEFAULT_KV_MOUNT}/data/files/${cid}`;
    const res = await this.client.read(path);
    return res.data.data; // unwrap KV v2 payload
  }

  // ---------- STREAM ENCRYPT (random nonces, framed as [nonce(12)][ct][tag(16)] per chunk) ----------
  encryptReadable(readable, dek, chunkBytes = DEFAULT_CHUNK_BYTES) {
    const out = new PassThrough();
    let buffer = Buffer.alloc(0);

    const flushChunk = (chunk) => {
      const nonce = randomBytes(12);
      const cipher = createCipheriv('aes-256-gcm', dek, nonce);
      const ct = Buffer.concat([cipher.update(chunk), cipher.final()]);
      const tag = cipher.getAuthTag();
      // Frame: nonce(12) + ct + tag(16)
      out.write(Buffer.concat([nonce, ct, tag]));
    };

    readable.on('data', (d) => {
      // Ensure d is a Buffer
      const chunk = Buffer.isBuffer(d) ? d : Buffer.from(d);
      buffer = Buffer.concat([buffer, chunk]);
      while (buffer.length >= chunkBytes) {
        const dataChunk = buffer.subarray(0, chunkBytes);
        buffer = buffer.subarray(chunkBytes);
        flushChunk(dataChunk);
      }
    });

    readable.on('end', () => {
      if (buffer.length > 0) flushChunk(buffer);
      out.end();
    });

    readable.on('error', (e) => out.destroy(e));
    return out;
  }

  // ---------- STREAM DECRYPT (parse frames of [nonce(12)][ct][tag(16)]) ----------
  decryptReadable(readable, dek, chunkBytes = DEFAULT_CHUNK_BYTES) {
    const out = new PassThrough();
    let buffer = Buffer.alloc(0);

    // minimal frame size when plaintext chunk is full: 12 + chunkBytes + 16
    // last chunk may be shorter (>= 12+16)
    const MIN_OVERHEAD = 12 + 16;

    const tryDrainFrames = (final = false) => {
      // For all complete full-sized frames:
      while (buffer.length >= (chunkBytes + MIN_OVERHEAD)) {
        const nonce = buffer.subarray(0, 12);
        const ctWithTag = buffer.subarray(12, 12 + chunkBytes + 16);
        buffer = buffer.subarray(12 + chunkBytes + 16);

        const ct = ctWithTag.subarray(0, ctWithTag.length - 16);
        const tag = ctWithTag.subarray(ctWithTag.length - 16);

        const decipher = createDecipheriv('aes-256-gcm', dek, nonce);
        decipher.setAuthTag(tag);
        const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
        out.write(pt);
      }

      // On final chunk, drain whatever remains if it's >= overhead
      if (final && buffer.length >= MIN_OVERHEAD) {
        const nonce = buffer.subarray(0, 12);
        const ct = buffer.subarray(12, buffer.length - 16);
        const tag = buffer.subarray(buffer.length - 16);

        const decipher = createDecipheriv('aes-256-gcm', dek, nonce);
        decipher.setAuthTag(tag);
        const pt = Buffer.concat([decipher.update(ct), decipher.final()]);
        out.write(pt);
        buffer = Buffer.alloc(0);
      }
    };

    readable.on('data', (d) => {
      // Ensure d is a Buffer
      const chunk = Buffer.isBuffer(d) ? d : Buffer.from(d);
      buffer = Buffer.concat([buffer, chunk]);
      tryDrainFrames(false);
    });

    readable.on('end', () => {
      tryDrainFrames(true);
      out.end();
    });

    readable.on('error', (e) => out.destroy(e));
    return out;
  }

  // ---------- END-TO-END HELPERS WITH IPFS ----------
  /**
   * Encrypt a Readable stream → upload to IPFS via /api/v0/add
   * Returns: { cid, wrapped_dek, key_version, alg, chunk_bytes, nonce_mode }
   */
  async encryptStreamToIpfs(plaintextReadable, ipfsApiUrl, keyName = DEFAULT_TRANSIT_KEY, chunkBytes = DEFAULT_CHUNK_BYTES, mfsDir = 'encrypted_data') {
    // 1) DEK from Vault (disposable)
    const { dek, wrappedDek, keyVersion } = await this.getDataKey(keyName);

    // 2) Encrypt streaming
    const cipherStream = this.encryptReadable(plaintextReadable, dek, chunkBytes);

    // 3) Upload to IPFS
    const uploadUrl = ipfsApiUrl.includes('/api/v0') ? `${ipfsApiUrl}/add` : `${ipfsApiUrl}/api/v0/add`;
    console.log(`📤 Uploading encrypted data to IPFS: ${uploadUrl}`);
    const form = new FormData();
    form.append('file', cipherStream, { filename: 'cipher.bin' });

    let res;
    try {
      res = await axios.post(`${uploadUrl}?pin=true`, form, {
        headers: {
          ...form.getHeaders(),
          'Authorization': `Bearer ${process.env.IPFS_AUTH_TOKEN}`
        },
        maxBodyLength: Infinity,
        maxContentLength: Infinity,
      });
      
      console.log(`✅ Encrypted data uploaded to IPFS with CID: ${res.data.Hash}`);
    } catch (ipfsError) {
      console.error(`❌ IPFS upload failed: ${ipfsError.message}`);
      throw ipfsError;
    }

    const cid = res.data.Hash;
    
    // Add encrypted file to MFS for visibility in FILES section
    try {
      // First create the directory if it doesn't exist
      const mkdirUrl = ipfsApiUrl.includes('/api/v0') ? `${ipfsApiUrl}/files/mkdir` : `${ipfsApiUrl}/api/v0/files/mkdir`;
      await axios.post(`${mkdirUrl}?arg=/${mfsDir}&parents=true`, {}, {
        headers: {
          'Authorization': `Bearer ${process.env.IPFS_AUTH_TOKEN}`
        }
      });
      
      const mfsPath = `/${mfsDir}/${cid}.enc`;
      const cpUrl = ipfsApiUrl.includes('/api/v0') ? `${ipfsApiUrl}/files/cp` : `${ipfsApiUrl}/api/v0/files/cp`;
      await axios.post(`${cpUrl}?arg=/ipfs/${cid}&arg=${mfsPath}`, {}, {
        headers: {
          'Authorization': `Bearer ${process.env.IPFS_AUTH_TOKEN}`
        }
      });
      console.log(`🔐📁 Added encrypted file to MFS: ${mfsPath}`);
    } catch (mfsError) {
      console.log(`⚠️ MFS add error for encrypted file: ${mfsError.message}`);
    }

    // 4) Return metadata; DO NOT persist plaintext DEK
    return {
      cid,
      wrapped_dek: wrappedDek,
      key_version: keyVersion,
      alg: 'AES-256-GCM',
      chunk_bytes: chunkBytes,
      nonce_mode: 'random' // we embed nonce per chunk
    };
  }

  /**
   * Decrypt from IPFS and pipe plaintext to a Writable (or return a Readable)
   * meta = { cid, wrapped_dek, chunk_bytes }
   */
  async decryptFromIpfsToStream(meta, ipfsApiUrl, destWritable) {
    const { cid, wrapped_dek, chunk_bytes = DEFAULT_CHUNK_BYTES } = meta;

    try {
      console.log(`🔓 Starting decryption for CID: ${cid}`);
      
      // 1) Unwrap DEK via Vault
      console.log(`🔑 Unwrapping DEK via Vault...`);
      const dek = await this.unwrapDek(wrapped_dek);
      console.log(`✅ DEK unwrapped successfully`);

      // 2) Stream ciphertext from IPFS
      const catUrl = ipfsApiUrl.includes('/api/v0') ? `${ipfsApiUrl}/cat` : `${ipfsApiUrl}/api/v0/cat`;
      console.log(`📥 Fetching encrypted data from: ${catUrl}?arg=${cid}`);
      
      const res = await axios.post(`${catUrl}?arg=${cid}`, {}, { 
        responseType: 'stream',
        headers: {
          'Authorization': `Bearer ${process.env.IPFS_AUTH_TOKEN}`
        }
      });
      console.log(`✅ IPFS response received, status: ${res.status}`);

      // 3) Decrypt streaming and pipe
      console.log(`🔐 Starting stream decryption...`);
      const plainStream = this.decryptReadable(res.data, dek, chunk_bytes);
      console.log(`✅ Stream decryption initialized`);
      
      if (destWritable) {
        plainStream.pipe(destWritable);
        return new Promise((resolve, reject) => {
          destWritable.on('finish', resolve);
          destWritable.on('error', reject);
        });
      }
      return plainStream; // caller can consume as Readable
    } catch (error) {
      console.error(`❌ Decryption error in decryptFromIpfsToStream: ${error.message}`);
      console.error(`❌ Error stack: ${error.stack}`);
      throw error;
    }
  }

  // ---------- Quick self-test (small) ----------
  async testEncryption() {
    try {
      const testData = { message: 'Hello Vault!', t: Date.now() };
      const enc = await this.encryptData(testData, DEFAULT_TRANSIT_KEY);
      const dec = await this.decryptData(enc, DEFAULT_TRANSIT_KEY);
      return JSON.stringify(testData) === JSON.stringify(dec);
    } catch (e) {
      return false;
    }
  }
}

const vaultService = new VaultService();

module.exports = {
  VaultService,
  vaultService,

  // small-payload helpers
  encryptData: (data, keyName) => vaultService.encryptData(data, keyName),
  decryptData: (ciphertext, keyName) => vaultService.decryptData(ciphertext, keyName),

  // envelope helpers
  getDataKey: (keyName) => vaultService.getDataKey(keyName),
  unwrapDek: (wrappedDek, keyName) => vaultService.unwrapDek(wrappedDek, keyName),
  rewrapDek: (wrappedDek, keyName) => vaultService.rewrapDek(wrappedDek, keyName),
  rotateTransitKey: (keyName) => vaultService.rotateTransitKey(keyName),

  // KV mapping
  storeCidMapping: (cid, obj) => vaultService.storeCidMapping(cid, obj),
  getCidMapping: (cid) => vaultService.getCidMapping(cid),

  // streaming + IPFS
  encryptStreamToIpfs: (readable, ipfsApiUrl, keyName, chunkBytes) =>
    vaultService.encryptStreamToIpfs(readable, ipfsApiUrl, keyName, chunkBytes),
  decryptFromIpfsToStream: (meta, ipfsApiUrl, destWritable) =>
    vaultService.decryptFromIpfsToStream(meta, ipfsApiUrl, destWritable),

  // health/test
  healthCheck: () => vaultService.healthCheck(),
  testEncryption: () => vaultService.testEncryption()
};
