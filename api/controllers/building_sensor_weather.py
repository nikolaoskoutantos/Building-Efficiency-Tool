

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.connection import get_db
from typing import Annotated
from datetime import datetime
import psycopg2
import os
from utils.hashing import hash_object

router = APIRouter(prefix="/building-sensor-weather", tags=["Building Sensor Weather"])

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
    db: Annotated[Session, Depends(get_db)]
):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM get_building_sensor_weather(%s, %s, %s)",
            (building_id, start_time, end_time)
        )
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        serializable_results = convert(results)
        response_hash = hash_object(serializable_results)
        return {"data": results, "hash": response_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying function: {str(e)}")

@router.post("/verify", summary="Verify hash for building sensor weather data", responses={500: {"description": "Internal Server Error"}})
def verify_building_sensor_weather(
    building_id: Annotated[int, Query(description="Building ID")],
    start_time: Annotated[datetime, Query(description="Start time (ISO format)")],
    end_time: Annotated[datetime, Query(description="End time (ISO format)")],
    hash_value: Annotated[str, Query(description="Hash to verify")],
    db: Annotated[Session, Depends(get_db)]
):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM get_building_sensor_weather(%s, %s, %s)",
            (building_id, start_time, end_time)
        )
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        serializable_results = convert(results)
        computed_hash = hash_object(serializable_results)
        return {"valid": computed_hash == hash_value, "computed_hash": computed_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying hash: {str(e)}")
