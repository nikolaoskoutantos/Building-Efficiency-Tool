# Chainlink External Adapter — Weather & Data to IPFS

This service is a Node.js/Express Chainlink external adapter that fetches weather data (from OpenWeather and Open-Meteo), encrypts it with Vault (if enabled), saves the ciphertext to IPFS, and returns only the CID (Content Identifier) to the Chainlink node. The raw weather data never goes on-chain; only the encrypted data (ciphertext) is stored off-chain, ensuring privacy and minimizing blockchain costs. This supports secure, scalable, and cost-efficient off-chain data delivery for smart contracts.

**Key Features:**

- Fetches weather data from OpenWeather and Open-Meteo APIs
- Supports both current and forecast weather requests
- Optionally encrypts data with Vault before storage
- Uploads (encrypted or plain) data to IPFS
- Returns only the IPFS CID to the Chainlink node (not raw data)
- API key authentication for all endpoints
- Swagger/OpenAPI documentation at `/api-docs`
- Can be run locally, with Docker, or via Docker Compose

---

## .env Configuration

Create a `.env` file in the root of the external adapter directory with the following variables:

```
# IPFS Configuration
IPFS_URL=https://ipfs.nkoutantos.com/api/v0         # IPFS API endpoint (local or remote)
IPFS_AUTH_TOKEN=...                                # (Optional) Auth token for IPFS service

# Weather API
OPENWEATHER_API_KEY=your_openweather_api_key       # OpenWeather API key

# Adapter Security
API_KEY=your_strong_random_key                     # API key for authenticating requests to this adapter
CORS_ORIGIN=*                                     # Allowed CORS origins (comma-separated or *)
PORT=3001                                         # Port to run the adapter on

# Vault Encryption
VAULT_ENDPOINT=http://localhost:8200               # Vault server endpoint
VAULT_TOKEN=qoe-dev-token-2025                     # Vault token (use a secure token in production)
VAULT_ENCRYPTION_KEY=weather-data                  # Vault encryption key name
VAULT_SECRET_PATH=secret                           # Vault secret path
VAULT_ENABLED=true                                 # Enable Vault encryption (true/false)
VAULT_KV_MOUNT=secret                              # Vault KV mount path

# Loki Logging
LOKI_URL=http://localhost:3100/loki/api/v1/push    # Loki push endpoint
LOKI_USERNAME=admin                                # Loki username
LOKI_PASSWORD=your_secure_loki_password            # Loki password

# Cost Data Source
COST_DATA_SOURCE="/home/node/app/data/Uniformat.xlsx" # Path to cost data Excel file
#COST_DATA_SOURCE="C:\Users\nikol\Documents\GitHub\QoE Application\external_adapter\data\Uniformat.xlsx"
```

**Never commit your real API keys or secrets to version control.**

---

## Running with Docker Compose

To build and start the adapter with Docker Compose:

```bash
docker compose up -d --build
```

This will build and start the external adapter, exposing it on port 8080 by default. Make sure your `.env` file is present so the container can load your configuration.

---

## API Usage

- **POST /** — Fetch weather data (see Swagger docs for schema)
- **POST /decrypt** — Decrypt data from IPFS (if Vault is enabled)
- **GET /health** — Health check endpoint
- **GET /api-docs** — Swagger UI

All requests (except `/health` and `/api-docs`) require an `x-api-key` header matching your `API_KEY`.

---

## Example Request

```bash
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_strong_random_key" \
  -d '{"id":"1","data":{"service":"openweather","lat":40,"lon":-74}}'
```

**Response:**

```json
{
  "jobRunID": "...",
  "cid": "QmYourEncryptedDataHash",
  "statusCode": 200
}
```

---

## Docker (Manual)

To build and run manually:

```bash
docker build . -t external-adapter
docker run -p 8080:8080 --env-file .env external-adapter:latest
```

---

## Reference

Based on [CL-EA-NodeJS-Template](https://github.com/thodges-gh/CL-EA-NodeJS-Template).

## Input Params

- `lat`: The latitude of the location to query (required)
- `lon`: The longitude of the location to query (required)
- `service`: The longitude of the location to query (optional)

## Output

```json
{
 "jobRunID": "278c97ffadb54a5bbb93cfec5f7b5503",
 "data": {
  "coord": {"lon": -3.5985, "lat": 37.1774},
  "weather": [
    {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
  ],
  "main": {
    "temp": 20.42,
    "feels_like": 19.3,
    "temp_min": 18.14,
    "temp_max": 20.46,
    "pressure": 1030,
    "humidity": 30
  },
  "visibility": 10000,
  "wind": {"speed": 0, "deg": 0},
  "clouds": {"all": 0},
  "dt": 1734534422,
  "sys": {
    "type": 2,
    "id": 2005546,
    "country": "ES",
    "sunrise": 1734506581,
    "sunset": 1734541160
  },
  "timezone": 3600,
  "id": 7668950,
  "name": "Realejo-San Matías",
  "cod": 200,
  "result": {
    "coord": {"lon": -3.5985, "lat": 37.1774},
    "weather": [
      {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
    ],
    "main": {
      "temp": 20.42,
      "feels_like": 19.3,
      "temp_min": 18.14,
      "temp_max": 20.46,
      "pressure": 1030,
      "humidity": 30
    }
  }
 },
 "statusCode": 200,
 "cid":"Qmf2hgPhAogGuQYvJ6agTNXJQbA6g3kvwczyaP5rGAPp2Y"
}
```

## Install Locally

Install dependencies:

```bash
yarn install
```

Crerate a `.env` file with the API KEY of the Open Weather API service.

```
OPENWEATHER_API_KEY= <YOUR_KEY_HERE>
```
