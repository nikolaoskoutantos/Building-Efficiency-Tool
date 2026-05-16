USER_NOT_FOUND_DESC = "User not found."
from fastapi import APIRouter, HTTPException, Depends, Header, status
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
from models.device_token import DeviceToken
from models.device_command import DeviceCommand
from models.topology import HVACZone, ZoneHVACUnit
from models.thermostat import Thermostat, ZoneThermostat
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import SessionLocal
from utils.unit_resolver import canonicalize_unit

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


# Defined here (before helper functions) so _create_device_zones can reference it at runtime
class ZoneRegistrationRequest(BaseModel):
    name: str
    zone_type: Optional[str] = None  # e.g. 'residential', 'office', 'industrial'


def _sensor_create_payload(
    building_id: int,
    hvac_unit_id: int,
    sensor_req: "SensorRegistrationRequest",
    db: Session,
    zone_name_to_id: Optional[dict] = None,
    room_name_to_id: Optional[dict] = None,
) -> dict:
    canonical_unit, unit_id = canonicalize_unit(sensor_req.unit, db)
    zone_id = sensor_req.zone_id
    if zone_id is None and sensor_req.zone_name and zone_name_to_id:
        zone_id = zone_name_to_id.get(sensor_req.zone_name)
    room_id = sensor_req.room_id
    if room_id is None and sensor_req.room_name and room_name_to_id:
        room_id = room_name_to_id.get(sensor_req.room_name)
    return {
        "building_id": building_id,
        "hvac_unit_id": hvac_unit_id,
        "name": sensor_req.name,
        "sensor_type": sensor_req.sensor_type,
        "unit": canonical_unit,
        "unit_id": unit_id,
        "room_id": room_id,
        "zone_id": zone_id,
        "thermostat_id": sensor_req.thermostat_id,
        "external_sensor_id": sensor_req.external_sensor_id,
        "payload_path": sensor_req.payload_path,
        "is_controllable": sensor_req.is_controllable,
        "command_payload_template": sensor_req.command_payload_template,
    }


def _build_sensor_for_device(
    building_id: int,
    hvac_unit_id: int,
    sensor_req: "SensorRegistrationRequest",
    db: Session,
    zone_name_to_id: Optional[dict] = None,
    room_name_to_id: Optional[dict] = None,
) -> Sensor:
    return Sensor(**_sensor_create_payload(building_id, hvac_unit_id, sensor_req, db, zone_name_to_id, room_name_to_id))


def _set_hvac_unit_fields(hvac_unit: HVACUnit, req: "DeviceRegistrationRequest") -> None:
    hvac_unit.building_id = req.building_id
    if req.name:
        hvac_unit.name = req.name
    if req.unit_type:
        hvac_unit.unit_type = req.unit_type


def _rotate_hvac_unit_credentials(hvac_unit: HVACUnit) -> str:
    """Rotate credentials on the existing HVACUnit row only.

    This helper never creates or replaces an HVACUnit. It mutates the current
    row in-place so related foreign keys keep pointing at the same id.
    """
    device_secret = secrets.token_urlsafe(48)
    device_secret_hash = bcrypt.hashpw(device_secret.encode(), bcrypt.gensalt()).decode()
    now = datetime.now(timezone.utc).isoformat()

    if not hvac_unit.device_key:
        hvac_unit.device_key = str(uuid.uuid4())

    hvac_unit.device_secret_hash = device_secret_hash
    hvac_unit.device_secret_rotated_at = now
    hvac_unit.device_revoked_at = None
    return device_secret


def _sync_thermostat_for_sensor(db: Session, sensor: Sensor, building_id: int) -> None:
    """For controllable sensors (or thermostat type), ensure a Thermostat row exists, link the
    sensor to it, and link the thermostat to the sensor's zone so the topology zone label works."""
    if sensor.sensor_type == "thermostat":
        sensor.is_controllable = True
    if not sensor.is_controllable:
        return
    thermostat = db.query(Thermostat).filter(
        Thermostat.building_id == building_id,
        Thermostat.name == sensor.name,
    ).first()
    if not thermostat:
        thermostat = Thermostat(building_id=building_id, name=sensor.name, is_controllable=True)
        db.add(thermostat)
        db.flush()
    else:
        thermostat.is_controllable = True
    sensor.thermostat_id = thermostat.id

    # Link thermostat → zone so the topology SQL (zone_primary_thermostat CTE) can
    # resolve the thermostat name and make the zone show as controllable.
    if sensor.zone_id:
        existing_link = db.query(ZoneThermostat).filter(
            ZoneThermostat.zone_id == sensor.zone_id,
            ZoneThermostat.thermostat_id == thermostat.id,
        ).first()
        if not existing_link:
            db.add(ZoneThermostat(zone_id=sensor.zone_id, thermostat_id=thermostat.id, role="primary"))


