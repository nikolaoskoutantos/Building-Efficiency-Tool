USER_NOT_FOUND_DESC = "User not found."
from fastapi import APIRouter, HTTPException, Depends, status
from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.policies import has_permission
from typing import Annotated, Optional, List
import uuid
import secrets
import bcrypt
from datetime import datetime, timezone
from sqlalchemy import func
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from models.hvac_models import Building
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import SessionLocal

router = APIRouter(prefix="/devices", tags=["Device Management"])

# String constants to avoid duplication (SonarQube S1192)
DEVICE_NOT_FOUND = "Device not found"
DEVICE_NOT_FOUND_DESC = "Device not found."
HVAC_UNIT_NOT_FOUND = "HVAC unit not found"
HVAC_UNIT_NOT_FOUND_DESC = "HVAC unit not found."
UNAUTHORIZED_DESC = "Unauthorized."
INTERNAL_SERVER_ERROR_DESC = "Internal server error."
UPDATE_DEVICE_LOG_PREFIX = "[update_device]"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]

# --- Response Models ---
class DeviceListResponse(BaseModel):
    id: int
    building_id: int
    building_name: str
    central_unit: Optional[str] = None
    zone: Optional[str] = None
    room: Optional[str] = None
    device_key: str  # Required again since we filter out None values
    sensor_count: int = 0  # Real sensor count
    created_at: Optional[str] = None

class SensorResponse(BaseModel):
    id: int
    type: Optional[str] = None
    lat: float
    lon: float
    rate_of_sampling: float
    unit: str
    room: Optional[str] = None
    zone: Optional[str] = None
    central_unit: Optional[str] = None

class SensorAddResponse(BaseModel):
    message: str
    sensors_added: int

# --- Request Models ---
class SensorRegistrationRequest(BaseModel):
    type: Optional[str] = None
    lat: float
    lon: float
    rate_of_sampling: Optional[float] = 5.0  # Default 5 seconds
    unit: str
    room: Optional[str] = None
    zone: Optional[str] = None
    central_unit: Optional[str] = None
    description: Optional[str] = None

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

class SensorBulkAddRequest(BaseModel):
    device_id: int
    sensors: List[SensorRegistrationRequest]

# --- Endpoints ---

