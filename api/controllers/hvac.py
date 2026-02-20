SCHEDULE_NOT_FOUND = "Schedule not found"
SCHEDULE_DELETED = "Schedule deleted"

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated, Optional
import uuid
import secrets
import bcrypt
from datetime import datetime, timezone
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from db import SessionLocal
from models.hvac_models import HVACSchedule

router = APIRouter(prefix="/schedules", tags=["HVAC Schedules"])


# --- Device Registration & Credential Upsert ---

# Pydantic model for sensor registration
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
    # Optionally allow updating device info
    central_unit: Optional[str] = None
    zone: Optional[str] = None
    room: Optional[str] = None
    sensors: Optional[List[SensorRegistrationRequest]] = None

@router.post(
    "/register_device",
    response_model=DeviceCredentialResponse,
    responses={
        400: {"description": "Invalid input or device already exists for this location."},
        401: {"description": "Unauthorized."},
        404: {"description": "Building not found."},
        500: {"description": "Internal server error."}
    },
    tags=["Device Management"]
)
def register_device(
    req: DeviceRegistrationRequest,
    db: Annotated[Session, Depends(get_db)]
):
    # Generate device_key and device_secret
    device_key = str(uuid.uuid4())
    device_secret = secrets.token_urlsafe(48)
    device_secret_hash = bcrypt.hashpw(device_secret.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()

    # Create new HVACUnit
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

    # Register sensors if provided
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
    "/hvac_units/{hvac_unit_id}/credentials/upsert",
    response_model=DeviceCredentialResponse,
    responses={
        404: {"description": "HVAC unit not found."},
        401: {"description": "Unauthorized."},
        500: {"description": "Internal server error."}
    },
    tags=["Device Management"]
)
def upsert_device_credentials(
    db: Annotated[Session, Depends(get_db)],
    hvac_unit_id: int,
    req: Optional[DeviceCredentialUpsertRequest] = None,
    
):
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not hvac_unit:
        raise HTTPException(status_code=404, detail="HVAC unit not found.")
    # Generate new device_secret
    device_secret = secrets.token_urlsafe(48)
    device_secret_hash = bcrypt.hashpw(device_secret.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()
    hvac_unit.device_secret_hash = device_secret_hash
    hvac_unit.device_secret_rotated_at = now
    hvac_unit.device_revoked_at = None
    # Optionally update device info
    if req:
        if req.central_unit is not None:
            hvac_unit.central_unit = req.central_unit
        if req.zone is not None:
            hvac_unit.zone = req.zone
        if req.room is not None:
            hvac_unit.room = req.room
        # Add new sensors if provided
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

class SchedulePeriod(BaseModel):
    start: str  # 'HH:mm'
    end: str    # 'HH:mm'
    enabled: bool


class ScheduleCreate(BaseModel):
    hvac_id: int
    periods: List[SchedulePeriod]


class ScheduleRead(ScheduleCreate):
    id: int
    created_at: str
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]

@router.get(
    "/",
    response_model=List[ScheduleRead],
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def get_schedules(hvac_id: int = None, db: DbSession = None):
    q = db.query(HVACSchedule)
    if hvac_id is not None:
        q = q.filter(HVACSchedule.hvac_id == hvac_id)
    return q.order_by(HVACSchedule.created_at.desc()).all()

@router.post(
    "/",
    response_model=ScheduleRead,
    responses={
        400: {"description": "Invalid input"},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def create_schedule(schedule: ScheduleCreate, db: DbSession = None):
    db_schedule = HVACSchedule(hvac_id=schedule.hvac_id, periods=[p.dict() for p in schedule.periods])
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.get(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def get_schedule(schedule_id: int, db: DbSession = None):
    schedule = db.query(HVACSchedule).filter(HVACSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    return schedule

@router.put(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={
        400: {"description": "Invalid input"},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def update_schedule(schedule_id: int, schedule: ScheduleCreate, db: DbSession = None):
    db_schedule = db.query(HVACSchedule).filter(HVACSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    db_schedule.hvac_id = schedule.hvac_id
    db_schedule.periods = [p.dict() for p in schedule.periods]
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.delete(
    "/{schedule_id}",
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_schedule(schedule_id: int, db: DbSession = None):
    db_schedule = db.query(HVACSchedule).filter(HVACSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    db.delete(db_schedule)
    db.commit()
    return {"detail": SCHEDULE_DELETED}
