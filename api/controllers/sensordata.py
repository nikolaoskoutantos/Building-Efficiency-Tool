from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Annotated
import jwt
from models.sensor import Sensor
from models.hvac_unit import HVACUnit
import os
from datetime import timezone
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensordata import SensorData
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.policies import has_permission

router = APIRouter(prefix="/sensordata", tags=["SensorData"])

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
    response_model=SensorDataRead,
    responses={
        404: {"description": "SensorData or Sensor not found"},
        401: {"description": "Unauthorized: Missing/invalid/expired device token"},
        403: {"description": "Forbidden: Device not authorized to write to this sensor, or device revoked"},
        500: {"description": "Internal server error"}
    },
)
def create_sensor_data(
    data: SensorDataCreate,
    db: Annotated[Session, Depends(get_db)],
    device_jwt: Annotated[dict, Depends(get_device_identity)]
):
    # Validate that the sensor belongs to the device
    sensor = db.query(Sensor).filter(Sensor.id == data.sensor_id).first()
    if not sensor or sensor.hvac_unit_id != int(device_jwt["sub"]):
        raise HTTPException(status_code=403, detail="Device not authorized to write to this sensor")
    db_data = SensorData(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data

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
