const fs = require('node:fs');
const path = require('node:path');
const XLSX = require('xlsx');
const { uploadToIPFS } = require('./ipfs');
const vault = require('./vault');
const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

/**
 * Escape special regex characters to prevent ReDoS attacks
 * @param {string} string - User input to escape
 * @returns {string} Escaped string safe for RegExp
 */
function escapeRegex(string) {
  return String(string).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Main handler for cost group requests
 */
const handleCostGroupRequest = async (req, res) => {
  try {
    const { id: jobRunID, data } = req.body;
    
    // Validate required parameters
    if (!data?.query_type) {
      return res.status(400).json({
        jobRunID,
        status: 'errored',
        error: 'Missing required parameter: query_type is required for cost group processing',
        statusCode: 400
      });
    }

    const { 
      query_type, 
      product_type,
      query_params = {}, 
      output_format = 'json' 
    } = data;

    // Step 1: Get file content from QUERY_FILE
    let fileContent;
    try {
      fileContent = await getFileContent();
    } catch (error) {
      return res.status(400).json({
        jobRunID,
        status: 'errored',
        error: `Failed to get file content: ${error.message}`,
        statusCode: 400
      });
    }

    // Step 2: Process content based on query type
    let processedData;
    let recordCount = 0;
    try {
      // Apply product type filter first if specified
      let filteredContent = fileContent;
      if (product_type) {
        const productFilter = {
          filters: [{
            field: 'product_type', 
            operator: 'eq', 
            value: product_type
          }]
        };
        const productResult = await processQuery('filter', fileContent, productFilter);
        filteredContent = JSON.stringify(productResult.data);
      }

      const result = await processQuery(query_type, filteredContent, query_params);
      processedData = result.data;
      recordCount = result.recordCount;
    } catch (error) {
      return res.status(500).json({
        jobRunID,
        status: 'errored',
        error: `Cost group processing failed: ${error.message}`,
        statusCode: 500
      });
    }

    // Step 3: Format output
    const formattedOutput = await formatOutput(processedData, output_format);
    const outputSize = Buffer.byteLength(formattedOutput, 'utf8');

    // Step 4: Encrypt if Vault is enabled
    let finalContent = formattedOutput;
    if (process.env.VAULT_ENABLED === 'true') {
      try {
        const encrypted = await vault.encryptData(formattedOutput);
        finalContent = JSON.stringify({
          encrypted: true,
          ciphertext: encrypted.ciphertext,
          query_metadata: {
            query_type,
            processed_records: recordCount,
            output_format,
            timestamp: new Date().toISOString()
          }
        });
      } catch (error) {
        console.warn('Vault encryption failed, storing unencrypted:', error.message);
      }
    }

    // Step 5: Upload to IPFS
    const filename = `cost_group_${query_type}_${Date.now()}.${output_format}`;
    const cid = await uploadToIPFS(finalContent, filename, 'cost_groups');

    // Return success response
    res.json({
      jobRunID,
      data: {
        cid: cid.toString(),
        query_type,
        processed_records: recordCount,
        output_size: outputSize
      },
      result: cid.toString(),
      statusCode: 200
    });

  } catch (error) {
    console.error('Query request handler error:', error);
    res.status(500).json({
      jobRunID: req.body?.id,
      status: 'errored',
        error: 'Internal server error processing cost group request',
      statusCode: 500
    });
  }
};

/**
 * Get file content from QUERY_FILE environment variable
 */
const getFileContent = async () => {
  const queryFilePath = process.env.QUERY_FILE;
  if (!queryFilePath) {
    throw new Error('QUERY_FILE environment variable not set');
  }
  
  const resolvedPath = path.resolve(process.cwd(), queryFilePath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`Query file not found: ${resolvedPath}`);
  }
  
  // Check if it's an Excel file
  const fileExtension = path.extname(resolvedPath).toLowerCase();
  if (fileExtension === '.xlsx' || fileExtension === '.xls') {
    // Read Excel file and convert to JSON
    const workbook = XLSX.readFile(resolvedPath);
    const sheetName = workbook.SheetNames[0]; // Use first sheet
    const worksheet = workbook.Sheets[sheetName];
    const jsonData = XLSX.utils.sheet_to_json(worksheet);
    return JSON.stringify(jsonData);
  } else {
    // Read as text file
    return fs.readFileSync(resolvedPath, 'utf8');
  }
};

/**
 * Process content based on query type
 */
