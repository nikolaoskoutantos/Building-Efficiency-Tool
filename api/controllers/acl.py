from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from db import SessionLocal
from models.hvac_unit import HVACUnit
from models.sensor import Sensor  # <-- adjust import path to your project
import logging

router = APIRouter(tags=["Device & User Authentication"])
logger = logging.getLogger("uvicorn.error")

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

def parse_and_validate_topic(topic, building_id, device_key):
    parts = topic.split("/")
    if len(parts) < 4:
        return None, None, "topic_too_short"
    if parts[0] != "building" or parts[2] != "device":
        return None, None, "invalid_root"
    try:
        topic_building_id = int(parts[1])
    except Exception:
        return None, None, "invalid_building_id"
    topic_device_key = parts[3]
    if topic_building_id != int(building_id):
        return None, None, "building_mismatch"
    if topic_device_key != device_key:
        return None, None, "device_key_mismatch"
    resource = parts[4] if len(parts) > 4 else ""
    return parts, resource, None

def check_action_policy(action, resource):
    if action not in ("publish", "subscribe"):
        return False, "invalid_action"
    if action == "publish" and resource not in ("status", "sensor"):
        return False, "publish_not_allowed_for_resource"
    if action == "subscribe" and resource not in ("cmd", "config"):
        return False, "subscribe_not_allowed_for_resource"
    return True, None

def check_sensor_ownership(db, parts, hvac_unit_id):
    if len(parts) < 6:
        return False, "sensor_topic_too_short"
    sensor_id_str = parts[5]
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


@router.post("/device/acl")
async def device_acl(body: EMQXACLRequest):
    username = (body.username or "").strip()
    action   = (body.action or "").strip().lower()
    topic    = (body.topic or "").strip().lstrip("/")

    db = SessionLocal()
    try:
        logger.info(f"ACL HIT username={username!r} action={action!r} topic={topic!r}")
        device = db.query(HVACUnit).filter(HVACUnit.device_key == username).first()
        if not device:
            return deny("device_not_found")
        building_id = getattr(device, "building_id", None)
        device_key  = (getattr(device, "device_key", None) or "").strip()
        hvac_unit_id = getattr(device, "id", None)
        if building_id is None or device_key == "" or hvac_unit_id is None:
            return deny("missing_device_fields")

        parts, resource, topic_error = parse_and_validate_topic(topic, building_id, device_key)
        if topic_error:
            return deny(topic_error)

        ok, action_error = check_action_policy(action, resource)
        if not ok:
            return deny(action_error)

        if resource == "sensor":
            ok, sensor_error = check_sensor_ownership(db, parts, hvac_unit_id)
            if not ok:
                return deny(sensor_error)
            return allow()

        return allow()
    except Exception:
        logger.exception("ACL error")
        return JSONResponse({"result": "deny"})
    finally:
        db.close()