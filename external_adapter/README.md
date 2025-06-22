# Chainlink NodeJS External Adapter Template

This template provides a basic framework for developing Chainlink external adapters in NodeJS. It is tailored to interact with the OpenWeather API to fetch weather data. Comments are included to assist with development and testing of the external adapter. Once the API-specific values (like query parameters and API key authentication) have been added to the adapter, it is very easy to add some tests to verify that the data will be correctly formatted when returned to the Chainlink node. There is no need to use any additional frameworks or to run a Chainlink node in order to test the adapter. The returned data, for the avoidance of extreme costs, are stored into the IPFS, so the Oracle Node takes the CID. Each user/invoker has access to these data through the unique IDs of IPFS.

This code is based on the original repository: [CL-EA-NodeJS-Template](https://github.com/thodges-gh/CL-EA-NodeJS-Template).

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

### Test

Run the local tests:

```bash
yarn test
```

Natively run the application (defaults to port 8080):

### Run

```bash
yarn start
```

## Health Check of the server

```
curl -X GET -H "Content-Type: application/json" "http://localhost:8080/health" 
```

## Call the external adapter/API server

```bash
curl -X POST -H "Content-Type: application/json" "http://localhost:8080/" --data '{"id": 0, "data": {"lat": "37.178055", "lon": "-3.600833"}}'
```

## Authentication

This API is protected with an API key. You must provide a valid API key in the `x-api-key` header with each request (except for `/api-docs`, `/swagger.json`, and `/health`).

### Environment Variable

Set the following in your deployment environment or in a `.env` file:

```
API_KEY=your_strong_random_key
```

### Example Request

```
curl -X POST https://your-app.fly.dev/ \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_strong_random_key" \
  -d '{"id":"1","data":{"service":"openweather","lat":40,"lon":-74}}'
```

## Docker

If you wish to use Docker to run the adapter, you can build the image by running the following command:

```bash
docker build . -t external-adapter
```

Then run it with:

```bash
docker run -p 8080:8080 -it external-adapter:latest
```
