from fastapi import APIRouter, Depends, HTTPException, Header, Request
from typing import Annotated
import jwt
import hashlib
import logging
from models.sensor import Sensor
from models.hvac_unit import HVACUnit
from models.device_token import DeviceToken
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensordata import SensorData, SensorDataRaw
from typing import List, Optional
from pydantic import BaseModel, model_validator
from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.policies import has_permission
from utils.rate_limit import RateLimiter

logger = logging.getLogger("sensordata")

# Separate, more permissive rate limiter for device ingestion
# (devices may push frequently; keyed on device JWT sub, not IP)
_DEVICE_INGEST_MAX = int(os.environ.get("DEVICE_INGEST_RATE_MAX", "120"))   # requests
_DEVICE_INGEST_WINDOW = int(os.environ.get("DEVICE_INGEST_RATE_WINDOW", "60"))  # seconds
device_ingest_limiter = RateLimiter(max_requests=_DEVICE_INGEST_MAX, window_seconds=_DEVICE_INGEST_WINDOW)

# Timestamp acceptance window (env-configurable, defaults: 24 h past, 5 min future)
_TS_MAX_PAST_HOURS = float(os.environ.get("SENSOR_TS_MAX_PAST_HOURS", "24"))
_TS_MAX_FUTURE_MIN = float(os.environ.get("SENSOR_TS_MAX_FUTURE_MIN", "5"))

router = APIRouter(prefix="/sensordata", tags=["SensorData"])

MAX_BULK_RECORDS = int(os.environ.get("SENSOR_BULK_MAX_RECORDS", "1000"))


# Pydantic schemas
class SensorDataCreate(BaseModel):
    sensor_id: int
    building_id: int
    ts: Optional[datetime] = None
    value: Optional[float] = None           # numeric (temperature, power, CO2, ...)
    value_text: Optional[str] = None        # text    (hvac_status, mode, ...)
    value_bool: Optional[bool] = None       # boolean (occupancy, on/off, ...)
    quality: Optional[str] = "valid"

    @model_validator(mode="after")
    def validate_fields(self) -> "SensorDataCreate":
        if self.value is None and self.value_text is None and self.value_bool is None:
            raise ValueError("At least one of value, value_text, or value_bool must be provided")
        if self.ts is not None:
            now = datetime.now(timezone.utc)
            ts = self.ts if self.ts.tzinfo else self.ts.replace(tzinfo=timezone.utc)
            if ts < now - timedelta(hours=_TS_MAX_PAST_HOURS):
                raise ValueError(f"Timestamp is too far in the past (max {_TS_MAX_PAST_HOURS}h)")
            if ts > now + timedelta(minutes=_TS_MAX_FUTURE_MIN):
                raise ValueError(f"Timestamp is too far in the future (max {_TS_MAX_FUTURE_MIN}min)")
        return self

class SensorDataRead(BaseModel):
    id: int
    sensor_id: int
    building_id: int
    ts: Optional[datetime] = None
    value: Optional[float] = None
    value_text: Optional[str] = None
    value_bool: Optional[bool] = None
    quality: Optional[str] = "valid"

    class Config:
        from_attributes = True

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

def sensor_data_payload(data: SensorDataCreate) -> dict:
    d = data.model_dump(exclude_none=True)
    if "ts" not in d or d["ts"] is None:
        d["ts"] = datetime.now(timezone.utc)
    return d


RAW_FIELDS = {"sensor_id", "building_id", "ts", "value", "value_text", "value_bool", "payload"}


def sensor_raw_payload(data: SensorDataCreate) -> dict:
    """Subset of sensor_data_payload that only contains SensorDataRaw columns."""
    return {k: v for k, v in sensor_data_payload(data).items() if k in RAW_FIELDS}

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
        logger.warning("device_auth_failed reason=missing_header")
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as exc:
        logger.warning("device_auth_failed reason=jwt_decode_error detail=%s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired device token")
    if payload.get("typ") != "device":
        logger.warning("device_auth_failed reason=wrong_token_type sub=%s", payload.get("sub"))
        raise HTTPException(status_code=403, detail="Not a device token")
    jti = payload.get("jti")
    if not jti:
        logger.warning("device_auth_failed reason=missing_jti sub=%s", payload.get("sub"))
        raise HTTPException(status_code=401, detail="Token missing jti claim")
    device_token_row = db.query(DeviceToken).filter(
        DeviceToken.jti == jti,
        DeviceToken.revoked_at.is_(None),
    ).first()
    if not device_token_row:
        logger.warning("device_auth_failed reason=jti_not_found_or_revoked jti=%s", jti)
        raise HTTPException(status_code=401, detail="Token has been revoked or is not recognised")
    hvac_unit = db.query(HVACUnit).filter(HVACUnit.id == device_token_row.hvac_unit_id).first()
    if not hvac_unit or hvac_unit.device_revoked_at:
        logger.warning("device_auth_failed reason=device_revoked hvac_unit_id=%s", device_token_row.hvac_unit_id)
        raise HTTPException(status_code=403, detail="Device revoked or not found")
    if not hvac_unit.device_secret_hash:
        logger.warning("device_auth_failed reason=no_credentials hvac_unit_id=%s", hvac_unit.id)
        raise HTTPException(status_code=403, detail="Device has no credentials")
    expected_cfp = hashlib.sha256(hvac_unit.device_secret_hash.encode()).hexdigest()[:16]
    if payload.get("cfp") != expected_cfp:
        logger.warning("device_auth_failed reason=cfp_mismatch hvac_unit_id=%s", hvac_unit.id)
        raise HTTPException(status_code=401, detail="Device credentials have been rotated — please re-authenticate")
    return payload

