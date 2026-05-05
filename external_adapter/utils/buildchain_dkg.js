const path = require('node:path');
const { randomUUID } = require('node:crypto');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const fetch = (...args) => import('node-fetch').then(({ default: fetch }) => fetch(...args));

const DKG_BASE_URL = process.env.BUILDCHAIN_API_URL || '';
const DKG_JWT_TOKEN = process.env.BUILDCHAIN_JWT_TOKEN || '';

function joinUrl(base, relative) {
  const normalizedBase = (base || '').replace(/\/+$/, '');
  const normalizedRelative = relative.startsWith('/') ? relative : `/${relative}`;
  return `${normalizedBase}${normalizedRelative}`;
}

async function parseJsonResponse(response, context) {
  const raw = await response.text();
  const contentType = response.headers.get('content-type') || '';

  try {
    return JSON.parse(raw);
  } catch (err) {
    const preview = raw.slice(0, 200).replaceAll(/\s+/g, ' ').trim();
    const error = new Error(`${context} returned non-JSON response (${contentType || 'unknown content-type'}): ${preview}. Parse error: ${err.message}`);
    error.status = response.status;
    error.body = raw;
    throw error;
  }
}

function summarizeBody(body) {
  if (typeof body === 'string') {
    return body.slice(0, 400);
  }

  try {
    return JSON.stringify(body).slice(0, 400);
  } catch {
    return String(body).slice(0, 400);
  }
}

function sanitizeIdPart(value) {
  return String(value || '')
    .toLowerCase()
    .replaceAll(/[^a-z0-9-]/g, '-')
    .replaceAll(/-+/g, '-')
    .replaceAll(/^-|-$/g, '')
    .slice(0, 64);
}

function buildKnowledgeAssetId(prefix, seed) {
  const safePrefix = sanitizeIdPart(prefix) || 'ka';
  const safeSeed = sanitizeIdPart(seed) || 'request';
  const uniqueSuffix = randomUUID().replaceAll(/-/g, '');
  return `${safePrefix}-${safeSeed}-${uniqueSuffix}`;
}

function authHeaders(extra = {}) {
  return {
    Authorization: `Bearer ${DKG_JWT_TOKEN}`,
    ...extra,
  };
}

// Validate JWT and confirm node is reachable
async function validateIdentity() {
  const url = `${DKG_BASE_URL}/auth/validate/identity`;
  const response = await fetch(url, {
    method: 'GET',
    headers: authHeaders(),
  });

  const body = await parseJsonResponse(response, 'DKG identity validation');

  if (!response.ok) {
    const err = new Error(`DKG identity validation failed: HTTP ${response.status}`);
    err.status = response.status;
    err.body = body;
    throw err;
  }

  return body;
}

// Publish a weather Knowledge Asset to the DKG node
async function createWeatherKA(data) {
  const url = `${DKG_BASE_URL}/api/weather-data/create`;
  const response = await fetch(url, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  });

  const body = await parseJsonResponse(response, 'DKG weather KA creation');

  if (!response.ok) {
    const err = new Error(`DKG weather KA creation failed: HTTP ${response.status} - ${summarizeBody(body)}`);
    err.status = response.status;
    err.body = body;
    throw err;
  }

  return body;
}

const weatherKATemplate = require('../schemas/weather-ka.json');
const costKATemplate    = require('../schemas/cost-ka.json');

// Replace __PLACEHOLDER__ tokens in a cloned template.
// - Strings: replaced wherever they appear (standalone or embedded inside a larger string value)
// - Numbers, booleans, arrays, objects: replace the quoted token with raw JSON
function fillTemplate(template, replacements) {
  let json = JSON.stringify(template);
  for (const [key, value] of Object.entries(replacements)) {
    if (typeof value === 'string') {
      // Escape the value for safe embedding inside a JSON string, then replace bare token
      const escaped = JSON.stringify(value).slice(1, -1);
      json = json.replaceAll(`__${key}__`, escaped);
    } else {
      // Non-string: swap the quoted token for raw JSON (number, boolean, array, object)
      json = json.replaceAll(`"__${key}__"`, JSON.stringify(value));
    }
  }
  return JSON.parse(json);
}