const processQuery = async (queryType, content, params) => {
  let data;
  
  // Try to parse content as JSON first, fallback to text processing
  try {
    data = JSON.parse(content);
  } catch {
    // If not JSON, treat as text and convert to array of lines for processing
    data = content.split('\n').map(line => ({ line: line.trim() })).filter(item => item.line);
  }

  switch (queryType) {
    case 'filter':
      return applyFilters(data, params.filters || []);
      
    case 'transform':
      return applyTransforms(data, params.transforms || []);
      
    case 'search':
      return applySearch(data, params.search_terms || []);
      
    case 'extract':
      return applyExtraction(data, params.extract_pattern);
      
    case 'aggregate':
      return applyAggregations(data, params.aggregations || []);
      
    default:
      throw new Error(`Unsupported query type: ${queryType}`);
  }
};

/**
 * Apply filter operations
 */
const applyFilters = (data, filters) => {
  if (!Array.isArray(data)) {
    throw new Error('Filter operations require array data');
  }

  let filtered = data;
  
  for (const filter of filters) {
    const { field, operator, value } = filter;
    
    filtered = filtered.filter(item => {
      const fieldValue = getNestedValue(item, field);
      return applyFilterCondition(fieldValue, operator, value);
    });
  }
  
  return { data: filtered, recordCount: filtered.length };
};

/**
 * Apply transformation operations
 */
const applyTransforms = (data, transforms) => {
  if (!Array.isArray(data)) {
    throw new Error('Transform operations require array data');
  }

  let transformed = [...data];
  
  for (const transform of transforms) {
    const { operation, params } = transform;
    switch (operation) {
      case 'select': {
        transformed = transformed.map(item => {
          const selected = {};
          for (const field of params.fields || []) {
            selected[field] = getNestedValue(item, field);
          }
          return selected;
        });
        break;
      }
      case 'rename': {
        transformed = transformed.map(item => {
          const renamed = { ...item };
          for (const [oldName, newName] of Object.entries(params.mappings || {})) {
            if (oldName in renamed) {
              renamed[newName] = renamed[oldName];
              delete renamed[oldName];
            }
          }
          return renamed;
        });
        break;
      }
      case 'sort': {
        const { field, direction = 'asc' } = params;
        transformed.sort((a, b) => {
          const aVal = getNestedValue(a, field);
          const bVal = getNestedValue(b, field);
          let result;
          if (aVal < bVal) {
            result = -1;
          } else if (aVal > bVal) {
            result = 1;
          } else {
            result = 0;
          }
          return direction === 'desc' ? -result : result;
        });
        break;
      }
    }
  }
  
  return { data: transformed, recordCount: transformed.length };
};

/**
 * Apply search operations
 */
const applySearch = (data, searchTerms) => {
  if (!Array.isArray(data)) {
    // For non-array data, convert to searchable format
    const content = typeof data === 'string' ? data : JSON.stringify(data);
    const lines = content.split('\n');
    data = lines.map(line => ({ line }));
  }

  const results = [];
  
  for (const term of searchTerms) {
    const lowerTerm = String(term).toLowerCase();
    
    for (let i = 0; i < data.length; i++) {
      const item = data[i];
      const searchable = JSON.stringify(item).toLowerCase();
      
      // Use safe string method instead of regex
      if (searchable.includes(lowerTerm)) {
        results.push({
          ...item,
          _search_match: term,
          _line_number: i + 1
        });
      }
    }
  }
  
  return { data: results, recordCount: results.length };
};

/**
 * Apply extraction using pattern matching
 * Note: RegEx extraction disabled for security (ReDoS prevention)
 */
const applyExtraction = (data, pattern) => {
  if (!pattern) {
    throw new Error('extract_pattern is required for extraction queries');
  }

  // Security: Do not allow regex patterns from user input (ReDoS vulnerability)
  // Use simple string search instead
  const content = typeof data === 'string' ? data : JSON.stringify(data);
  const matches = [];
  const lowerContent = content.toLowerCase();
  const lowerPattern = String(pattern).toLowerCase();
  
  let index = 0;
  while ((index = lowerContent.indexOf(lowerPattern, index)) !== -1) {
    matches.push({
      match: content.substring(index, index + pattern.length),
      index: index
    });
    index += pattern.length;
  }
  
  return { data: matches, recordCount: matches.length };
};

/**
 * Apply aggregation operations
 */
