# Centralized Logging with Loki + Grafana

## Quick Start

1. Copy environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your secure passwords
   ```

2. Start logging services:
   ```bash
   cd logger
   docker compose up -d
   ```

3. Access Grafana:
   - URL: https://grafana.nkoutantos.com
   - Username: `admin`
   - Password: `your_secure_grafana_password`

## Configure Other Containers

Add this to each service in your docker-compose files:

```yaml
services:
  your-service:
    # ... existing config ...
    logging:
      driver: "loki"
      options:
        loki-url: "https://logs.nkoutantos.com/loki/api/v1/push"
        loki-basic-auth-username: "admin"
        loki-basic-auth-password: "your_secure_loki_password"
        loki-external-labels: "service=your-service-name"
    networks:
      - qoe-logging-network

networks:
  qoe-logging-network:
    external: true
```

## Services

- **Loki** (Port 3100): Secure log storage with authentication
- **Grafana** (Port 3000): Log dashboard with SSL
- **Caddy**: Reverse proxy with automatic HTTPS
- **Promtail**: Log collector

## Domains

- **Grafana**: https://grafana.nkoutantos.com
- **Loki API**: https://logs.nkoutantos.com

## Security Features

- HTTPS with automatic Let's Encrypt certificates
- Basic authentication for Loki API
- Secure password configuration
- Security headers enabled