def _upsert_device_sensors(
    db: Session,
    sensors: Optional[List["SensorRegistrationRequest"]],
    building_id: int,
    hvac_unit_id: int,
) -> None:
    """Update existing sensors in-place (preserving IDs) and add new ones.

    Matching is done by sensor name within the device.  Sensors no longer
    present in the request are left untouched so that historical data is
    never orphaned.
    """
    if not sensors:
        return

    existing_by_name: dict = {
        s.name: s
        for s in db.query(Sensor).filter(Sensor.hvac_unit_id == hvac_unit_id).all()
    }

    for sensor_req in sensors:
        if sensor_req.name in existing_by_name:
            # In-place update — ID is preserved
            s = existing_by_name[sensor_req.name]
            canonical_unit, unit_id = canonicalize_unit(sensor_req.unit, db)
            s.sensor_type = sensor_req.sensor_type
            s.unit = canonical_unit
            s.unit_id = unit_id
            s.room_id = sensor_req.room_id
            # Only overwrite zone_id when explicitly provided — never clear an existing zone assignment
            if sensor_req.zone_id is not None:
                s.zone_id = sensor_req.zone_id
            s.thermostat_id = sensor_req.thermostat_id
            s.external_sensor_id = sensor_req.external_sensor_id
            s.payload_path = sensor_req.payload_path
            s.is_controllable = sensor_req.is_controllable
            s.command_payload_template = sensor_req.command_payload_template
            s.building_id = building_id
            s.hvac_unit_id = hvac_unit_id
            _sync_thermostat_for_sensor(db, s, building_id)
            print(f"{UPDATE_DEVICE_LOG_PREFIX} Updated sensor id={s.id} name={s.name}")
        else:
            # New sensor
            new_sensor = _build_sensor_for_device(building_id, hvac_unit_id, sensor_req, db)
            db.add(new_sensor)
            db.flush()
            # Safety net: if no zone was supplied, assign to the device's first linked zone
            # so the sensor always appears in the topology.
            if not new_sensor.zone_id:
                default_zone = (
                    db.query(HVACZone)
                    .join(ZoneHVACUnit, ZoneHVACUnit.zone_id == HVACZone.id)
                    .filter(ZoneHVACUnit.hvac_unit_id == hvac_unit_id)
                    .first()
                )
                if default_zone:
                    new_sensor.zone_id = default_zone.id
            _sync_thermostat_for_sensor(db, new_sensor, building_id)
            print(f"{UPDATE_DEVICE_LOG_PREFIX} Added new sensor name={sensor_req.name}")

def _create_device_zones(
    db: Session,
    building_id: int,
    hvac_unit: HVACUnit,
    zone_requests: Optional[List[ZoneRegistrationRequest]],
) -> dict[str, int]:
    """Create zones for the device and link them via zone_hvac_units.

    Returns a mapping of zone_name → zone_id so sensors can be assigned
    to their zone during the same registration call.
    If no zones are requested, one default zone is created automatically.
    """
    requests = zone_requests or [ZoneRegistrationRequest(name=f"{hvac_unit.name} Zone")]
    zone_name_to_id: dict[str, int] = {}

    for zone_req in requests:
        zone = HVACZone(
            building_id=building_id,
            name=zone_req.name,
            zone_type=zone_req.zone_type,
        )
        db.add(zone)
        db.flush()  # populate zone.id before linking

        link = ZoneHVACUnit(zone_id=zone.id, hvac_unit_id=hvac_unit.id)
        db.add(link)
        zone_name_to_id[zone_req.name] = zone.id

    return zone_name_to_id


# --- Response Models ---
class DeviceListResponse(BaseModel):
    id: int
    building_id: int
    building_name: str
    name: str
    unit_type: str
    device_key: str
    sensor_count: int = 0
    created_at: Optional[str] = None

class SensorResponse(BaseModel):
    id: int
    name: str
    sensor_type: str
    unit: Optional[str] = None
    room_id: Optional[int] = None
    zone_id: Optional[int] = None
    thermostat_id: Optional[int] = None
    payload_path: Optional[str] = None
    is_controllable: bool = False
    command_payload_template: Optional[str] = None

class SensorAddResponse(BaseModel):
    message: str
    sensors_added: int

