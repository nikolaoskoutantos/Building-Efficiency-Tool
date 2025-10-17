Repository: QoE Application — Chainlink + FastAPI + HVAC optimizer

Target: Help an AI coding assistant be immediately productive in this repository.

Key architecture (short):
- FastAPI backend in `api/` exposes REST endpoints (entry: `api/main.py`). Controllers live in `api/controllers/` (e.g. `predict.py`, `hvac.py`, `sensordata.py`).
- Data models and DB access: SQLAlchemy models under `api/models` and DB helpers in `api/db/` (see `db/connection.py` and `db/init.sql` in `api/db`).
- HVAC ML service: `api/services/hvac_optimizer_service.py` implements training, prediction, and location-aware model storage. Trained scikit-learn models are saved to `saved_models/` and referenced via `models.predictor.model_data.rf_model_path`.
- External adapter for Chainlink: `external_adapter/` contains a Node.js external adapter that fetches weather and returns an IPFS CID. See `external_adapter/README.md` for run/test instructions.

What to do first (quick wins):
- Run the backend locally: start the FastAPI app from `api/main.py` (project uses Starlette / FastAPI). For local dev use `uvicorn api.main:app --reload --port 8000` from repository root (ensure Python deps in `api/requirements_hvac.txt` or `environment.yml` are installed).
- Train an HVAC model: POST to `/predict/hvac/train` with JSON body matching `HVACTrainingRequest` in `api/controllers/predict.py` (fields: latitude, longitude, sensor_id, knowledge_id, days_back). Training runs in background and persists models to `saved_models/` and DB.
- Call prediction/optimization: use `/predict/hvac/predict` and `/predict/hvac/optimize` endpoints; payload schemas are in `api/controllers/predict.py`.

Project-specific conventions and pitfalls:
- Models are location-scoped: HVAC models are stored per (latitude, longitude) in the `Predictor` table. The service loads models using a location tolerance (default 0.01°) — changing tolerance affects which model is reused.
- Saved model files are plain joblib `.pkl` files under `saved_models/`. When editing model save/load paths, update both `hvac_optimizer_service.py` and DB `model_data` keys.
- DB initialization: the project relies on PostgreSQL init scripts under `db/` (see `api/db/init.sql` and `api/db/migration_*.sql`). The FastAPI app no longer auto-creates tables (Base.metadata.create_all is commented out in `api/main.py`). For local testing prefer the provided `api/db/mock_data.py` helper or run migrations.
- Time formats: HVAC services expect `starting_time` formatted as '%d/%m/%Y %H:%M' (see `predict.py` and `hvac_optimizer_service.py`). Be careful when generating timestamps.

Integration & external dependencies to note:
- Chainlink / smart contracts live in `chainlink/` and `smart_contracts/`. The external adapter (`external_adapter/`) communicates with Chainlink nodes and posts results to IPFS (CID returned). If modifying the adapter follow `external_adapter/README.md` for API_KEY and OpenWeather key setup.
- Scikit-learn and joblib are used for ML (see `api/services/hvac_optimizer_service.py`). Large training runs will read from PostgreSQL and write `.pkl` files to `saved_models/` — ensure this directory is writable.
- DB: PostgreSQL expected. Connection config is under `api/db/connection.py`. Inspect `api/db/pg_hba.conf` and `docker-compose.yml` in `db/` for containerized setups.

Patterns and code examples to follow (copyable guidance):
- Create a controller endpoint that uses DB session:

  - Use `get_db()` pattern from existing controllers (open DB session, yield, finally close). Example: `api/controllers/hvac.py`.

- When adding a new ML pipeline, persist artifacts and metadata similarly to `HVACOptimizerService.train_full_pipeline`:
  - save model with `joblib.dump(...)` into `saved_models/`
  - insert a `Predictor` DB record with `model_type`, `model_data` containing `rf_model_path` and metrics
  - insert a `TrainingHistory` record with timestamps and metrics

- For background work from HTTP handlers, follow existing pattern in `api/controllers/predict.py` using FastAPI `BackgroundTasks` to call service methods.

Useful files to inspect when making changes:
- `api/main.py` — app composition, middleware, static mount
- `api/controllers/predict.py` — HVAC training/prediction endpoints and Pydantic schemas
- `api/services/hvac_optimizer_service.py` — full ML pipeline, saved model conventions, evaluation and optimization methods
- `saved_models/` — where joblib `.pkl` models are stored
- `external_adapter/README.md` and adapter source — Chainlink adapter usage and API contract
- `api/db/` — migrations, mock data and connection config

When editing code, follow these strict rules:
- Preserve DB schema fields used by ML code: `Predictor.model_data` must keep `rf_model_path`, `a_coefficient`, and `avg_consumption_off` keys for compatibility.
- Keep `starting_time` parsing format and `duration` semantics (5-minute intervals, default 12) unless you update all callers and docs.
- Do not change saved model filename patterns without updating `get_all_location_models()` consumers and any tooling that scans `saved_models/`.

Testing and debug tips:
- Unit tests live under `api/tests/` and `tests/`. See `api/tests/README.md` and run tests with pytest from repo root (install test deps). Example: `python -m pytest api/tests -q`.
- For quick manual checks use curl to hit health: `GET http://localhost:8000/health` (FastAPI default path from `api/controllers/health.py`).

If you need more context or want me to extend this with examples (curl bodies, pytest snippets, or merge an existing copilot file), tell me which area to expand.
