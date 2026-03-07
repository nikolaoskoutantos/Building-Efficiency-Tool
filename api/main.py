from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
import os
from controllers.health import router as health_router
from controllers.service import router as service_router
from controllers.sensor import router as sensor_router
from controllers.rate import router as rate_router
from controllers.weather import router as weather_router
from controllers.sensordata import router as sensordata_router
from controllers.smartcontract import router as smartcontract_router
from controllers.predict import router as predict_router
from controllers.auth import router as auth_router
from controllers.building_sensor_weather import router as building_sensor_weather_router
from controllers.hvac import router as hvac_router
from controllers.acl import router as acl_router
from controllers.devices import router as devices_router
from controllers.buildings import router as buildings_router
from controllers.user_settings import router as user_settings_router
from controllers.mqtt import router as mqtt_router
from controllers.dashboard import router as dashboard_router
from utils.emqx_acl_middleware import EMQXACLHeaderMiddleware
from db.connection import SessionLocal, engine, Base
from models.hvac_models import Building
from models.service import Service  # Import Service model to ensure table creation
from models.sensor import Sensor
from models.sensordata import SensorData  # Import SensorData model to ensure table creation
from models.rate import Rate  # Import Rate model to ensure table creation
from models.predictor import Predictor, TrainingHistory  # Import updated models
from models.knowledge import Knowledge
from models.mqtt_config import MQTTBrokerConfig
from services.hvac_optimizer_service import HVACOptimizerService  # Import HVAC service
from db.mock_data import insert_mock_data  # Updated import path
from utils.sql import apply_sql_file
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,  # overrides existing uvicorn logging config
)

# Cron Scheduler for weather updates
from services.weather_service import setup_weather_scheduler
from db.connection import async_session_maker

@asynccontextmanager
async def lifespan(app):
    setup_weather_scheduler(async_session_maker)
    yield

app = FastAPI(lifespan=lifespan)
# app.add_middleware(EMQXACLHeaderMiddleware)

# Add session middleware for login/logout
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# Configure CORS origins from environment variables
def get_cors_origins():
    """Get CORS allowed origins from environment variables."""
    # Default development origins
    default_origins = [
        "http://localhost:3000",   # Vue.js dev server
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3001",   # Vue.js alternative port
        "http://127.0.0.1:3000",   # Alternative localhost format
        "http://127.0.0.1:5173",   # Alternative localhost format
        "http://127.0.0.1:3001",   # Alternative localhost format
    ]
    
    # Get custom origins from environment variable
    custom_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if custom_origins:
        custom_list = [origin.strip() for origin in custom_origins.split(",") if origin.strip()]
        default_origins.extend(custom_list)
    
    # Add local network origins if configured
    local_ip = os.getenv("LOCAL_NETWORK_IP")
    local_ports = os.getenv("LOCAL_NETWORK_PORTS", "3000,3001,5173")
    if local_ip:
        ports = [port.strip() for port in local_ports.split(",") if port.strip()]
        for port in ports:
            default_origins.append(f"http://{local_ip}:{port}")
    
    return list(set(default_origins))  # Remove duplicates

# Allow CORS for configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Vue.js static files (production build) if available
vue_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ui/dist'))
if os.path.isdir(vue_dist_path):
    app.mount("/", StaticFiles(directory=vue_dist_path, html=True), name="static")


# Create database tables
Base.metadata.create_all(bind=engine)

# Apply SQL bootstrap functions (idempotent CREATE OR REPLACE FUNCTION statements)
try:
    update_function_sql_path = os.path.join(os.path.dirname(__file__), "db", "update_function.sql")
    apply_sql_file(update_function_sql_path, engine)
    print("[main.py] Applied db/update_function.sql")
except Exception as e:
    print(f"[main.py] Warning: failed to apply db/update_function.sql: {e}")

# Apply user settings migration (idempotent ALTER TABLE statements)
try:
    user_settings_migration_path = os.path.join(os.path.dirname(__file__), "db", "migration_user_settings.sql")
    apply_sql_file(user_settings_migration_path, engine)
    print("[main.py] Applied db/migration_user_settings.sql")
except Exception as e:
    print(f"[main.py] Warning: failed to apply db/migration_user_settings.sql: {e}")

# Insert mock data if DEV mode is enabled
if os.getenv("DEV", "false").lower() == "true":
    try:
        print("[main.py] DEV mode enabled: inserting mock data...")
        insert_mock_data()
    except Exception as e:
        print(f"[main.py] Warning: mock data insertion failed: {e}")

app.include_router(health_router)
app.include_router(auth_router, prefix="/auth")
app.include_router(service_router)
app.include_router(sensor_router)
app.include_router(rate_router)
app.include_router(weather_router)
app.include_router(sensordata_router)
app.include_router(smartcontract_router)
app.include_router(predict_router)
app.include_router(building_sensor_weather_router)
app.include_router(hvac_router)
app.include_router(acl_router)
app.include_router(devices_router)
app.include_router(buildings_router)
app.include_router(user_settings_router)
app.include_router(mqtt_router)
app.include_router(dashboard_router)