# --- Request Models ---
class SensorRegistrationRequest(BaseModel):
    name: str
    sensor_type: str
    unit: Optional[str] = None
    room_id: Optional[int] = None
    room_name: Optional[str] = None  # resolved to room_id after rooms are created in same transaction
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    thermostat_id: Optional[int] = None
    external_sensor_id: Optional[str] = None
    payload_path: Optional[str] = None
    is_controllable: bool = False
    command_payload_template: Optional[str] = None

class RoomRegistrationRequest(BaseModel):
    name: str
    zone_name: Optional[str] = None  # links to a zone being created in this request


class DeviceRegistrationRequest(BaseModel):
    building_id: int
    name: str
    unit_type: str
    sensors: Optional[List[SensorRegistrationRequest]] = None
    zones: Optional[List[ZoneRegistrationRequest]] = None  # None = auto-create one zone
    rooms: Optional[List[RoomRegistrationRequest]] = None

class DeviceCredentialResponse(BaseModel):
    device_key: str
    device_secret: str

class DeviceCredentialUpsertRequest(BaseModel):
    name: Optional[str] = None
    unit_type: Optional[str] = None
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
                name=device.name,
                unit_type=device.unit_type,
                device_key=device_key,
                sensor_count=int(sensor_count),
                created_at=device.created_at.isoformat() if device.created_at else None
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
        403: {"description": UNAUTHORIZED_DESC},
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
                name=sensor.name,
                sensor_type=sensor.sensor_type,
                unit=sensor.unit,
                room_id=sensor.room_id,
                zone_id=sensor.zone_id,
                thermostat_id=sensor.thermostat_id,
                payload_path=sensor.payload_path,
                is_controllable=sensor.is_controllable,
                command_payload_template=sensor.command_payload_template,
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
        sensor = _build_sensor_for_device(hvac_unit.building_id, hvac_unit.id, s, db)
        db.add(sensor)
        db.flush()
        _sync_thermostat_for_sensor(db, sensor, hvac_unit.building_id)
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
        403: {"description": UNAUTHORIZED_DESC},
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
        name=req.name,
        unit_type=req.unit_type,
        device_key=device_key,
        device_secret_hash=device_secret_hash,
        device_secret_rotated_at=now,
        device_revoked_at=None
    )
    db.add(hvac_unit)
    db.flush()  # get hvac_unit.id before zone creation

    # Always create at least one zone and link it to the unit.
    # If the user supplied zone definitions, create them; otherwise auto-create one.
    zone_name_to_id = _create_device_zones(db, req.building_id, hvac_unit, req.zones)

    room_name_to_id: dict = {}
    if req.rooms:
        from models.topology import Room, ZoneRoom
        for room_req in req.rooms:
            room = Room(building_id=req.building_id, name=room_req.name.strip())
            db.add(room)
            db.flush()
            room_name_to_id[room_req.name.strip()] = room.id
            if room_req.zone_name:
                zone_id = zone_name_to_id.get(room_req.zone_name)
                if zone_id:
                    db.add(ZoneRoom(zone_id=zone_id, room_id=room.id))

    if req.sensors:
        for s in req.sensors:
            if not has_permission(user_id, "building", req.building_id, db):
                raise HTTPException(status_code=401, detail=UNAUTHORIZED_DESC)
            sensor = _build_sensor_for_device(req.building_id, hvac_unit.id, s, db, zone_name_to_id, room_name_to_id)
            db.add(sensor)
            db.flush()
            _sync_thermostat_for_sensor(db, sensor, req.building_id)

    db.commit()

    return DeviceCredentialResponse(device_key=device_key, device_secret=device_secret)

