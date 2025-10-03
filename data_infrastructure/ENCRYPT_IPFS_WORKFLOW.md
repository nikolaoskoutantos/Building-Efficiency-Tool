# Encrypt-then-IPFS Workflow Example

## Use Case: Secure Weather Data Storage

This demonstrates encrypting data with Vault before storing in IPFS for privacy.

### Setup

```powershell
# 1. Start infrastructure
docker-compose up -d

# 2. Enable encryption (REQUIRED for your use case)
./vault-setup.sh

# 3. Verify encryption is working
curl -X POST -H "X-Vault-Token: qoe-dev-token-2025" \
  -d '{"plaintext": "SGVsbG8="}' \
  http://localhost:8200/v1/transit/encrypt/weather-data
```

### Workflow Implementation

#### Step 1: Encrypt Data Before IPFS
```javascript
// Example: External Adapter encrypting weather data
const weatherData = {
  temperature: 23.5,
  humidity: 65,
  timestamp: "2025-10-03T12:00:00Z"
};

// 1. Base64 encode the data
const plaintext = Buffer.from(JSON.stringify(weatherData)).toString('base64');

// 2. Encrypt with Vault
const encryptResponse = await fetch('http://localhost:8200/v1/transit/encrypt/weather-data', {
  method: 'POST',
  headers: {
    'X-Vault-Token': 'qoe-dev-token-2025',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ plaintext })
});

const { data: { ciphertext } } = await encryptResponse.json();
// Result: "vault:v1:abc123encrypted456data789"
```

#### Step 2: Store Encrypted Data in IPFS
```javascript
// 3. Store encrypted data in IPFS
const ipfsResponse = await fetch('http://localhost:5001/api/v0/add', {
  method: 'POST',
  body: new FormData().append('file', new Blob([ciphertext]))
});

const { Hash: ipfsHash } = await ipfsResponse.json();
// Result: "QmYourEncryptedDataHash"
```

#### Step 3: Retrieve and Decrypt
```javascript
// 4. Retrieve encrypted data from IPFS
const retrievedData = await fetch(`http://localhost:8080/ipfs/${ipfsHash}`);
const encryptedContent = await retrievedData.text();

// 5. Decrypt with Vault
const decryptResponse = await fetch('http://localhost:8200/v1/transit/decrypt/weather-data', {
  method: 'POST',
  headers: {
    'X-Vault-Token': 'qoe-dev-token-2025',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ ciphertext: encryptedContent })
});

const { data: { plaintext: decryptedBase64 } } = await decryptResponse.json();

// 6. Decode back to original data
const originalData = JSON.parse(Buffer.from(decryptedBase64, 'base64').toString());
// Result: { temperature: 23.5, humidity: 65, timestamp: "2025-10-03T12:00:00Z" }
```

### Security Benefits

1. **Zero-Knowledge IPFS**: IPFS only stores encrypted data, no plaintext
2. **Separate Key Management**: Encryption keys never stored with data
3. **Access Control**: Vault policies control who can encrypt/decrypt
4. **Audit Trail**: Vault logs all encryption/decryption operations

### Integration with Your External Adapter

```javascript
// external_adapter/app.js modification
async function storeWeatherDataSecurely(weatherData) {
  // 1. Encrypt first
  const encrypted = await vaultEncrypt(weatherData);
  
  // 2. Store encrypted data in IPFS
  const ipfsHash = await ipfsStore(encrypted);
  
  // 3. Return hash for blockchain storage
  return ipfsHash;
}

async function retrieveWeatherDataSecurely(ipfsHash) {
  // 1. Get encrypted data from IPFS
  const encrypted = await ipfsRetrieve(ipfsHash);
  
  // 2. Decrypt with Vault
  const decrypted = await vaultDecrypt(encrypted);
  
  return decrypted;
}
```

### CLI Testing

```powershell
# Test encryption
$plaintext = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("test data"))
curl -X POST -H "X-Vault-Token: qoe-dev-token-2025" `
  -d "{\"plaintext\": \"$plaintext\"}" `
  http://localhost:8200/v1/transit/encrypt/weather-data

# Test IPFS storage
echo "vault:v1:encrypted_data_here" | curl -X POST -F "file=@-" http://localhost:5001/api/v0/add

# Test IPFS retrieval
curl http://localhost:8080/ipfs/QmYourHashHere
```

### Production Considerations

1. **Token Management**: Use proper Vault authentication (not dev token)
2. **Key Rotation**: Vault supports automatic key rotation
3. **Backup**: Ensure Vault storage backend is backed up
4. **Monitoring**: Monitor encryption/decryption performance
5. **Network Security**: Use TLS for Vault communication in production