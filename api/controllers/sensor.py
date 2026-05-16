
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensor import Sensor
from typing import List
from pydantic import BaseModel
from utils.unit_resolver import canonicalize_unit

# Reused literals
SENSOR_NOT_FOUND_MSG = "Sensor not found"
SENSOR_RESOURCE = "sensor"
MANAGER_ADMIN_ROLES = ["BUILDING_MANAGER", "ADMIN"]
SENSOR_ACCESS_ROLES = ["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]
CREATE_SENSOR_UNAUTHORIZED_MSG = "You are not authorized to create sensors in this building."
VIEW_SENSORS_UNAUTHORIZED_MSG = "You are not authorized to view sensors."
VIEW_SENSOR_UNAUTHORIZED_MSG = "You are not authorized to view this sensor."
UPDATE_SENSOR_UNAUTHORIZED_MSG = "You are not authorized to update this sensor."
DELETE_SENSOR_UNAUTHORIZED_MSG = "You are not authorized to delete this sensor."
SENSOR_DELETED_MSG = "Sensor deleted"

from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.policies import has_permission
router = APIRouter(
    prefix="/sensors",
    tags=["Sensors"],
    dependencies=[Depends(get_current_user_role(SENSOR_ACCESS_ROLES))]
)

# Pydantic schemas
class SensorBase(BaseModel):
    building_id: int
    name: str
    sensor_type: str
    unit: Optional[str] = None
    hvac_unit_id: Optional[int] = None
    room_id: Optional[int] = None
    zone_id: Optional[int] = None
    thermostat_id: Optional[int] = None
    external_sensor_id: Optional[str] = None
    external_bms_id: Optional[str] = None
    payload_path: Optional[str] = None

class SensorCreate(SensorBase):
    pass

class SensorUpdate(BaseModel):
    building_id: Optional[int] = None
    name: Optional[str] = None
    sensor_type: Optional[str] = None
    unit: Optional[str] = None
    hvac_unit_id: Optional[int] = None
    room_id: Optional[int] = None
    zone_id: Optional[int] = None
    thermostat_id: Optional[int] = None
    external_sensor_id: Optional[str] = None
    external_bms_id: Optional[str] = None
    payload_path: Optional[str] = None

class SensorRead(SensorBase):
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
    "/",
    response_model=SensorRead,
    responses={
        403: {"description": CREATE_SENSOR_UNAUTHORIZED_MSG},
        404: {"description": SENSOR_NOT_FOUND_MSG}
    }
)
def create_sensor(sensor: SensorCreate, db: Annotated[Session, Depends(get_db)], user: Annotated[dict, Depends(get_current_user_role(MANAGER_ADMIN_ROLES))]):
    user_id = resolve_registered_user_id(user, db)
    # Resource-level permission: user can only create sensors in buildings they manage
    if user_id is None or not has_permission(user_id, "building", sensor.building_id, db):
        raise HTTPException(status_code=403, detail=CREATE_SENSOR_UNAUTHORIZED_MSG)
    data = sensor.model_dump()
    canonical_unit, unit_id = canonicalize_unit(data.get("unit"), db)
    data["unit"] = canonical_unit
    data["unit_id"] = unit_id
    db_sensor = Sensor(**data)
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@router.get(
    "/",
    response_model=List[SensorRead],
    responses={
        403: {"description": VIEW_SENSORS_UNAUTHORIZED_MSG}
    }
)
def read_sensors(db: Annotated[Session, Depends(get_db)], user: Annotated[dict, Depends(get_current_user_role(SENSOR_ACCESS_ROLES))], skip: int = 0, limit: int = 100):
    user_id = resolve_registered_user_id(user, db)
    # Only return sensors in buildings the user manages
    if user_id is None:
        raise HTTPException(status_code=403, detail=VIEW_SENSORS_UNAUTHORIZED_MSG)
    sensors = db.query(Sensor).all()
    # Filter sensors by permission
    return [s for s in sensors if has_permission(user_id, SENSOR_RESOURCE, s.id, db)]

@router.get(
    "/{sensor_id}",
    response_model=SensorRead,
    responses={
        403: {"description": VIEW_SENSOR_UNAUTHORIZED_MSG},
        404: {"description": SENSOR_NOT_FOUND_MSG}
    }
)
def read_sensor(sensor_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[dict, Depends(get_current_user_role(SENSOR_ACCESS_ROLES))]):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    user_id = resolve_registered_user_id(user, db)
    if not sensor:
        raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND_MSG)
    if user_id is None or not has_permission(user_id, SENSOR_RESOURCE, sensor_id, db):
        raise HTTPException(status_code=403, detail=VIEW_SENSOR_UNAUTHORIZED_MSG)
    return sensor

@router.put(
    "/{sensor_id}",
    response_model=SensorRead,
    responses={
        403: {"description": UPDATE_SENSOR_UNAUTHORIZED_MSG},
        404: {"description": SENSOR_NOT_FOUND_MSG}
    }
)
def update_sensor(sensor_id: int, sensor: SensorUpdate, db: Annotated[Session, Depends(get_db)], user: Annotated[dict, Depends(get_current_user_role(MANAGER_ADMIN_ROLES))]):
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    user_id = resolve_registered_user_id(user, db)
    if not db_sensor:
        raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND_MSG)
    if user_id is None or not has_permission(user_id, SENSOR_RESOURCE, sensor_id, db):
        raise HTTPException(status_code=403, detail=UPDATE_SENSOR_UNAUTHORIZED_MSG)
    updates = sensor.model_dump(exclude_unset=True)
    if "unit" in updates:
        canonical_unit, unit_id = canonicalize_unit(updates.get("unit"), db)
        updates["unit"] = canonical_unit
        updates["unit_id"] = unit_id
    # Never allow hvac_unit_id to be silently cleared via a unit/name edit;
    # caller must explicitly pass a non-null value to change the device association.
    if updates.get("hvac_unit_id") is None:
        updates.pop("hvac_unit_id", None)
    for key, value in updates.items():
        setattr(db_sensor, key, value)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@router.delete(
    "/{sensor_id}",
    responses={
        200: {"description": SENSOR_DELETED_MSG},
        403: {"description": DELETE_SENSOR_UNAUTHORIZED_MSG},
        404: {"description": SENSOR_NOT_FOUND_MSG}
    }
)
def delete_sensor(sensor_id: int, db: Annotated[Session, Depends(get_db)], user: Annotated[dict, Depends(get_current_user_role(MANAGER_ADMIN_ROLES))]):
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    user_id = resolve_registered_user_id(user, db)
    if not db_sensor:
        raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND_MSG)
    if user_id is None or not has_permission(user_id, SENSOR_RESOURCE, sensor_id, db):
        raise HTTPException(status_code=403, detail=DELETE_SENSOR_UNAUTHORIZED_MSG)
    db.delete(db_sensor)
    db.commit()
    return {"detail": SENSOR_DELETED_MSG}
