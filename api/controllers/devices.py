from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated, Optional, List
import uuid
import secrets
import bcrypt
from datetime import datetime, timezone
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import SessionLocal

router = APIRouter(prefix="/devices", tags=["Device Management"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]

# --- Device Registration & Credential Upsert ---
class SensorRegistrationRequest(BaseModel):
    type: Optional[str] = None
    lat: float
    lon: float
    rate_of_sampling: float
    raw_data_id: int
    unit: str
    room: Optional[str] = None
    zone: Optional[str] = None
    central_unit: Optional[str] = None

class DeviceRegistrationRequest(BaseModel):
    building_id: int
    central_unit: Optional[str] = None
    zone: Optional[str] = None
    room: Optional[str] = None
    sensors: Optional[List[SensorRegistrationRequest]] = None

class DeviceCredentialResponse(BaseModel):
    device_key: str
    device_secret: str

class DeviceCredentialUpsertRequest(BaseModel):
    central_unit: Optional[str] = None
    zone: Optional[str] = None
    room: Optional[str] = None
    sensors: Optional[List[SensorRegistrationRequest]] = None

@router.post(
    "/register",
    response_model=DeviceCredentialResponse,
    responses={
        400: {"description": "Invalid input or device already exists for this location."},
        401: {"description": "Unauthorized."},
        404: {"description": "Building not found."},
        500: {"description": "Internal server error."}
    },
)
def register_device(
    req: DeviceRegistrationRequest,
    db: Annotated[Session, Depends(get_db)]
):
    device_key = str(uuid.uuid4())
    device_secret = secrets.token_urlsafe(48)
    device_secret_hash = bcrypt.hashpw(device_secret.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()

    hvac_unit = HVACUnit(
        building_id=req.building_id,
        central_unit=req.central_unit,
        zone=req.zone,
        room=req.room,
        device_key=device_key,
        device_secret_hash=device_secret_hash,
        device_secret_rotated_at=now,
        device_revoked_at=None
    )
    db.add(hvac_unit)
    db.commit()
    db.refresh(hvac_unit)

    if req.sensors:
        for s in req.sensors:
            sensor = Sensor(
                building_id=req.building_id,
                hvac_unit_id=hvac_unit.id,
                type=s.type,
                lat=s.lat,
                lon=s.lon,
                rate_of_sampling=s.rate_of_sampling,
                raw_data_id=s.raw_data_id,
                unit=s.unit,
                room=s.room,
                zone=s.zone,
                central_unit=s.central_unit
            )
            db.add(sensor)
        db.commit()

    return DeviceCredentialResponse(device_key=device_key, device_secret=device_secret)

@router.post(
    "/{hvac_unit_id}/credentials/upsert",
    response_model=DeviceCredentialResponse,
    responses={
        404: {"description": "HVAC unit not found."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."}
    },
)
def upsert_device_credentials(
    db: Annotated[Session, Depends(get_db)],
    hvac_unit_id: int,
    req: Optional[DeviceCredentialUpsertRequest] = None,
):
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not hvac_unit:
        raise HTTPException(status_code=404, detail="HVAC unit not found.")
    device_secret = secrets.token_urlsafe(48)
    device_secret_hash = bcrypt.hashpw(device_secret.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()
    hvac_unit.device_secret_hash = device_secret_hash
    hvac_unit.device_secret_rotated_at = now
    hvac_unit.device_revoked_at = None
    if req:
        if req.central_unit is not None:
            hvac_unit.central_unit = req.central_unit
        if req.zone is not None:
            hvac_unit.zone = req.zone
        if req.room is not None:
            hvac_unit.room = req.room
        if req.sensors:
            for s in req.sensors:
                sensor = Sensor(
                    building_id=hvac_unit.building_id,
                    hvac_unit_id=hvac_unit.id,
                    type=s.type,
                    lat=s.lat,
                    lon=s.lon,
                    rate_of_sampling=s.rate_of_sampling,
                    raw_data_id=s.raw_data_id,
                    unit=s.unit,
                    room=s.room,
                    zone=s.zone,
                    central_unit=s.central_unit
                )
                db.add(sensor)
            db.commit()
    db.commit()
    db.refresh(hvac_unit)
    return DeviceCredentialResponse(device_key=hvac_unit.device_key, device_secret=device_secret)
