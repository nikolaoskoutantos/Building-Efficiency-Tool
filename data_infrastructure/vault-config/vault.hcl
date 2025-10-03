# HashiCorp Vault Configuration for QoE Application
# This is a development configuration - DO NOT use in production

# Storage backend (file system for development)
storage "file" {
  path = "/vault/data"
}

# Listener configuration
listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = 1  # Disable TLS for development (enable for production)
}

# UI configuration
ui = true

# API address
api_addr = "http://0.0.0.0:8200"
cluster_addr = "http://0.0.0.0:8201"

# Disable mlock for development (enable for production)
disable_mlock = true

# Log level
log_level = "Info"

# Default lease TTL
default_lease_ttl = "168h"
max_lease_ttl = "720h"