function buildWeatherKA(data) {
  const {
    id,
    ipfsCid,
    contractAddress,
    location,
    qoe,
    buildingDID = '',
    dateCreated = new Date().toISOString().split('T')[0],
  } = data;

  const baseId = `https://buildchain.org/ka/${id}`;

  return fillTemplate(weatherKATemplate, {
    BASE_ID:          baseId,
    DATE:             dateCreated,
    CONTRACT_ADDRESS: contractAddress,
    IPFS_CID:         ipfsCid,
    LOCATION_NAME:    location.name,
    LAT:              String(location.lat),
    LON:              String(location.lon),
    BUILDING_DID:     buildingDID,
    QOE_EVAL_ID:      qoe.evaluationID,
    QOE_OVERALL:      qoe.overallScore,
    QOE_OW_RT:        qoe.openweather.responseTimeMs,
    QOE_OW_DC:        qoe.openweather.dataCompleteness,
    QOE_OW_RS:        qoe.openweather.reliabilityScore,
    QOE_OW_AS:        qoe.openweather.accuracyScore,
    QOE_OW_AV:        qoe.openweather.availability,
    QOE_OM_RT:        qoe.openmeteo.responseTimeMs,
    QOE_OM_DC:        qoe.openmeteo.dataCompleteness,
    QOE_OM_RS:        qoe.openmeteo.reliabilityScore,
    QOE_OM_AS:        qoe.openmeteo.accuracyScore,
    QOE_OM_AV:        qoe.openmeteo.availability,
  });
}

// Publish a material cost Knowledge Asset to the DKG node
async function createCostKA(data) {
  const url = `${DKG_BASE_URL}/api/cost-data/create`;
  const response = await fetch(url, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(data),
  });

  const body = await parseJsonResponse(response, 'DKG cost KA creation');

  if (!response.ok) {
    const err = new Error(`DKG cost KA creation failed: HTTP ${response.status} - ${summarizeBody(body)}`);
    err.status = response.status;
    err.body = body;
    throw err;
  }

  return body;
}

function buildCostKA(data) {
  const {
    id,
    ipfsCid,
    contractAddress,
    creator,
    lastUpdate,
    sampleCosts = [],
    dateCreated = new Date().toISOString().split('T')[0],
    uploader,
  } = data;

  const baseId    = `https://buildchain.org/ka/${id}`;
  const uploader_ = uploader || creator;

  const sampleCostPreview = sampleCosts.map((item, index) => ({
    '@id':          `${baseId}/sample/${index}`,
    'ex:material':  item.material,
    'ex:unit':      item.unit,
    'ex:price':     String(item.price),
    'ex:currency':  item.currency || 'EUR',
  }));

  return fillTemplate(costKATemplate, {
    BASE_ID:          baseId,
    DATE:             dateCreated,
    CONTRACT_ADDRESS: contractAddress,
    IPFS_CID:         ipfsCid,
    CREATOR_NAME:     creator.name,
    CREATOR_ID:       creator.identifier,
    UPLOADER_NAME:    uploader_.name,
    UPLOADER_ID:      uploader_.identifier,
    LAST_UPDATE:      lastUpdate,
    SAMPLE_COSTS:     sampleCostPreview,
  });
}

async function getBuildingLatLon(did) {
  if (!DKG_BASE_URL) {
    throw new Error('BUILDCHAIN_API_URL is not configured');
  }

  const candidates = [
    `/buildchain/buildings/query?did=${encodeURIComponent(did)}`,
    `/api/buildchain/buildings/query?did=${encodeURIComponent(did)}`,
  ];

  let lastError;

  for (const relativePath of candidates) {
    const url = joinUrl(DKG_BASE_URL, relativePath);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: authHeaders(),
      });

      const body = await parseJsonResponse(response, `Buildchain building lookup at ${relativePath}`);

      if (!response.ok) {
        const err = new Error(`Failed to fetch building location for DID ${did}: HTTP ${response.status}`);
        err.status = response.status;
        err.body = body;
        throw err;
      }

      if (!Array.isArray(body) || body.length === 0 || typeof body[0] !== 'object' || body[0] === null) {
        const err = new Error(`Buildchain API returned no building data for DID ${did}`);
        err.body = body;
        throw err;
      }

      const [building] = body;
      const lat = Number.parseFloat(building.lat);
      const lon = Number.parseFloat(building.lon);

      if (Number.isNaN(lat) || Number.isNaN(lon)) {
        const err = new Error(`Buildchain API returned invalid coordinates for DID ${did}`);
        err.body = body;
        throw err;
      }

      return { lat, lon };
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error(`Failed to resolve building DID ${did}`);
}

module.exports = {
  validateIdentity,
  createWeatherKA,
  buildWeatherKA,
  createCostKA,
  buildCostKA,
  buildKnowledgeAssetId,
  getBuildingLatLon,
};