@router.get(
    "/",
    response_model=List[DeviceListResponse],
    responses={
        401: {"description": UNAUTHORIZED_DESC},
        403: {"description": UNAUTHORIZED_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def list_devices(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Get all registered HVAC devices with real sensor counts (auth required)"""
    try:
        user_id = resolve_registered_user_id(user, db)
        sensor_count_subquery = (
            db.query(
                Sensor.hvac_unit_id,
                func.count(Sensor.id).label('sensor_count')
            )
            .group_by(Sensor.hvac_unit_id)
            .subquery()
        )
        # Main query joining devices, buildings, and sensor counts
        devices_query = (
            db.query(
                HVACUnit,
                Building.name.label('building_name'),
                func.coalesce(sensor_count_subquery.c.sensor_count, 0).label('sensor_count')
            )
            .outerjoin(Building, HVACUnit.building_id == Building.id)
            .outerjoin(sensor_count_subquery, HVACUnit.id == sensor_count_subquery.c.hvac_unit_id)
            .all()
        )
        
        result = []
        for device, building_name, sensor_count in devices_query:
            # Only include devices with valid device keys
            device_key = device.device_key
            if device_key is None or device_key.strip() == "":
                continue  # Skip devices without valid keys
            if not has_permission(user_id, "device", device.id, db):
                continue
                
            result.append(DeviceListResponse(
                id=device.id,
                building_id=device.building_id,
                building_name=building_name or "Unknown Building",
                central_unit=device.central_unit,
                zone=device.zone,
                room=device.room,
                device_key=device_key,
                sensor_count=int(sensor_count),
                created_at=None
            ))
        
        return result
    except Exception as e:
        print(f"[list_devices] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{device_id}/sensors",
    response_model=List[SensorResponse],
    responses={
        404: {"description": DEVICE_NOT_FOUND_DESC},
        401: {"description": UNAUTHORIZED_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def get_device_sensors(
    device_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Get all sensors for a specific device"""
    try:
        user_id = resolve_registered_user_id(user, db)
        # Verify device exists
        device = db.query(HVACUnit).filter(HVACUnit.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND)
        if not has_permission(user_id, "device", device_id, db):
            raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
        
        # Get sensors for this device
        sensors = db.query(Sensor).filter(Sensor.hvac_unit_id == device_id).all()
        
        return [
            SensorResponse(
                id=sensor.id,
                type=sensor.type,
                lat=sensor.lat,
                lon=sensor.lon,
                rate_of_sampling=sensor.rate_of_sampling,
                unit=sensor.unit,
                room=sensor.room,
                zone=sensor.zone,
                central_unit=sensor.central_unit
            )
            for sensor in sensors
        ]
    except HTTPException:
        raise
    except Exception as e:
        print(f"[get_device_sensors] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/sensors",
    response_model=SensorAddResponse,
    responses={
        400: {"description": "Invalid input or device not found."},
        401: {"description": UNAUTHORIZED_DESC},
        404: {"description": DEVICE_NOT_FOUND_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def add_sensors_to_device(
    req: SensorBulkAddRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    """Add multiple sensors to an existing HVAC device"""
    user_id = resolve_registered_user_id(user, db)
    # Verify device exists
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == req.device_id).first()
    if not hvac_unit:
        raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND_DESC)
    
    # Add sensors
    sensors_added = 0
    for s in req.sensors:
        if not has_permission(user_id, "building", hvac_unit.building_id, db):
            raise HTTPException(status_code=401, detail=UNAUTHORIZED_DESC)
        sensor = Sensor(
            building_id=hvac_unit.building_id,
            hvac_unit_id=hvac_unit.id,
            type=s.type,
            lat=s.lat,
            lon=s.lon,
            rate_of_sampling=s.rate_of_sampling,
            unit=s.unit,
            room=s.room,
            zone=s.zone,
            central_unit=s.central_unit
        )
        db.add(sensor)
        sensors_added += 1
    
    db.commit()
    
    return SensorAddResponse(
        message=f"Successfully added {sensors_added} sensor(s) to device {req.device_id}",
        sensors_added=sensors_added
    )

@router.post(
    "/register",
    response_model=DeviceCredentialResponse,
    responses={
        400: {"description": "Invalid input or device already exists for this location."},
        401: {"description": UNAUTHORIZED_DESC},
        404: {"description": "Building not found."},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def register_device(
    req: DeviceRegistrationRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", req.building_id, db):
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
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
            if not has_permission(user_id, "building", req.building_id, db):
                raise HTTPException(status_code=401, detail=UNAUTHORIZED_DESC)
            sensor = Sensor(
                building_id=req.building_id,
                hvac_unit_id=hvac_unit.id,
                type=s.type,
                lat=s.lat,
                lon=s.lon,
                rate_of_sampling=s.rate_of_sampling,
                unit=s.unit,
                room=s.room,
                zone=s.zone,
                central_unit=s.central_unit
            )
            db.add(sensor)
        db.commit()

    return DeviceCredentialResponse(device_key=device_key, device_secret=device_secret)

@router.put(
    "/{hvac_unit_id}",
    response_model=dict,
    responses={
        400: {"description": "Invalid input or validation error."},
        401: {"description": UNAUTHORIZED_DESC},
        404: {"description": DEVICE_NOT_FOUND_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def update_device(
    hvac_unit_id: int,
    req: DeviceRegistrationRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    """Update an existing HVAC device and its sensors"""
    try:
        user_id = resolve_registered_user_id(user, db)
        # Find the existing device
        hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
        if not hvac_unit:
            raise HTTPException(status_code=404, detail=HVAC_UNIT_NOT_FOUND)
        if not has_permission(user_id, "device", hvac_unit_id, db):
            raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
        if not has_permission(user_id, "building", req.building_id, db):
            raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)

        # Update HVAC unit fields
        hvac_unit.building_id = req.building_id
        hvac_unit.central_unit = req.central_unit
        hvac_unit.zone = req.zone
        hvac_unit.room = req.room

        # Delete existing sensors for this device (handle foreign key constraints)
        print(f"{UPDATE_DEVICE_LOG_PREFIX} Starting sensor cleanup for device {hvac_unit_id}")
        existing_sensors = db.query(Sensor).filter(Sensor.hvac_unit_id == hvac_unit_id).all()
        print(f"{UPDATE_DEVICE_LOG_PREFIX} Found {len(existing_sensors)} sensors to clean up")
        
        for sensor in existing_sensors:
            print(f"{UPDATE_DEVICE_LOG_PREFIX} Cleaning up sensor {sensor.id}")
            # Delete all sensor data records that reference this sensor from all tables
            from models.sensordata import SensorData, HVACSensorData, SensorDataRaw
            
            sensor_data_count = db.query(SensorData).filter(SensorData.sensor_id == sensor.id).count()
            hvac_data_count = db.query(HVACSensorData).filter(HVACSensorData.sensor_id == sensor.id).count()
            raw_data_count = db.query(SensorDataRaw).filter(SensorDataRaw.sensor_id == sensor.id).count()
            
            print(f"{UPDATE_DEVICE_LOG_PREFIX} Sensor {sensor.id} has {sensor_data_count} SensorData, {hvac_data_count} HVACSensorData, {raw_data_count} SensorDataRaw records")
            
            db.query(SensorData).filter(SensorData.sensor_id == sensor.id).delete(synchronize_session=False)
            db.query(HVACSensorData).filter(HVACSensorData.sensor_id == sensor.id).delete(synchronize_session=False)
            db.query(SensorDataRaw).filter(SensorDataRaw.sensor_id == sensor.id).delete(synchronize_session=False)
            
        # Flush changes to database before deleting sensors
        db.flush()
        print(f"{UPDATE_DEVICE_LOG_PREFIX} All sensor data deleted, now deleting sensors")
            
        # Now we can safely delete the sensors
        db.query(Sensor).filter(Sensor.hvac_unit_id == hvac_unit_id).delete(synchronize_session=False)
        
        # Add new sensors if provided
        if req.sensors:
            for s in req.sensors:
                if not has_permission(user_id, "building", req.building_id, db):
                    raise HTTPException(status_code=401, detail=UNAUTHORIZED_DESC)
                sensor = Sensor(
                    building_id=req.building_id,
                    hvac_unit_id=hvac_unit.id,
                    type=s.type,
                    lat=s.lat,
                    lon=s.lon,
                    rate_of_sampling=s.rate_of_sampling,
                    unit=s.unit,
                    room=s.room,
                    zone=s.zone,
                    central_unit=s.central_unit
                )
                db.add(sensor)

        db.commit()
        
        return {"message": "Device updated successfully", "device_id": hvac_unit_id}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"{UPDATE_DEVICE_LOG_PREFIX} Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/{hvac_unit_id}/credentials/upsert",
    response_model=DeviceCredentialResponse,
    responses={
        404: {"description": HVAC_UNIT_NOT_FOUND_DESC},
        401: {"description": UNAUTHORIZED_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def upsert_device_credentials(
    db: Annotated[Session, Depends(get_db)],
    hvac_unit_id: int,
    req: Optional[DeviceCredentialUpsertRequest] = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None,
):
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not hvac_unit:
        raise HTTPException(status_code=404, detail=HVAC_UNIT_NOT_FOUND_DESC)
    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "device", hvac_unit.id, db):
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
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
