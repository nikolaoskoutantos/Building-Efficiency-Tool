#!/bin/bash
# Vault Setup Script for QoE Application
# Run this after starting the containers to initialize Vault

set -e

echo "================🔐 Setting up HashiCorp Vault==============="
  
# Set Vault address
export VAULT_ADDR='http://localhost:8200'

# Wait for Vault to be ready
echo "⏳ Waiting for Vault to be ready..."
until curl -s $VAULT_ADDR/v1/sys/health > /dev/null 2>&1; do
  echo "Waiting for Vault..."
  sleep 2
done

echo "✅ Vault is ready!"

# Authenticate with dev token
export VAULT_TOKEN="qoe-dev-token-2025"

# Check if Vault is already initialized
if vault status | grep -q "Initialized.*true"; then
  echo "✅ Vault is already initialized"
else
  echo "🔧 Initializing Vault..."
  vault operator init
fi

echo "🔧 Setting up secrets engines for QoE application..."

# Enable Key-Value secrets engine for configuration
vault secrets list | grep -q "secret/" || {
  echo "Enabling KV secrets engine..."
  vault secrets enable -path=secret kv-v2
}

# Enable Transit secrets engine for encryption
vault secrets list | grep -q "transit/" || {
  echo "Enabling Transit secrets engine..."
  vault secrets enable transit
}

echo "🔑 Creating encryption keys for weather data..."

# Create encryption key for weather data
vault write -f transit/keys/weather-data || echo "Key already exists"

# Create encryption key for general data
vault write -f transit/keys/qoe-data || echo "Key already exists"

echo "📝 Setting up initial secrets..."

# Store encryption configuration
vault kv put secret/encryption \
  weather_key_name="weather-data" \
  qoe_key_name="qoe-data" \
  algorithm="aes256-gcm96"

# Store API keys (you'll update these with real values)
vault kv put secret/api-keys \
  openweather="your-openweather-api-key-here" \
  openmeteo="your-openmeteo-api-key-here" \
  ipfs_auth="your-ipfs-auth-token-here"

# Store database configuration
vault kv put secret/database \
  host="localhost" \
  port="5432" \
  database="qoe_database" \
  username="qoe_user" \
  password="qoe_password"

echo "🔍 Creating Vault policies for different access levels..."

# Create policy for external adapter (read-only for API keys, encrypt/decrypt access)
vault policy write external-adapter - <<EOF
# Allow encryption/decryption operations
path "transit/encrypt/weather-data" {
  capabilities = ["update"]
}
path "transit/decrypt/weather-data" {
  capabilities = ["update"]
}
path "transit/encrypt/qoe-data" {
  capabilities = ["update"]
}
path "transit/decrypt/qoe-data" {
  capabilities = ["update"]
}

# Read API keys
path "secret/data/api-keys" {
  capabilities = ["read"]
}

# Read encryption config
path "secret/data/encryption" {
  capabilities = ["read"]
}
EOF

# Create policy for API backend (broader access)
vault policy write api-backend - <<EOF
# Full access to secrets
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Encryption operations
path "transit/encrypt/*" {
  capabilities = ["update"]
}
path "transit/decrypt/*" {
  capabilities = ["update"]
}

# Key management
path "transit/keys/*" {
  capabilities = ["read", "list"]
}
EOF

echo "🎫 Creating authentication tokens..."

# Create token for external adapter
EXTERNAL_ADAPTER_TOKEN=$(vault write -field=token auth/token/create \
  policies="external-adapter" \
  ttl="720h" \
  renewable=true)

# Create token for API backend
API_BACKEND_TOKEN=$(vault write -field=token auth/token/create \
  policies="api-backend" \
  ttl="720h" \
  renewable=true)

echo ""
echo "🎉 Vault setup complete!"
echo "======================="
echo ""
echo "📋 Important Information:"
echo "  Vault UI: http://localhost:8200"
echo "  Root Token: qoe-dev-token-2025"
echo ""
echo "🔑 Application Tokens:"
echo "  External Adapter: $EXTERNAL_ADAPTER_TOKEN"
echo "  API Backend: $API_BACKEND_TOKEN"
echo ""
echo "💡 Next Steps:"
echo "  1. Update your .env files with the tokens above"
echo "  2. Replace placeholder API keys in Vault"
echo "  3. Test encryption/decryption from your application"
echo ""
echo "🔧 Useful Commands:"
echo "  vault status                    # Check Vault status"
echo "  vault kv list secret/           # List all secrets"
echo "  vault policy list               # List all policies"
echo "  vault auth list                 # List auth methods"
echo ""
echo "⚠️  Development Setup Notice:"
echo "   This is configured for development only!"
echo "   For production, enable TLS and use proper authentication."