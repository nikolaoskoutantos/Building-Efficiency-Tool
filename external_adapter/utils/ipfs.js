const path = require('path');
const fs = require('fs');
const tmp = require('tmp');
const FormData = require('form-data');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

const IPFS_URL = process.env.IPFS_URL || 'http://127.0.0.1:5001/api/v0';
const IPFS_AUTH_TOKEN = process.env.IPFS_AUTH_TOKEN || ''; // unified auth token

let ipfsClientPromise = null;
const isLocalNode = IPFS_URL.includes('127.0.0.1') || IPFS_URL.includes('localhost');

if (isLocalNode) {
  ipfsClientPromise = (async () => {
    const { create } = await import('ipfs-http-client');
    return create({ url: IPFS_URL });
  })();
}

const uploadToIPFS = async (data, filename) => {
  try {
    if (isLocalNode && ipfsClientPromise) {
      const ipfs = await ipfsClientPromise;
      const { cid } = await ipfs.add({ path: filename, content: data }, { pin: true });

      const mfsPath = `/weather_data/${filename}`;
      await ipfs.files.write(mfsPath, data, { create: true, parents: true, truncate: true });

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
      const mkdirResponse = await fetch(`${IPFS_URL}/files/mkdir?arg=/weather_data&parents=true`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${IPFS_AUTH_TOKEN}`,
        },
      });
      
      const mfsPath = `/weather_data/${filename}`;
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
};