@router.post(
    "/",
    response_model=SensorDataRead,
    responses={
        404: {"description": "Sensor not found"},
        401: {"description": "Unauthorized: Missing/invalid/expired device token"},
        403: {"description": "Forbidden: Device not authorized to write to this sensor, or device revoked"},
        429: {"description": "Device ingestion rate limit exceeded"},
        500: {"description": "Internal server error"}
    },
)
def create_sensor_data(
    data: SensorDataCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    device_jwt: Annotated[dict, Depends(get_device_identity)]
):
    device_id = int(device_jwt["sub"])
    if not device_ingest_limiter.is_allowed(str(device_id)):
        raise HTTPException(status_code=429, detail="Device ingestion rate limit exceeded")
    validate_device_sensor_ids(db, [data.sensor_id], device_id)
    payload = sensor_data_payload(data)
    raw_row = SensorDataRaw(**sensor_raw_payload(data))
    db.add(raw_row)
    db.commit()
    db.refresh(raw_row)
    return {**payload, "id": raw_row.id}

@router.post(
    "/bulk",
    response_model=List[SensorDataRead],
    responses={
        400: {"description": "Empty payload"},
        401: {"description": "Unauthorized: Missing/invalid/expired device token"},
        403: {"description": "Forbidden: Device not authorized to write to one or more sensors, or device revoked"},
        429: {"description": "Device ingestion rate limit exceeded"},
        500: {"description": "Internal server error"}
    },
)
def create_sensor_data_bulk(
    data: List[SensorDataCreate],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    device_jwt: Annotated[dict, Depends(get_device_identity)]
):
    device_id = int(device_jwt["sub"])
    if not device_ingest_limiter.is_allowed(str(device_id)):
        raise HTTPException(status_code=429, detail="Device ingestion rate limit exceeded")
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
        device_id
    )

    raw_rows = [SensorDataRaw(**sensor_raw_payload(item)) for item in data]
    db.add_all(raw_rows)
    db.commit()
    for row in raw_rows:
        db.refresh(row)
    return [{**sensor_data_payload(item), "id": raw_row.id} for item, raw_row in zip(data, raw_rows)]

@router.get("/", response_model=List[SensorDataRead])
def read_sensor_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))],
    sensor_id: Optional[int] = None,
    ts_from: Optional[datetime] = None,
    ts_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
):
    user_id = resolve_registered_user_id(user, db)
    q = db.query(SensorData)
    if sensor_id is not None:
        q = q.filter(SensorData.sensor_id == sensor_id)
    if ts_from is not None:
        q = q.filter(SensorData.ts >= ts_from)
    if ts_to is not None:
        q = q.filter(SensorData.ts <= ts_to)
    sensor_data_rows = q.order_by(SensorData.ts.desc()).offset(skip).limit(limit).all()
    return [row for row in sensor_data_rows if has_permission(user_id, "sensor", row.sensor_id, db)]


@router.get(
    "/me",
    response_model=List[SensorDataRead],
    responses={
        401: {"description": "Missing or invalid device token"},
        403: {"description": "Device revoked or not found"},
    },
    summary="Read own sensor data (device JWT)",
)
def read_own_sensor_data(
    db: Annotated[Session, Depends(get_db)],
    device_jwt: Annotated[dict, Depends(get_device_identity)],
    sensor_id: Optional[int] = None,
    ts_from: Optional[datetime] = None,
    ts_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
):
    """Device reads its own aggregated sensor data — no user JWT needed."""
    device_id = int(device_jwt["sub"])
    # Collect sensor IDs that belong to this device
    device_sensor_ids = [
        s.id for s in db.query(Sensor).filter(Sensor.hvac_unit_id == device_id).all()
    ]
    if not device_sensor_ids:
        return []
    q = db.query(SensorData).filter(SensorData.sensor_id.in_(device_sensor_ids))
    if sensor_id is not None:
        if sensor_id not in device_sensor_ids:
            raise HTTPException(status_code=403, detail="Sensor does not belong to this device")
        q = q.filter(SensorData.sensor_id == sensor_id)
    if ts_from is not None:
        q = q.filter(SensorData.ts >= ts_from)
    if ts_to is not None:
        q = q.filter(SensorData.ts <= ts_to)
    return q.order_by(SensorData.ts.desc()).offset(skip).limit(limit).all()

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
