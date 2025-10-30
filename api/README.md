# QoE Application API

This folder contains the FastAPI backend for the QoE Application, including all database, encryption, and service logic.

## Overview

- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL (with Docker Compose)
- **Encryption:** pgcrypto extension for secure wallet and rating data
- **Automated schema and mock data initialization**

## Database & Encryption

- Database is managed via Docker Compose (`db` service)
- On first run, the database is initialized with:
  - Tables from SQLAlchemy models (auto-created on API startup)
  - Encryption and utility functions from `db/update_function.sql` (mounted and run by Postgres)
  - Mock/sample data loaded by the API if `DEV=true`
- **Encryption:**
  - Uses PostgreSQL's `pgcrypto` extension (enabled automatically)
  - Wallet addresses and sensitive data are never stored in plain text

## Running the API

1. **Start the backend and database:**

```sh
  docker compose up -d --build
```

2. **Environment variables:**

- Set in `.env` (see example below)
- Key variable: `DATABASE_URL=postgresql://<user>:<password>@db:5432/<dbname>`

3. **Access the API:**

- Default: http://localhost:8000
- Docs: http://localhost:8000/docs

## Example .env

```
DATABASE_URL=postgresql://qoe_user:qoe_password@db:5432/qoe_database
POSTGRES_USER=qoe_user
POSTGRES_PASSWORD=qoe_password
POSTGRES_DB=qoe_database
SESSION_SECRET_KEY=your-session-secret-key
RATING_ENCRYPTION_KEY=your-encryption-key
DEV=true
```

##### Development Notes

- All schema and encryption logic is automated; no manual DB setup needed
- Mock data is loaded only if `DEV=true`
- For test and migration details, see `db/README.md` and `tests/README.md`

## Security

- All sensitive data is encrypted at rest
- No plain text wallet addresses are stored
- Session and rating keys are managed via environment variables

---

For more details, see the `db/` and `tests/` subfolders.
