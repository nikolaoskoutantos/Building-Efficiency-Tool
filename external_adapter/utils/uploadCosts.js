const { Readable } = require('stream');
const { encryptStreamToIpfs, storeCidMapping, healthCheck } = require('./vault');
const { v4: uuidv4 } = require('uuid');
const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');
const tmp = require('tmp');

async function handleCostsUpload(req, res) {
  const jobRunID = uuidv4();
  try {
    const { job_id, buyer, pubKey, productIds } = req.body || {};
    
    // Validate required fields
    if (!job_id || typeof job_id !== 'string' || job_id.trim() === '') {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'Missing or invalid job_id in request body', statusCode: 400 });
    }
    if (!buyer || typeof buyer !== 'string' || buyer.trim() === '') {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'Missing or invalid buyer in request body', statusCode: 400 });
    }
    if (!pubKey || typeof pubKey !== 'string' || pubKey.trim() === '') {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'Missing or invalid pubKey in request body', statusCode: 400 });
    }

    // Always use QUERY_FILE (Proforma.xlsx)
    const queryFile = process.env.QUERY_FILE;
    if (!queryFile) {
      return res.status(400).json({ jobRunID, status: 'errored', error: 'QUERY_FILE not configured', statusCode: 400 });
    }
    
    const sourceFilePath = path.isAbsolute(queryFile) ? queryFile : path.resolve(process.cwd(), queryFile);
    if (!fs.existsSync(sourceFilePath)) {
      return res.status(400).json({ jobRunID, status: 'errored', error: `Query file not found at ${sourceFilePath}`, statusCode: 400 });
    }

    const originalName = path.basename(sourceFilePath);
    let fileStream;
    let isFiltered = false;
    let productCount = 0;
    
    // Check if we need to filter by productIds
    const shouldFilter = Array.isArray(productIds) && productIds.length > 0;
    
    if (shouldFilter) {
      // Filter the Excel file by WP column
      try {
        const workbook = XLSX.readFile(sourceFilePath);
        
        // Look for the "Classification" sheet
        const sheetName = 'Classification';
        if (!workbook.SheetNames.includes(sheetName)) {
          return res.status(400).json({ 
            jobRunID, 
            status: 'errored', 
            error: `Sheet "${sheetName}" not found in Excel file. Available sheets: ${workbook.SheetNames.join(', ')}`, 
            statusCode: 400 
          });
        }
        
        const worksheet = workbook.Sheets[sheetName];
        const data = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        
        if (data.length === 0) {
          return res.status(400).json({ jobRunID, status: 'errored', error: 'Classification sheet is empty', statusCode: 400 });
        }
        
        // Find the WP column (productIds match WP values)
        const header = data[0];
        let wpColIndex = -1;
        
        for (let i = 0; i < header.length; i++) {
          const colName = String(header[i]).trim();
          if (colName === 'WP') {
            wpColIndex = i;
            break;
          }
        }
        
        if (wpColIndex === -1) {
          return res.status(400).json({ 
            jobRunID, 
            status: 'errored', 
            error: 'Could not find "WP" column in Classification sheet', 
            statusCode: 400 
          });
        }
        
        // Filter rows: keep header + rows matching productIds (WP column)
        const filteredData = [header]; // Keep header
        for (let i = 1; i < data.length; i++) {
          const row = data[i];
          const wpValue = row[wpColIndex];
          if (productIds.includes(Number(wpValue))) {
            filteredData.push(row);
          }
        }
        
        productCount = filteredData.length - 1; // Exclude header
        
        if (productCount === 0) {
          return res.status(400).json({ 
            jobRunID, 
            status: 'errored', 
            error: `No products found matching IDs: ${productIds.join(', ')}`, 
            statusCode: 400 
          });
        }
        
        // Create new workbook preserving all sheets, but with filtered Classification sheet
        const newWorkbook = XLSX.utils.book_new();
        
        // Copy all sheets from original workbook
        for (const originalSheetName of workbook.SheetNames) {
          if (originalSheetName === sheetName) {
            // Replace Classification sheet with filtered data
            const newWorksheet = XLSX.utils.aoa_to_sheet(filteredData);
            XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, sheetName);
          } else {
            // Keep other sheets as-is
            const originalSheet = workbook.Sheets[originalSheetName];
            XLSX.utils.book_append_sheet(newWorkbook, originalSheet, originalSheetName);
          }
        }
        
        // Write to buffer in memory (no disk write)
        const excelBuffer = XLSX.write(newWorkbook, { type: 'buffer', bookType: 'xlsx' });
        
        // Create stream from buffer
        fileStream = Readable.from(excelBuffer);
        isFiltered = true;
        
      } catch (filterError) {
        console.error('Error filtering Excel file:', filterError);
        return res.status(500).json({ 
          jobRunID, 
          status: 'errored', 
          error: `Failed to filter Excel file: ${filterError.message}`, 
          statusCode: 500 
        });
      }
    } else {
      // No filtering - upload full Proforma.xlsx as-is
      fileStream = fs.createReadStream(sourceFilePath);
    }

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
      
      // TODO: If pubKey is provided, we should:
      // 1. Encrypt the file stream as we do now (using Vault encryption)
      // 2. Re-encrypt the DEK (data encryption key) of the encrypted CID with the user's public key
      // 3. Return the re-encrypted DEK in wrappedDEK field
      // For now, wrappedDEK returns empty string until this encryption logic is implemented
      
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
        buyer: buyer,
        pubKey: pubKey,
        productIds: productIds || [],
        filtered: isFiltered,
        productCount: isFiltered ? productCount : undefined,
        data_type: 'costs'
      });

      return res.status(200).json({ 
        cid: result.cid, 
        wrappedDEK: ""
      });
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