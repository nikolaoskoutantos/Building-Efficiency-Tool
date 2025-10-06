# PowerShell Vault Setup Script
# Run this after starting Vault container

$VAULT_ADDR = "http://localhost:8200"
$VAULT_TOKEN = "qoe-dev-token-2025"

Write-Host "================Setting up HashiCorp Vault===============" -ForegroundColor Cyan

# Wait for Vault to be ready
Write-Host "Waiting for Vault to be ready..." -ForegroundColor Yellow
do {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod -Uri "$VAULT_ADDR/v1/sys/health" -Method Get
        if ($health.initialized) { break }
    } catch {
        Write-Host "Waiting for Vault..." -ForegroundColor Yellow
    }
} while ($true)

Write-Host "Vault is ready!" -ForegroundColor Green

# Setup secrets engines
Write-Host "Setting up secrets engines..." -ForegroundColor Yellow

try {
    # Enable KV secrets engine
    docker exec -e VAULT_TOKEN=$VAULT_TOKEN -e VAULT_ADDR=http://127.0.0.1:8200 qoe-vault vault secrets enable -path=secret kv-v2
    Write-Host "KV secrets engine enabled" -ForegroundColor Green
} catch {
    Write-Host "KV secrets engine may already exist" -ForegroundColor Yellow
}

try {
    # Enable Transit secrets engine
    docker exec -e VAULT_TOKEN=$VAULT_TOKEN -e VAULT_ADDR=http://127.0.0.1:8200 qoe-vault vault secrets enable transit
    Write-Host "Transit secrets engine enabled" -ForegroundColor Green
} catch {
    Write-Host "Transit engine may already exist" -ForegroundColor Yellow
}

# Create encryption keys
Write-Host "Creating encryption keys..." -ForegroundColor Yellow

docker exec -e VAULT_TOKEN=$VAULT_TOKEN -e VAULT_ADDR=http://127.0.0.1:8200 qoe-vault vault write -f transit/keys/weather-data
docker exec -e VAULT_TOKEN=$VAULT_TOKEN -e VAULT_ADDR=http://127.0.0.1:8200 qoe-vault vault write -f transit/keys/qoe-data

# Create policies
Write-Host "Creating access policies..." -ForegroundColor Yellow

$externalAdapterPolicy = @"
# Allow encryption/decryption operations
path "transit/encrypt/weather-data" {
  capabilities = ["update"]
}
path "transit/decrypt/weather-data" {
  capabilities = ["update"]
}
path "transit/datakey/plaintext/weather-data" {
  capabilities = ["update"]
}
path "transit/rewrap/weather-data" {
  capabilities = ["update"]
}

# Read API keys
path "secret/data/api-keys" {
  capabilities = ["read"]
}

# KV access for CID mappings
path "kv/data/files/*" {
  capabilities = ["create", "read", "update", "delete"]
}
"@

# Write policy to temporary file and apply
$policyFile = [System.IO.Path]::GetTempFileName()
$externalAdapterPolicy | Out-File -FilePath $policyFile -Encoding utf8
docker cp $policyFile qoe-vault:/tmp/external-adapter-policy.hcl
docker exec -e VAULT_TOKEN=$VAULT_TOKEN -e VAULT_ADDR=http://127.0.0.1:8200 qoe-vault vault policy write external-adapter /tmp/external-adapter-policy.hcl
Remove-Item $policyFile

Write-Host ""
Write-Host "Vault setup complete!" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Important Information:" -ForegroundColor White
Write-Host "  Vault UI: $VAULT_ADDR" -ForegroundColor Cyan
Write-Host "  Root Token: $VAULT_TOKEN" -ForegroundColor Cyan
Write-Host ""
Write-Host "Encryption Keys Created:" -ForegroundColor White
Write-Host "  - weather-data (for weather datasets)" -ForegroundColor Green
Write-Host "  - qoe-data (for general QoE data)" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Start your external adapter" -ForegroundColor Yellow
Write-Host "  2. Test the encryption integration" -ForegroundColor Yellow
Write-Host ""