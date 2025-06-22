const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const IPFS_URL = process.env.IPFS_URL || 'http://127.0.0.1:5001/api/v0';

// Dynamically import `ipfs-http-client` and initialize IPFS client
let ipfsPromise = (async () => {
    const { create } = await import('ipfs-http-client');
    return create({ url: IPFS_URL });
})();

/**
 * Uploads a file to IPFS, pins it, and adds it to IPFS Desktop "Files" section.
 * @param {Buffer | string} data - The file data to upload.
 * @param {string} filename - The filename for MFS storage.
 * @returns {Promise<string>} - The CID of the stored file.
 */
const uploadToIPFS = async (data, filename) => {
    try {
        const ipfs = await ipfsPromise;
        
        // ✅ Upload file to IPFS and pin it
        const { cid } = await ipfs.add(data, { pin: true });
        console.log(`✅ File stored in IPFS with CID: ${cid.toString()}`);

        // ✅ Add the file to IPFS Desktop "Files" using MFS
        const mfsPath = `/weather_data/${filename}`;
        await ipfs.files.write(mfsPath, data, { create: true, parents: true, truncate: true });

        console.log(`✅ File added to IPFS Desktop MFS at ${mfsPath}`);
        return cid.toString();
    } catch (error) {
        console.error('❌ Error uploading to IPFS:', error);
        throw new Error('Failed to upload data to IPFS');
    }
};

/**
 * Retrieves a file from IPFS using its CID.
 * @param {string} cid - The CID of the stored file.
 * @returns {Promise<Buffer>} - The retrieved file data.
 */
const retrieveFromIPFS = async (cid) => {
    try {
        const ipfs = await ipfsPromise;
        const stream = ipfs.cat(cid);
        let content = '';
        for await (const chunk of stream) {
            content += chunk.toString();
        }
        return content;
    } catch (error) {
        console.error('❌ Error retrieving from IPFS:', error);
        throw new Error('Failed to retrieve data from IPFS');
    }
};

module.exports = {
    uploadToIPFS,
    retrieveFromIPFS,
};
