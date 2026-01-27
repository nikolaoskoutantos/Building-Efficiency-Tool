# Query Controller Test Examples

## Filter Example
```bash
curl -X POST "http://localhost:3001/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_api_key" \
  -d '{
    "id": "test-filter-001",
    "data": {
      "query_type": "filter",
      "file_source": "data",
      "file_data": "W3sibmFtZSI6IkpvaG4iLCJhZ2UiOjMwLCJjaXR5IjoiTllDIn0seyJuYW1lIjoiSmFuZSIsImFnZSI6MjUsImNpdHkiOiJMQSJ9LHsibmFtZSI6IkJvYiIsImFnZSI6MzUsImNpdHkiOiJOWUMifV0=",
      "query_params": {
        "filters": [
          {"field": "city", "operator": "eq", "value": "NYC"},
          {"field": "age", "operator": "gte", "value": "30"}
        ]
      },
      "output_format": "json"
    }
  }'
```

## Transform Example
```bash
curl -X POST "http://localhost:3001/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_api_key" \
  -d '{
    "id": "test-transform-001",
    "data": {
      "query_type": "transform",
      "file_source": "data", 
      "file_data": "W3sibmFtZSI6IkpvaG4iLCJhZ2UiOjMwLCJjaXR5IjoiTllDIn0seyJuYW1lIjoiSmFuZSIsImFnZSI6MjUsImNpdHkiOiJMQSJ9XQ==",
      "query_params": {
        "transforms": [
          {
            "operation": "select",
            "params": {"fields": ["name", "age"]}
          },
          {
            "operation": "rename", 
            "params": {"mappings": {"name": "full_name", "age": "years"}}
          }
        ]
      },
      "output_format": "csv"
    }
  }'
```

## Search Example  
```bash
curl -X POST "http://localhost:3001/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_api_key" \
  -d '{
    "id": "test-search-001",
    "data": {
      "query_type": "search",
      "file_source": "path",
      "file_path": "./test.txt",
      "query_params": {
        "search_terms": ["error", "warning", "critical"]
      },
      "output_format": "json"
    }
  }'
```

## Extract Example (Regex)
```bash
curl -X POST "http://localhost:3001/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_api_key" \
  -d '{
    "id": "test-extract-001", 
    "data": {
      "query_type": "extract",
      "file_source": "data",
      "file_data": "VGhpcyBpcyBhIHRlc3QgZmlsZSB3aXRoIGVtYWlsczogam9obkBleGFtcGxlLmNvbSBhbmQgamFuZUBleGFtcGxlLm9yZw==",
      "query_params": {
        "extract_pattern": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
      },
      "output_format": "json"
    }
  }'
```

## Aggregate Example
```bash
curl -X POST "http://localhost:3001/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_api_key" \
  -d '{
    "id": "test-aggregate-001",
    "data": {
      "query_type": "aggregate", 
      "file_source": "data",
      "file_data": "W3sicHJvZHVjdCI6IkEiLCJzYWxlcyI6MTAwfSx7InByb2R1Y3QiOiJCIiwic2FsZXMiOjE1MH0seyJwcm9kdWN0IjoiQyIsInNhbGVzIjo3NX1d",
      "query_params": {
        "aggregations": [
          {"field": "sales", "operation": "sum"},
          {"field": "sales", "operation": "avg"},
          {"field": "sales", "operation": "count"}
        ]
      },
      "output_format": "json"
    }
  }'
```

## Base64 Encoded Test Data

### JSON Array (for filter/transform/aggregate tests):
```json
[{"name":"John","age":30,"city":"NYC"},{"name":"Jane","age":25,"city":"LA"},{"name":"Bob","age":35,"city":"NYC"}]
```
Base64: `W3sibmFtZSI6IkpvaG4iLCJhZ2UiOjMwLCJjaXR5IjoiTllDIn0seyJuYW1lIjoiSmFuZSIsImFnZSI6MjUsImNpdHkiOiJMQSJ9LHsibmFtZSI6IkJvYiIsImFnZSI6MzUsImNpdHkiOiJOWUMifV0=`

### Text with Emails (for extract test):
```text
This is a test file with emails: john@example.com and jane@example.org
```
Base64: `VGhpcyBpcyBhIHRlc3QgZmlsZSB3aXRoIGVtYWlsczogam9obkBleGFtcGxlLmNvbSBhbmQgamFuZUBleGFtcGxlLm9yZw==`

### Sales Data (for aggregate test):
```json
[{"product":"A","sales":100},{"product":"B","sales":150},{"product":"C","sales":75}]
```  
Base64: `W3sicHJvZHVjdCI6IkEiLCJzYWxlcyI6MTAwfSx7InByb2R1Y3QiOiJCIiwic2FsZXMiOjE1MH0seyJwcm9kdWN0IjoiQyIsInNhbGVzIjo3NX1d`