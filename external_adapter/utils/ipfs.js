const path = require('node:path');
const fs = require('node:fs');
const tmp = require('tmp');
const FormData = require('form-data');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

const IPFS_URL = process.env.IPFS_URL || 'http://127.0.0.1:5001/api/v0';
const IPFS_AUTH_TOKEN = process.env.IPFS_AUTH_TOKEN || ''; // unified auth token

let ipfsClient = null;
const isLocalNode = IPFS_URL.includes('127.0.0.1') || IPFS_URL.includes('localhost');

// Initialize IPFS client asynchronously (not at module load)
async function getIpfsClient() {
  if (!isLocalNode) return null;
  if (ipfsClient) return ipfsClient;
  
  try {
    const { create } = await import('ipfs-http-client');
    ipfsClient = create({ url: IPFS_URL });
    return ipfsClient;
  } catch (error) {
    console.warn('Failed to initialize local IPFS client:', error.message);
    return null;
  }
}

// New: Precompute CID from buffer (async, using multiformats)
async function precomputeCID(buffer) {
  // Lazy-load multiformats to avoid extra deps if not used
  const { CID } = await import('multiformats/cid');
  const { sha256 } = await import('multiformats/hashes/sha2');
  const hash = await sha256.digest(buffer);
  // 0x55 = raw, or use appropriate codec for your data
  return CID.createV1(0x55, hash).toString();
}

const uploadToIPFS = async (data, filename, mfsDir = 'weather_data') => {
  try {
    const client = await getIpfsClient();
    if (isLocalNode && client) {
      const { cid } = await client.add({ path: filename, content: data }, { pin: true });

      const mfsPath = `/${mfsDir}/${filename}`;
      await client.files.write(mfsPath, data, { create: true, parents: true, truncate: true });

      console.log(`✅ Local IPFS: Stored '${filename}' with CID: ${cid}`);
      return cid.toString();
    }

    // Filebase-compatible flow (RPC API)
    const tmpFile = tmp.fileSync({ postfix: path.extname(filename) });
    fs.writeFileSync(tmpFile.name, data);

    const form = new FormData();
    form.append('file', fs.createReadStream(tmpFile.name), filename);

    const response = await fetch(`${IPFS_URL}/add?pin=true`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${IPFS_AUTH_TOKEN}`,
        ...form.getHeaders(),
      },
      body: form,
    });

    tmpFile.removeCallback();

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errText}`);
    }

    const json = await response.json();
    const cid = json.Hash;
    console.log(`✅ Filebase: Uploaded '${filename}' with CID: ${cid}`);
    
    // Add to MFS (Mutable File System) so it shows in FILES section
    try {
      // First create the directory if it doesn't exist
      await fetch(`${IPFS_URL}/files/mkdir?arg=/${mfsDir}&parents=true`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${IPFS_AUTH_TOKEN}`,
        },
      });
      
      const mfsPath = `/${mfsDir}/${filename}`;
      const cpResponse = await fetch(`${IPFS_URL}/files/cp?arg=/ipfs/${cid}&arg=${mfsPath}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${IPFS_AUTH_TOKEN}`,
        },
      });
      
      if (cpResponse.ok) {
        console.log(`📁 Added to MFS: ${mfsPath}`);
      } else {
        console.log(`⚠️ MFS add failed: ${cpResponse.statusText}`);
      }
    } catch (mfsError) {
      console.log(`⚠️ MFS add error: ${mfsError.message}`);
    }
    
    return cid;
  } catch (err) {
    console.error('❌ Error uploading to IPFS:', err.message);
    throw new Error('Failed to upload data to IPFS');
  }
};

const retrieveFromIPFS = async (cid) => {
  try {
    const url = `https://ipfs.filebase.io/ipfs/${cid}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.text();
  } catch (err) {
    console.error('❌ Retrieve error:', err.message);
    throw new Error('Failed to retrieve IPFS content');
  }
};

module.exports = {
  uploadToIPFS,
  retrieveFromIPFS,
  precomputeCID, // New: export the precomputeCID function
};
