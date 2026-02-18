from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from db.connection import SessionLocal, engine, Base
from models.hvac_models import Building
from models.service import Service  # Import Service model to ensure table creation
from models.sensor import Sensor
from models.sensordata import SensorData  # Import SensorData model to ensure table creation
from models.rate import Rate  # Import Rate model to ensure table creation
from models.predictor import Predictor, TrainingHistory  # Import updated models
from models.knowledge import Knowledge
from services.hvac_optimizer_service import HVACOptimizerService  # Import HVAC service
from models.hvac_unit import HVACUnit  
from db.mock_data import insert_mock_data  # Updated import path
from utils.sql import apply_sql_file
app = FastAPI()

# Add session middleware for login/logout
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# Serve Vue.js static files (production build) if available
vue_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ui/dist'))
if os.path.isdir(vue_dist_path):
    app.mount("/", StaticFiles(directory=vue_dist_path, html=True), name="static")



# Create database tables
Base.metadata.create_all(bind=engine)

# Apply stored procedure/function after tables exist
update_fn_path = os.path.join(os.path.dirname(__file__), 'db', 'update_function.sql')
if os.path.exists(update_fn_path):
    apply_sql_file(update_fn_path, engine)
    print("✅ Applied update_function.sql after table creation.")
else:
    print(f"⚠️ update_function.sql not found at {update_fn_path}")

# Insert mock data if DEV mode is enabled
if os.getenv("DEV", "false").lower() == "true":
    try:
        print("[main.py] DEV mode enabled: inserting mock data...")
        insert_mock_data()
    except Exception as e:
        print(f"[main.py] Warning: mock data insertion failed: {e}")

# Allow CORS for local development (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Vue.js dev server
        "http://localhost:5173",  # Vite dev server (alternative port)
        "http://127.0.0.1:3000",  # Alternative localhost format
        "http://127.0.0.1:5173",  # Alternative localhost format
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from controllers.building_sensor_weather import router as building_sensor_weather_router

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(service_router)
app.include_router(sensor_router)
app.include_router(rate_router)
app.include_router(weather_router)
app.include_router(sensordata_router)
app.include_router(smartcontract_router)
app.include_router(predict_router)
app.include_router(building_sensor_weather_router)
