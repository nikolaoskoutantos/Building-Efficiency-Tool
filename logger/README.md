# Centralized Logging with Alloy, Loki, and Grafana

This logging stack uses **Alloy** to collect all logs from the Docker engine and forward them to **Loki** for storage and querying. **Grafana** provides dashboards and log exploration.

## How It Works

- **Alloy** acts as the log collector, reading all logs from the Docker engine.
- Alloy forwards these logs to **Loki**, a log aggregation system.
- **Grafana** connects to Loki, allowing you to visualize and search logs from all your containers in one place.

This setup avoids the need to configure logging drivers in each container—Alloy captures everything at the Docker engine level.

## Services

- **Alloy**: Collects all Docker logs and forwards to Loki
- **Loki**: Stores and indexes logs
- **Grafana**: Dashboards and log search

## .env Configuration

The `.env` file is used to securely configure credentials and environment variables for the logging stack. For a stable and secure setup, you should:

- Copy `.env.example` to `.env` and fill in all required values.
- Set strong, unique passwords for Grafana and Loki.
- Configure domain names to match your deployment (e.g., for HTTPS certificates).
- Review and adjust any other environment variables for your infrastructure (such as email for Let's Encrypt notifications).

Keeping your `.env` file up to date and secure ensures reliable authentication, encrypted connections, and smooth operation of all logging services.