@router.put(
    "/{hvac_unit_id}",
    response_model=dict,
    responses={
        400: {"description": "Invalid input or validation error."},
        401: {"description": UNAUTHORIZED_DESC},
        403: {"description": UNAUTHORIZED_DESC},
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
        hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
        if not hvac_unit:
            raise HTTPException(status_code=404, detail=HVAC_UNIT_NOT_FOUND)
        if not has_permission(user_id, "device", hvac_unit_id, db):
            raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
        if not has_permission(user_id, "building", req.building_id, db):
            raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)

        _set_hvac_unit_fields(hvac_unit, req)
        _upsert_device_sensors(db, req.sensors, req.building_id, hvac_unit.id)

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
        403: {"description": UNAUTHORIZED_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def upsert_device_credentials(
    db: Annotated[Session, Depends(get_db)],
    hvac_unit_id: int,
    req: Optional[DeviceCredentialUpsertRequest] = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None,
):
    try:
        hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
        if not hvac_unit:
            raise HTTPException(status_code=404, detail=HVAC_UNIT_NOT_FOUND_DESC)

        original_hvac_unit_id = hvac_unit.id
        user_id = resolve_registered_user_id(user, db)
        if not has_permission(user_id, "device", hvac_unit.id, db):
            raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)

        device_secret = _rotate_hvac_unit_credentials(hvac_unit)

        # Revoke all active tokens for this device — secret rotation = immediate logout
        db.query(DeviceToken).filter(
            DeviceToken.hvac_unit_id == hvac_unit.id,
            DeviceToken.revoked_at.is_(None),
        ).update({DeviceToken.revoked_at: datetime.now(timezone.utc)}, synchronize_session=False)

        if req:
            if req.name is not None:
                hvac_unit.name = req.name
            if req.unit_type is not None:
                hvac_unit.unit_type = req.unit_type
            if req.sensors is not None:
                _upsert_device_sensors(db, req.sensors, hvac_unit.building_id, hvac_unit.id)

        db.flush()

        if hvac_unit.id != original_hvac_unit_id:
            raise RuntimeError(
                f"HVAC unit identity changed during credential rotation: "
                f"{original_hvac_unit_id} -> {hvac_unit.id}"
            )

        db.commit()
        db.refresh(hvac_unit)
        return DeviceCredentialResponse(device_key=hvac_unit.device_key, device_secret=device_secret)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"[upsert_device_credentials] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{hvac_unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": HVAC_UNIT_NOT_FOUND_DESC}, 403: {"description": UNAUTHORIZED_DESC}},
)
def delete_device(
    hvac_unit_id: int,
    db: DbSession,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))],
):
    """Delete an HVAC unit and all its sensors."""
    user_id = resolve_registered_user_id(user, db)
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not hvac_unit:
        raise HTTPException(status_code=404, detail=HVAC_UNIT_NOT_FOUND)
    if not has_permission(user_id, "building", hvac_unit.building_id, db):
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
    db.delete(hvac_unit)
    db.commit()


@router.delete(
    "/{hvac_unit_id}/sensors/{sensor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Sensor not found."}, 403: {"description": UNAUTHORIZED_DESC}},
)
def delete_sensor(
    hvac_unit_id: int,
    sensor_id: int,
    db: DbSession,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))],
):
    """Delete a single sensor from a device."""
    user_id = resolve_registered_user_id(user, db)
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not hvac_unit:
        raise HTTPException(status_code=404, detail=HVAC_UNIT_NOT_FOUND)
    if not has_permission(user_id, "building", hvac_unit.building_id, db):
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id, Sensor.hvac_unit_id == hvac_unit_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found.")
    db.delete(sensor)
    db.commit()


@router.delete(
    "/{hvac_unit_id}/tokens/{jti}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Token revoked."},
        404: {"description": "Token not found or already revoked."},
        403: {"description": UNAUTHORIZED_DESC},
    },
    summary="Revoke a specific device token by its jti"
)
def revoke_device_token(
    hvac_unit_id: int,
    jti: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None,
):
    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "device", hvac_unit_id, db):
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)
    token_row = db.query(DeviceToken).filter(
        DeviceToken.jti == jti,
        DeviceToken.hvac_unit_id == hvac_unit_id,
        DeviceToken.revoked_at.is_(None),
    ).first()
    if not token_row:
        raise HTTPException(status_code=404, detail="Token not found or already revoked.")
    token_row.revoked_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------------------
# Control signal (command) endpoint
# ---------------------------------------------------------------------------

class DeviceCommandRequest(BaseModel):
    command_type: str
    payload: dict


class DeviceCommandResponse(BaseModel):
    command_id: int
    status: str
    topic: str


@router.post(
    "/{hvac_unit_id}/command",
    response_model=DeviceCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Command accepted and published to device."},
        400: {"description": "Broker publish failed."},
        403: {"description": UNAUTHORIZED_DESC},
        404: {"description": DEVICE_NOT_FOUND_DESC},
    },
    summary="Send a control signal (command) to a device over MQTT",
)
def send_device_command(
    hvac_unit_id: int,
    body: DeviceCommandRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None,
):
    from services.mqtt_publisher import get_publisher

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "device", hvac_unit_id, db):
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)

    device = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND)

    topic = f"building/{device.building_id}/device/{device.device_key}/cmd"
    mqtt_payload = {
        "command_type": body.command_type,
        **body.payload,
    }

    cmd = DeviceCommand(
        hvac_unit_id=hvac_unit_id,
        building_id=device.building_id,
        command_type=body.command_type,
        payload=mqtt_payload,
        status="pending",
        topic=topic,
        issued_by_user_id=user_id,
    )
    db.add(cmd)
    db.flush()  # get cmd.id before publish

    published = get_publisher().publish(topic, mqtt_payload)
    cmd.status = "published" if published else "failed"
    db.commit()

    if not published:
        raise HTTPException(status_code=400, detail="MQTT broker publish failed.")

    return DeviceCommandResponse(
        command_id=cmd.id,
        status=cmd.status,
        topic=topic,
    )


