from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.connection import get_db
from models.mqtt_config import MQTTBrokerConfig

from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
router = APIRouter(
    prefix="/mqtt",
    tags=["MQTT"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)

# String constants to avoid duplication (SonarQube S1192)
MQTT_CONFIG_NOT_FOUND = "MQTT configuration not found"
MQTT_CONFIG_NOT_FOUND_DESC = "MQTT configuration not found."
DEVICE_NOT_FOUND = "Device not found"
DEVICE_NOT_FOUND_DESC = "Device not found."
SENSOR_NOT_FOUND = "Sensor not found"
SENSOR_NOT_FOUND_DESC = "Sensor not found."
INVALID_INPUT_DESC = "Invalid input."
INTERNAL_SERVER_ERROR_DESC = "Internal server error."

# Log prefixes
LOG_GET_MQTT_CONFIG = "[get_mqtt_config]"
LOG_GET_DEVICE_MQTT_INFO = "[get_device_mqtt_info]"
LOG_GET_SENSOR_MQTT_INFO = "[get_sensor_mqtt_info]"
LOG_UPDATE_MQTT_CONFIG = "[update_mqtt_config]"

# String constants to avoid duplication (SonarQube S1192)
MQTT_CONFIG_NOT_FOUND = "MQTT configuration not found"
MQTT_CONFIG_NOT_FOUND_DESC = "MQTT configuration not found."
DEVICE_NOT_FOUND = "Device not found"
DEVICE_NOT_FOUND_DESC = "Device not found."
SENSOR_NOT_FOUND = "Sensor not found"
SENSOR_NOT_FOUND_DESC = "Sensor not found."
INVALID_INPUT_DESC = "Invalid input."
INTERNAL_SERVER_ERROR_DESC = "Internal server error."

# Log prefixes
LOG_GET_MQTT_CONFIG = "[get_mqtt_config]"
LOG_GET_DEVICE_MQTT_INFO = "[get_device_mqtt_info]"
LOG_GET_SENSOR_MQTT_INFO = "[get_sensor_mqtt_info]"
LOG_UPDATE_MQTT_CONFIG = "[update_mqtt_config]"

# Pydantic models
class MQTTConfigResponse(BaseModel):
    broker_url: str
    broker_port: int
    broker_username: Optional[str] = None
    broker_password: Optional[str] = None

    class Config:
        from_attributes = True

class MQTTConfigUpdate(BaseModel):
    broker_url: Optional[str] = None
    broker_port: Optional[int] = None
    broker_username: Optional[str] = None
    broker_password: Optional[str] = None
    use_tls: Optional[bool] = None
    client_id_prefix: Optional[str] = None
    topic_prefix: Optional[str] = None
    keepalive_seconds: Optional[int] = None

class DeviceMQTTInfo(BaseModel):
    device_id: int
    device_key: str
    publish_prefix: str
    subscribe_prefix: str
    client_id: str

class SensorMQTTInfo(BaseModel):
    sensor_id: int
    device_id: int
    publish_topic: str
    payload_path: Optional[str] = None

@router.get(
    "/config",
    response_model=MQTTConfigResponse,
    responses={
        404: {"description": MQTT_CONFIG_NOT_FOUND_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def get_mqtt_config(db: Annotated[Session, Depends(get_db)]):
    """Get active MQTT broker configuration"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    try:
        # Return only main config from environment variables
        return MQTTConfigResponse(
            broker_url=os.environ.get("MQTT_HOST", "localhost"),
            broker_port=int(os.environ.get("MQTT_PORT", 1883)),
            broker_username=os.environ.get("MQTT_USER"),
            broker_password=os.environ.get("MQTT_PASS"),
        )
    except Exception as e:
        print(f"{LOG_GET_MQTT_CONFIG} Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/device/{device_id}/info",
    response_model=DeviceMQTTInfo,
    responses={
        403: {"description": "Forbidden: User not authorized to access this device's MQTT info."},
        404: {"description": DEVICE_NOT_FOUND_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def get_device_mqtt_info(
    device_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Get MQTT publishing information for a specific device (with permission check)"""
    from utils.policies import has_permission
    try:
        # Get MQTT config
        config = db.query(MQTTBrokerConfig).filter(MQTTBrokerConfig.is_active == True).first()
        if not config:
            raise HTTPException(status_code=404, detail=MQTT_CONFIG_NOT_FOUND)
        # Get device info
        from models.hvac_unit import HVACUnit
        device = db.query(HVACUnit).filter(HVACUnit.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail=DEVICE_NOT_FOUND)
        user_id = resolve_registered_user_id(user, db)
        if user_id is None or not has_permission(user_id, "device", device.id, db):
            raise HTTPException(status_code=403, detail="You are not authorized to access this device's MQTT info.")
        return DeviceMQTTInfo(
            device_id=device.id,
            device_key=device.device_key,
            publish_prefix=f"{config.topic_prefix}/devices/{device.id}",
            subscribe_prefix=f"{config.topic_prefix}/commands/{device.id}",
            client_id=f"{config.client_id_prefix}_{device.id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"{LOG_GET_DEVICE_MQTT_INFO} Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/sensor/{sensor_id}/info",
    response_model=SensorMQTTInfo,
    responses={
        403: {"description": "Forbidden: User not authorized to access this sensor's MQTT info."},
        404: {"description": SENSOR_NOT_FOUND_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def get_sensor_mqtt_info(
    sensor_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Get MQTT publishing information for a specific sensor (with permission check)"""
    from utils.policies import has_permission
    try:
        # Get sensor info
        from models.sensor import Sensor
        sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
        if not sensor:
            raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND)
        user_id = resolve_registered_user_id(user, db)
        if user_id is None or not has_permission(user_id, "sensor", sensor.id, db):
            raise HTTPException(status_code=403, detail="You are not authorized to access this sensor's MQTT info.")
        # Get MQTT config
        config = db.query(MQTTBrokerConfig).filter(MQTTBrokerConfig.is_active == True).first()
        if not config:
            raise HTTPException(status_code=404, detail=MQTT_CONFIG_NOT_FOUND)
        return SensorMQTTInfo(
            sensor_id=sensor.id,
            device_id=sensor.hvac_unit_id,
            publish_topic=f"{config.topic_prefix}/devices/{sensor.hvac_unit_id}/sensors/{sensor.id}",
            payload_path=sensor.payload_path
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"{LOG_GET_SENSOR_MQTT_INFO} Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/config",
    response_model=MQTTConfigResponse,
    dependencies=[Depends(get_current_user_role(["ADMIN"]))],
    responses={
        400: {"description": INVALID_INPUT_DESC},
        404: {"description": MQTT_CONFIG_NOT_FOUND_DESC},
        500: {"description": INTERNAL_SERVER_ERROR_DESC}
    },
)
def update_mqtt_config(
    updates: MQTTConfigUpdate,
    db: Annotated[Session, Depends(get_db)]
):
    """Update MQTT broker configuration (ADMIN only)"""
    try:
        config = db.query(MQTTBrokerConfig).filter(MQTTBrokerConfig.is_active == True).first()
        if not config:
            raise HTTPException(status_code=404, detail=MQTT_CONFIG_NOT_FOUND)
        
        # Update only provided fields
        update_data = updates.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        
        db.commit()
        db.refresh(config)
        
        return config
    except HTTPException:
        raise
    except Exception as e:
        print(f"{LOG_UPDATE_MQTT_CONFIG} Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
