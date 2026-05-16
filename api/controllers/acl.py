from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session
from db import SessionLocal
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
import logging
import os

router = APIRouter(tags=["Device & User Authentication"])
logger = logging.getLogger("uvicorn.error")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class EMQXACLRequest(BaseModel):
    username: str
    clientid: str
    action: str   # "publish" | "subscribe"
    topic: str


def deny(reason: str):
    logger.info(f"DENY reason={reason}")
    return JSONResponse({"result": "deny"})

def allow():
    logger.info("ALLOW")
    return JSONResponse({"result": "allow"})

def parse_and_validate_topic(topic, device_key):
    """Validate topic format: {device_key}/{resource}"""
    parts = topic.split("/")
    if len(parts) < 2:
        return None, None, "topic_too_short"
    if parts[0] != device_key:
        return None, None, "device_key_mismatch"
    resource = parts[1]
    return parts, resource, None

def check_action_policy(action, resource):
    if action not in ("publish", "subscribe"):
        return False, "invalid_action"
    # Device-level resources
    device_publish = ("status", "sensor")
    device_subscribe = ("cmd", "config")
    # Sensor-level resources
    sensor_publish = ("status", "sensor")
    sensor_subscribe = ("cmd", "config")
    if action == "publish" and resource in device_publish:
        return True, None
    if action == "subscribe" and resource in device_subscribe:
        return True, None
    if action == "publish" and resource in sensor_publish:
        return True, None
    if action == "subscribe" and resource in sensor_subscribe:
        return True, None
    # Allow direct sensor publish: {device_key}/{sensor_id} where sensor_id is an integer
    if action == "publish" and resource.isdigit():
        return True, None
    return False, "not_allowed_for_resource"

def check_sensor_ownership(db, parts, hvac_unit_id):
    if len(parts) < 2:
        return False, "sensor_topic_too_short"
    sensor_id_str = parts[1]
    try:
        sensor_id = int(sensor_id_str)
    except Exception:
        return False, "invalid_sensor_id"
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        return False, "sensor_not_found"
    sensor_hvac_unit_id = getattr(sensor, "hvac_unit_id", None)
    if sensor_hvac_unit_id != hvac_unit_id:
        return False, "sensor_not_owned_by_device"
    return True, None


def check_backend_service_acl(username, action, topic):
    service_user = os.environ.get("MQTT_SERVICE_USER", "")
    if not service_user or username != service_user:
        return False, None

    parts = topic.split("/")
    resource = parts[1] if len(parts) >= 2 else ""
    # Backend service: may subscribe to anything, publish only cmd/config
    if action == "subscribe":
        return True, None
    if action == "publish" and resource in ("cmd", "config"):
        return True, None
    return True, "backend_service_topic_not_permitted"


def get_device_context(db, username):
    device = db.query(HVACUnit).filter(HVACUnit.device_key == username).first()
    if not device:
        return None, "device_not_found"

    building_id = getattr(device, "building_id", None)
    device_key = (getattr(device, "device_key", None) or "").strip()
    hvac_unit_id = getattr(device, "id", None)
    if building_id is None or device_key == "" or hvac_unit_id is None:
        return None, "missing_device_fields"

    return {
        "building_id": building_id,
        "device_key": device_key,
        "hvac_unit_id": hvac_unit_id,
    }, None


@router.post("/device/acl")
def device_acl(body: EMQXACLRequest, db: Annotated[Session, Depends(get_db)]):
    username = (body.username or "").strip()
    action   = (body.action or "").strip().lower()
    topic    = (body.topic or "").strip().lstrip("/")

    try:
        logger.info(f"ACL HIT username={username!r} action={action!r} topic={topic!r}")

        is_backend_user, backend_error = check_backend_service_acl(username, action, topic)
        if is_backend_user:
            if backend_error:
                return deny(backend_error)
            return allow()

        device_context, device_error = get_device_context(db, username)
        if device_error:
            return deny(device_error)

        parts, resource, topic_error = parse_and_validate_topic(
            topic,
            device_context["device_key"],
        )
        if topic_error:
            return deny(topic_error)

        ok, action_error = check_action_policy(action, resource)
        if not ok:
            return deny(action_error)

        if resource.isdigit():
            owns_sensor, sensor_error = check_sensor_ownership(
                db,
                parts,
                device_context["hvac_unit_id"],
            )
            if not owns_sensor:
                return deny(sensor_error)

        return allow()
    except Exception:
        logger.exception("ACL error")
        return JSONResponse({"result": "deny"})
