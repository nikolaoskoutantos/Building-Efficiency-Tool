# Application API

This folder contains the FastAPI backend for the QoE Application. It is responsible for API endpoints, authentication, database access, weather/sensor aggregation, HVAC optimization, and startup bootstrap tasks such as migrations and mock data loading.

## What This Backend Does

The API is the main application service for the project. It:

- exposes REST endpoints through FastAPI
- connects to PostgreSQL for application data
- runs Alembic migrations on startup when enabled
- applies SQL helper/database functions from `db/update_function.sql`
- seeds mock/demo data in development mode
- loads HVAC optimization models from MLflow
- serves authenticated routes for buildings, devices, sensors, dashboard data, user settings, and optimization

## Current Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Migrations:** Alembic
- **ML/Optimization:** scikit-learn + MLflow
- **Auth:** session middleware plus JWT/session-based authenticated endpoints
- **Messaging / IoT support:** EMQX-related integration and MQTT utilities

## Folder Map

- [`controllers/`](./controllers/)API route handlers
- [`services/`](./services/)Business logic, weather workflows, HVAC optimization logic
- [`models/`](./models/)SQLAlchemy ORM models
- [`db/`](./db/)DB connection helpers, SQL bootstrap scripts, mock data
- [`alembic/`](./alembic/) and [`alembic.ini`](./alembic.ini)Schema migrations
- [`utils/`](./utils/)Shared helpers such as auth, SQL utilities, policy checks, migration helpers
- [`workers/`](./workers/)
  Background-style processing such as MQTT subscriber logic

## Startup Flow

The backend startup order in [`main.py`](./main.py) is important:

1. FastAPI app is initialized
2. Alembic migrations run if enabled
3. SQL bootstrap functions from `db/update_function.sql` are applied
4. optional SQL compatibility migrations are applied
5. mock data is inserted in development mode
6. routers are mounted and the API begins serving traffic
7. the weather scheduler is started through the FastAPI lifespan hook

This means the database must be reachable before the API can fully start.

## Environment Files

This backend expects an `.env` file inside the `api/` folder.

Typical workflow:

1. copy [`api/.env.example`](./.env.example) to `api/.env`
2. fill in the required values
3. run commands from inside the `api/` folder when using the local compose file

## Database URLs: Docker vs Local

This is one of the most common sources of confusion.

- **When the API runs inside Docker Compose**, use the Docker service hostname:

  - `postgresql://user:password@db:5432/dbname`
- **When the API runs on your host machine**, `db` usually will not resolve.
  Use the published host port instead:

  - `postgresql://user:password@localhost:5444/dbname`

In this repo, the PostgreSQL container exposes:

- host `5444` -> container `5432`

So if you see an error like:

`could not translate host name "db" to address`

you are probably using the Docker hostname from a non-Docker process.

## Running the Backend

### Docker Compose

From the `api/` folder:

```sh
docker compose up -d --build
```

This compose setup includes more than just the API. It currently defines services such as:

| Service       | Purpose                                                                                         |
| :------------ | :---------------------------------------------------------------------------------------------- |
| `traefik`   | Reverse proxy and entrypoint router for HTTP, HTTPS, and MQTT traffic.                          |
| `ui`        | Frontend development container serving the Vue.js interface.                                    |
| `api`       | Main FastAPI backend for application logic, auth, DB access, and optimization routes.           |
| `mlflow`    | Experiment tracking and model registry/artifact store used by HVAC optimization flows.          |
| `portainer` | Docker management UI for inspecting and managing deployed containers.                           |
| `emqx`      | MQTT broker and dashboard used for device messaging / IoT-style integration.                    |
| `authelia`  | Authentication and access-control service for protected internal tools.                         |
| `redis`     | Supporting datastore used by infrastructure/auth-related services.                              |
| `db`        | PostgreSQL database storing application data, schedules, sensor data, and optimization history. |

For backend development, the most important dependencies are:

- API
- PostgreSQL
- MLflow for optimization-related functionality

### Local Host Execution

If you run the API directly on your machine instead of in Docker:

- make sure PostgreSQL is reachable on the host
- use a host-based `DATABASE_URL`
- make sure migrations can connect successfully before startup continues

## Migrations

Schema changes are managed through Alembic.

The backend can run:

- `alembic upgrade head`

automatically on startup when enabled through the startup migration settings.

This behavior is controlled through the migration helper logic in [`utils/alembic_migrations.py`](./utils/alembic_migrations.py).

## SQL Bootstrap Functions

The backend also applies raw SQL from:

- [`db/update_function.sql`](./db/update_function.sql)

These SQL functions support higher-level data access patterns such as combined building/sensor/weather queries and dashboard-oriented database functions.

This file is applied by the API during startup, not just by PostgreSQL container initialization.

## Mock Data

Mock data is loaded from:

- [`db/mock_data.py`](./db/mock_data.py)

It is intended for development/demo workflows and currently seeds:

- demo buildings and users
- building/user role mappings
- HVAC units
- sensors
- weather data
- sensor timeseries
- HVAC schedules
- optimization history / visualization data

Mock data only loads when development mode is enabled.

Important environment flags:

- `DEV=true`
- `RUN_MOCK_DATA_ON_STARTUP=true`

If you want the backend to start without reseeding mock data, disable the second flag.

## HVAC Optimization and MLflow

The optimization flow depends on MLflow.

Mock data alone is not enough to fully test optimization endpoints. For HVAC prediction/optimization to work end to end:

- MLflow must be reachable
- a trained model must be registered for the target building/location

The main optimization logic lives in:

- [`services/hvac_optimizer_service.py`](./services/hvac_optimizer_service.py)

The main HVAC prediction/optimization endpoints live in:

- [`controllers/predict.py`](./controllers/predict.py)

If no model is registered in MLflow, optimization calls may fail or return no usable model state.

## Authentication

This backend includes authenticated routes and session support.

Relevant pieces include:

- `SessionMiddleware` configured in [`main.py`](./main.py)
- auth endpoints under [`controllers/auth.py`](./controllers/auth.py)
- JWT/session-aware UI/backend integration
- role-aware route protection via auth dependencies and policy checks

Many routes require authenticated users with appropriate building/device permissions.

## Common Problems

### 1. `could not translate host name "db"`

Cause:

- using the Docker hostname from a host-side process

Fix:

- switch to `localhost:5444` when running the API outside Docker

### 2. Alembic migration failure on startup

Cause:

- database is not reachable
- wrong connection string
- migration startup is enabled before DB is ready

Fix:

- confirm `DATABASE_URL`
- confirm PostgreSQL is running
- run migrations manually if needed

### 3. Optimization works partially but model is missing

Cause:

- MLflow is not reachable
- no registered model exists for the selected building

Fix:

- verify `MLFLOW_TRACKING_URI`
- verify model registration in MLflow

### 4. Mock data does not appear

Cause:

- `DEV` is false
- mock data startup flag is disabled
- startup failed earlier during DB connection or migration

Fix:

- check startup logs in order
- ensure migrations and DB connectivity complete first

## Security Notes

- sensitive keys and credentials are provided through environment variables
- wallet/auth-related flows should not rely on committed secrets
- local `.env` files must not be committed
- production deployments should replace demo/default values and restrict service exposure appropriately

## Summary

If you are new to this backend, the simplest mental model is:

- PostgreSQL stores the core data
- FastAPI exposes the app logic
- Alembic manages schema changes
- SQL bootstrap functions support richer queries
- mock data powers local demos
- MLflow provides trained models for HVAC optimization

For broader system context, use the root [`README.md`](../README.md). For API-specific implementation details, start from the folders listed above.