# ---------------------------------------------------------------------------
# Device-side command polling  (REST — for edge / industrial without MQTT)
# Auth: device JWT  (same token issued by POST /device/auth)
# ---------------------------------------------------------------------------

class PendingCommandResponse(BaseModel):
    command_id: int
    command_type: str
    payload: dict
    issued_at: str
    topic: str


class CommandAckRequest(BaseModel):
    status: str = "acked"   # "acked" | "failed"


def _get_device_jwt(authorization: Annotated[str, Header()]) -> dict:
    """Validate device Bearer JWT and return its payload.
    Replicates the logic from sensordata.get_device_identity so that devices
    can use the same token for both data upload and command polling.
    """
    import jwt as _jwt
    import hashlib as _hashlib
    JWT_SECRET = os.environ.get("SESSION_SECRET_KEY")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]
    try:
        payload = _jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired device token") from exc
    if payload.get("typ") != "device":
        raise HTTPException(status_code=403, detail="Not a device token")
    return payload


def _resolve_device_from_jwt(
    device_jwt: Annotated[dict, Depends(_get_device_jwt)],
    db: Annotated[Session, Depends(get_db)],
) -> HVACUnit:
    """Look up the HVACUnit for the authenticated device JWT."""
    hvac_unit_id = int(device_jwt["sub"])
    device = db.query(HVACUnit).filter(HVACUnit.id == hvac_unit_id).first()
    if not device or device.device_revoked_at:
        raise HTTPException(status_code=403, detail="Device revoked or not found")
    return device


@router.get(
    "/me/commands/pending",
    response_model=List[PendingCommandResponse],
    responses={
        200: {"description": "Unacknowledged commands queued for this device."},
        401: {"description": "Missing or invalid device token."},
        403: {"description": "Device revoked or not found."},
    },
    summary="Poll pending commands (device JWT required)",
)
def get_pending_commands(
    db: Annotated[Session, Depends(get_db)],
    device: Annotated[HVACUnit, Depends(_resolve_device_from_jwt)],
):
    """
    Edge / industrial devices that cannot use MQTT call this endpoint to poll
    for commands that have been published but not yet acknowledged.
    Returns all commands with status 'published' (sent but no ACK received).
    """
    cmds = (
        db.query(DeviceCommand)
        .filter(
            DeviceCommand.hvac_unit_id == device.id,
            DeviceCommand.status == "published",
            DeviceCommand.acked_at.is_(None),
        )
        .order_by(DeviceCommand.issued_at.asc())
        .all()
    )
    return [
        PendingCommandResponse(
            command_id=c.id,
            command_type=c.command_type,
            payload=c.payload,
            issued_at=c.issued_at.isoformat(),
            topic=c.topic,
        )
        for c in cmds
    ]


@router.post(
    "/me/commands/{command_id}/ack",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Command acknowledged."},
        401: {"description": "Missing or invalid device token."},
        403: {"description": "Device revoked, not found, or command does not belong to device."},
        404: {"description": "Command not found."},
    },
    summary="Acknowledge a command (device JWT required)",
)
def ack_command(
    command_id: int,
    body: CommandAckRequest,
    db: Annotated[Session, Depends(get_db)],
    device: Annotated[HVACUnit, Depends(_resolve_device_from_jwt)],
):
    """
    Device calls this after executing (or failing to execute) a command received
    via GET /devices/me/commands/pending.  Sets acked_at and updates status.
    """
    cmd = (
        db.query(DeviceCommand)
        .filter(
            DeviceCommand.id == command_id,
            DeviceCommand.hvac_unit_id == device.id,
        )
        .first()
    )
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    if cmd.hvac_unit_id != device.id:
        raise HTTPException(status_code=403, detail=UNAUTHORIZED_DESC)

    cmd.acked_at = datetime.now(timezone.utc)
    cmd.status = body.status if body.status in ("acked", "failed") else "acked"
    db.commit()
    return {"command_id": cmd.id, "status": cmd.status, "acked_at": cmd.acked_at.isoformat()}
