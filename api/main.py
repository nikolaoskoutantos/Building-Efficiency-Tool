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
from db import SessionLocal, engine, Base
from models.service import Service  # Import Service model to ensure table creation
from models.sensor import Sensor
from models.sensordata import SensorData  # Import SensorData model to ensure table creation
from models.rate import Rate  # Import Rate model to ensure table creation
from models.predictor import Predictor
from models.knowledge import Knowledge
from utils.mock_data import insert_mock_data

app = FastAPI()

# Add session middleware for login/logout
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "your-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# Serve Vue.js static files (production build) if available
vue_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ui/dist'))
if os.path.isdir(vue_dist_path):
    app.mount("/", StaticFiles(directory=vue_dist_path, html=True), name="static")

# Create database tables and insert mock data if needed
Base.metadata.create_all(bind=engine)
insert_mock_data()

# Allow CORS for local development (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(service_router)
app.include_router(sensor_router)
app.include_router(rate_router)
app.include_router(weather_router)
app.include_router(sensordata_router)
app.include_router(smartcontract_router)
app.include_router(predict_router)
