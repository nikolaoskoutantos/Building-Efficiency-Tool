from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Annotated, Any, Dict
import jwt
from models.sensor import Sensor
from models.hvac_unit import HVACUnit
import os
from datetime import timezone
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensordata import SensorData, SensorDataRaw
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.policies import has_permission

router = APIRouter(prefix="/sensordata", tags=["SensorData"])

MAX_BULK_RECORDS = int(os.environ.get("SENSOR_BULK_MAX_RECORDS", "1000"))

# Pydantic schemas
class SensorDataBase(BaseModel):
    sensor_id: int
    timestamp: Optional[datetime] = None
    value: float

class SensorDataCreate(SensorDataBase):
    pass

class SensorDataRead(SensorDataBase):
    id: int
    class Config:
        from_attributes = True

class SensorDataRawBase(BaseModel):
    sensor_id: int
    timestamp: Optional[datetime] = None
    value: Optional[float] = None
    measurement_type: str = "temperature"
    unit: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

class SensorDataRawCreate(SensorDataRawBase):
    pass

class SensorDataRawRead(SensorDataRawBase):
    id: int
    class Config:
        from_attributes = True

def sensor_data_payload(data: SensorDataCreate):
    return data.dict(exclude_none=True)

def sensor_data_raw_payload(data: SensorDataRawCreate):
    return data.dict(exclude_none=True)

def validate_device_sensor_ids(
    db: Session,
    sensor_ids: List[int],
    device_id: int
):
    unique_sensor_ids = list(set(sensor_ids))
    sensors = db.query(Sensor).filter(Sensor.id.in_(unique_sensor_ids)).all()
    authorized_sensor_ids = {
        sensor.id
        for sensor in sensors
        if sensor.hvac_unit_id == device_id
    }
    unauthorized_sensor_ids = [
        sensor_id
        for sensor_id in unique_sensor_ids
        if sensor_id not in authorized_sensor_ids
    ]
    if unauthorized_sensor_ids:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Device not authorized to write to one or more sensors",
                "sensor_ids": unauthorized_sensor_ids
            }
        )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/auth_device",
    response_model=dict,
    responses={
        401: {"description": "Missing or invalid Authorization header, or invalid/expired device token"},
        403: {"description": "Not a device token, or device revoked/not found"},
        500: {"description": "Internal server error"}
    }
)
def get_device_identity(
    authorization: Annotated[str, Header()],
    db: Annotated[Session, Depends(get_db)]
):
    JWT_SECRET = os.environ.get("SESSION_SECRET_KEY")
    JWT_ALGORITHM = "HS256"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired device token")
    if payload.get("typ") != "device":
        raise HTTPException(status_code=403, detail="Not a device token")
    # Optionally, check device is not revoked
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == int(payload["sub"])).first()
    if not hvac_unit or hvac_unit.device_revoked_at:
        raise HTTPException(status_code=403, detail="Device revoked or not found")
    return payload

@router.post(
    "/",
    response_model=SensorDataRawRead,
    responses={
        404: {"description": "SensorData or Sensor not found"},
        401: {"description": "Unauthorized: Missing/invalid/expired device token"},
        403: {"description": "Forbidden: Device not authorized to write to this sensor, or device revoked"},
        500: {"description": "Internal server error"}
    },
)
def create_sensor_data(
    data: SensorDataRawCreate,
    db: Annotated[Session, Depends(get_db)],
    device_jwt: Annotated[dict, Depends(get_device_identity)]
):
    validate_device_sensor_ids(db, [data.sensor_id], int(device_jwt["sub"]))
    db_data = SensorDataRaw(**sensor_data_raw_payload(data))
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data

@router.post(
    "/bulk",
    response_model=List[SensorDataRawRead],
    responses={
        400: {"description": "Empty payload"},
        401: {"description": "Unauthorized: Missing/invalid/expired device token"},
        403: {"description": "Forbidden: Device not authorized to write to one or more sensors, or device revoked"},
        500: {"description": "Internal server error"}
    },
)
def create_sensor_data_bulk(
    data: List[SensorDataRawCreate],
    db: Annotated[Session, Depends(get_db)],
    device_jwt: Annotated[dict, Depends(get_device_identity)]
):
    if not data:
        raise HTTPException(status_code=400, detail="Bulk sensor data payload cannot be empty")
    if len(data) > MAX_BULK_RECORDS:
        raise HTTPException(
            status_code=400,
            detail=f"Bulk payload exceeds maximum of {MAX_BULK_RECORDS} records per request."
        )

    validate_device_sensor_ids(
        db,
        [item.sensor_id for item in data],
        int(device_jwt["sub"])
    )

    db_rows = [
        SensorDataRaw(**sensor_data_raw_payload(item))
        for item in data
    ]
    db.add_all(db_rows)
    db.commit()
    for row in db_rows:
        db.refresh(row)
    return db_rows

@router.get("/", response_model=List[SensorDataRead])
def read_sensor_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))],
    skip: int = 0,
    limit: int = 100
):
    user_id = resolve_registered_user_id(user, db)
    sensor_data_rows = db.query(SensorData).offset(skip).limit(limit).all()
    return [row for row in sensor_data_rows if has_permission(user_id, "sensor", row.sensor_id, db)]

@router.get(
    "/{data_id}",
    response_model=SensorDataRead,
    responses={
        403: {"description": "You are not authorized to view this sensor data"},
        404: {"description": "SensorData not found"},
    }
)
def read_single_sensor_data(
    data_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    data = db.query(SensorData).filter(SensorData.id == data_id).first()
    if not data:
        raise HTTPException(status_code=404, detail="SensorData not found")
    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "sensor", data.sensor_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to view this sensor data")
    return data

@router.delete(
    "/{data_id}",
    responses={
        200: {"description": "SensorData deleted"},
        403: {"description": "You are not authorized to delete this sensor data"},
        404: {"description": "SensorData not found"},
    }
)
def delete_sensor_data(
    data_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    db_data = db.query(SensorData).filter(SensorData.id == data_id).first()
    if not db_data:
        raise HTTPException(status_code=404, detail="SensorData not found")
    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "sensor", db_data.sensor_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to delete this sensor data")
    db.delete(db_data)
    db.commit()
    return {"detail": "SensorData deleted"}