const applyAggregations = (data, aggregations) => {
  if (!Array.isArray(data)) {
    throw new Error('Aggregation operations require array data');
  }

  const results = {};
  
  for (const agg of aggregations) {
    const { field, operation } = agg;
    const values = data.map(item => getNestedValue(item, field)).filter(val => val != null);
    
    switch (operation) {
      case 'count': {
        results[`${field}_count`] = values.length;
        break;
      }
      case 'sum': {
        results[`${field}_sum`] = values.reduce((sum, val) => sum + Number(val || 0), 0);
        break;
      }
      case 'avg': {
        const sum = values.reduce((s, val) => s + Number(val || 0), 0);
        results[`${field}_avg`] = values.length > 0 ? sum / values.length : 0;
        break;
      }
      case 'min': {
        results[`${field}_min`] = Math.min(...values.map(Number));
        break;
      }
      case 'max': {
        results[`${field}_max`] = Math.max(...values.map(Number));
        break;
      }
    }
  }
  
  return { data: results, recordCount: 1 };
};

/**
 * Format output in specified format
 */
const formatOutput = async (data, format) => {
  switch (format) {
    case 'json':
      return JSON.stringify(data, null, 2);
      
    case 'csv':
      if (!Array.isArray(data)) {
        throw new Error('CSV format requires array data');
      }
      return convertToCSV(data);
      
    case 'excel':
    case 'xlsx':
      return convertToExcel(data);
      
    case 'xml':
      return convertToXML(data);
      
    case 'txt':
      if (Array.isArray(data)) {
        return data.map(item => JSON.stringify(item)).join('\n');
      }
      return typeof data === 'string' ? data : JSON.stringify(data);
      
    default:
      return JSON.stringify(data, null, 2);
  }
};

/**
 * Helper functions
 */
const getNestedValue = (obj, path) => {
  return path.split('.').reduce((current, key) => current?.[key], obj);
};

const applyFilterCondition = (fieldValue, operator, value) => {
  switch (operator) {
    case 'eq': return fieldValue == value;
    case 'ne': return fieldValue != value;
    case 'gt': return Number(fieldValue) > Number(value);
    case 'lt': return Number(fieldValue) < Number(value);
    case 'gte': return Number(fieldValue) >= Number(value);
    case 'lte': return Number(fieldValue) <= Number(value);
    case 'contains': return String(fieldValue).toLowerCase().includes(String(value).toLowerCase());
    case 'regex': 
      // Security: RegEx matching disabled (ReDoS vulnerability)
      // Fall back to contains behavior
      return String(fieldValue).toLowerCase().includes(String(value).toLowerCase());
    default: return false;
  }
};

const convertToExcel = (data) => {
  // Create a new workbook
  const workbook = XLSX.utils.book_new();
  
  if (Array.isArray(data)) {
    // Convert array data to worksheet
    const worksheet = XLSX.utils.json_to_sheet(data);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
  } else {
    // Convert object data to worksheet
    const worksheet = XLSX.utils.json_to_sheet([data]);
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
  }
  
  // Return the workbook as buffer
  return XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
};

const convertToCSV = (data) => {
  if (data.length === 0) return '';
  
  const headers = Object.keys(data[0]);
  const csvHeaders = headers.join(',');
  const csvRows = data.map(row => 
    headers.map(header => {
      const value = row[header];
      const stringValue = value === null || value === undefined ? '' : String(value);
      return stringValue.includes(',') ? `"${stringValue}"` : stringValue;
    }).join(',')
  );
  
  return [csvHeaders, ...csvRows].join('\n');
};

const convertToXML = (data) => {
  const xmlHeader = '<?xml version="1.0" encoding="UTF-8"?>\n<root>\n';
  const xmlFooter = '</root>';
  
  if (Array.isArray(data)) {
    const xmlBody = data.map((item, index) => {
      return `  <item_${index}>\n${objectToXML(item, 4)}  </item_${index}>`;
    }).join('\n');
    return xmlHeader + xmlBody + '\n' + xmlFooter;
  } else {
    return xmlHeader + objectToXML(data, 2) + xmlFooter;
  }
};

const objectToXML = (obj, indent = 0) => {
  const spaces = ' '.repeat(indent);
  let xml = '';
  
  for (const [key, value] of Object.entries(obj)) {
    const sanitizedKey = key.replace(/[^a-zA-Z0-9_]/g, '_');
    if (typeof value === 'object' && value !== null) {
      xml += `${spaces}<${sanitizedKey}>\n${objectToXML(value, indent + 2)}${spaces}</${sanitizedKey}>\n`;
    } else {
      xml += `${spaces}<${sanitizedKey}>${value}</${sanitizedKey}>\n`;
    }
  }
  
  return xml;
};

module.exports = {
  handleCostGroupRequest
};