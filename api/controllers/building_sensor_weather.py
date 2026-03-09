from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.connection import get_db
from typing import Annotated
from datetime import datetime
import os
from utils.hashing import hash_object
from utils.auth_dependencies import get_current_user_role
from utils.policies import has_permission
from models.hvac_models import Building
from models.sensor import Sensor

router = APIRouter(
    prefix="/building-sensor-weather",
    tags=["Building Sensor Weather"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
)

def convert(obj):
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

@router.get(
    "/",
    summary="Get combined sensor and weather data for a building",
    responses={500: {"description": "Internal Server Error"}},
)
def get_building_sensor_weather(
    building_id: Annotated[int, Query(description="Building ID")],
    start_time: Annotated[datetime, Query(description="Start time (ISO format)")],
    end_time: Annotated[datetime, Query(description="End time (ISO format)")],
    db: Annotated[Session, Depends(get_db)],
    user=Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))
):
    user_id = user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=403, detail="User ID missing in token.")
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to access this building's data.")
    try:
        # Example: fetch sensors and weather for the building using SQLAlchemy
        sensors = db.query(Sensor).filter(Sensor.building_id == building_id).all()
        sensor_data = [
            {
                "id": s.id,
                "type": s.type,
                "lat": s.lat,
                "lon": s.lon,
                "rate_of_sampling": s.rate_of_sampling,
                "unit": s.unit,
                "room": s.room,
                "zone": s.zone,
                "central_unit": s.central_unit
            }
            for s in sensors
        ]
        # Weather data: placeholder, replace with actual weather query
        weather_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "building_id": building_id,
            "weather": "Sample weather data"
        }
        results = {"sensors": sensor_data, "weather": weather_data}
        response_hash = hash_object(results)
        return {"data": results, "hash": response_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying data: {str(e)}")

@router.post("/verify", summary="Verify hash for building sensor weather data", responses={500: {"description": "Internal Server Error"}})
def verify_building_sensor_weather(
    building_id: Annotated[int, Query(description="Building ID")],
    start_time: Annotated[datetime, Query(description="Start time (ISO format)")],
    end_time: Annotated[datetime, Query(description="End time (ISO format)")],
    hash_value: Annotated[str, Query(description="Hash to verify")],
    db: Annotated[Session, Depends(get_db)]
):
    try:
        sensors = db.query(Sensor).filter(Sensor.building_id == building_id).all()
        sensor_data = [
            {
                "id": s.id,
                "type": s.type,
                "lat": s.lat,
                "lon": s.lon,
                "rate_of_sampling": s.rate_of_sampling,
                "unit": s.unit,
                "room": s.room,
                "zone": s.zone,
                "central_unit": s.central_unit
            }
            for s in sensors
        ]
        weather_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "building_id": building_id,
            "weather": "Sample weather data"
        }
        results = {"sensors": sensor_data, "weather": weather_data}
        computed_hash = hash_object(results)
        return {"valid": computed_hash == hash_value, "computed_hash": computed_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying hash: {str(e)}")
