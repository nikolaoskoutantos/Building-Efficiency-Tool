from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, Optional, List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.connection import get_db
from models.hvac_models import Building
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from models.mqtt_config import MQTTBrokerConfig
import os

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Pydantic response models
class DashboardDevice(BaseModel):
    id: int
    building_id: int
    building_name: str
    central_unit: Optional[str] = None
    zone: Optional[str] = None
    room: Optional[str] = None
    device_key: str
    sensor_count: int = 0
    created_at: Optional[str] = None

class DashboardBuilding(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    lat: Optional[str] = None
    lon: Optional[str] = None

class DashboardMQTTConfig(BaseModel):
    broker_url: str
    broker_port: int
    broker_username: Optional[str] = None
    broker_password: Optional[str] = None

class DashboardUserSettings(BaseModel):
    default_building_id: Optional[int] = None
    theme: Optional[str] = None
    notifications_enabled: bool = True
    auto_refresh_devices: bool = True

class DashboardResponse(BaseModel):
    devices: List[DashboardDevice]
    buildings: List[DashboardBuilding]
    mqtt_config: DashboardMQTTConfig
    user_settings: DashboardUserSettings
    stats: Dict[str, Any]

@router.get("/", 
    response_model=DashboardResponse,
    responses={
        500: {"description": "Internal server error."}
    }
)
async def get_dashboard_data(db: Annotated[Session, Depends(get_db)]):
    """
    Unified dashboard endpoint that loads all necessary data in a single optimized query.
    Returns devices, buildings, MQTT config, user settings, and statistics.
    """
    try:
        # 1. Load buildings
        buildings = db.query(Building).all()
        buildings_data = [
            DashboardBuilding(
                id=building.id,
                name=building.name,
                address=building.address,
                lat=building.lat,
                lon=building.lon
            )
            for building in buildings
        ]

        # 2. Load devices with sensor counts in a single optimized query
        devices_query = db.query(
            HVACUnit.id,
            HVACUnit.building_id,
            Building.name.label('building_name'),
            HVACUnit.central_unit,
            HVACUnit.zone,
            HVACUnit.room,
            HVACUnit.device_key,
            HVACUnit.created_at,
            func.count(Sensor.id).label('sensor_count')
        ).join(
            Building, HVACUnit.building_id == Building.id
        ).outerjoin(
            Sensor, Sensor.hvac_unit_id == HVACUnit.id
        ).filter(
            HVACUnit.device_key.isnot(None)  # Only include devices with keys
        ).group_by(
            HVACUnit.id,
            HVACUnit.building_id,
            Building.name,
            HVACUnit.central_unit,
            HVACUnit.zone,
            HVACUnit.room,
            HVACUnit.device_key,
            HVACUnit.created_at
        ).all()

        devices_data = [
            DashboardDevice(
                id=device.id,
                building_id=device.building_id,
                building_name=device.building_name,
                central_unit=device.central_unit,
                zone=device.zone,
                room=device.room,
                device_key=device.device_key,
                sensor_count=device.sensor_count,
                created_at=device.created_at.isoformat() if device.created_at else None
            )
            for device in devices_query
        ]

        # 3. Load MQTT configuration - try from DB first, then .env fallback
        mqtt_config_db = db.query(MQTTBrokerConfig).first()
        
        if mqtt_config_db:
            mqtt_config = DashboardMQTTConfig(
                broker_url=mqtt_config_db.broker_url,
                broker_port=mqtt_config_db.broker_port,
                broker_username=mqtt_config_db.broker_username,
                broker_password=mqtt_config_db.broker_password
            )
        else:
            # Fallback to environment variables
            mqtt_config = DashboardMQTTConfig(
                broker_url=os.getenv("MQTT_HOST", "localhost"),
                broker_port=int(os.getenv("MQTT_PORT", "1883")),
                broker_username=os.getenv("MQTT_USER"),
                broker_password=os.getenv("MQTT_PASS")
            )

        # 4. Load user settings (assuming there's a current user context)
        # For now, return default settings - can be extended with user authentication
        user_settings = DashboardUserSettings(
            default_building_id=buildings_data[0].id if buildings_data else None,
            theme="light",
            notifications_enabled=True,
            auto_refresh_devices=True
        )

        # 5. Calculate dashboard statistics
        total_devices = len(devices_data)
        total_sensors = sum(device.sensor_count for device in devices_data)
        total_buildings = len(buildings_data)
        
        stats = {
            "total_devices": total_devices,
            "total_sensors": total_sensors,
            "total_buildings": total_buildings,
            "devices_with_sensors": len([d for d in devices_data if d.sensor_count > 0]),
            "average_sensors_per_device": round(total_sensors / total_devices, 1) if total_devices > 0 else 0
        }

        return DashboardResponse(
            devices=devices_data,
            buildings=buildings_data,
            mqtt_config=mqtt_config,
            user_settings=user_settings,
            stats=stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard data: {str(e)}")

@router.get("/stats",
    responses={
        500: {"description": "Internal server error."}
    }
)
async def get_dashboard_stats(db: Annotated[Session, Depends(get_db)]):
    """
    Quick endpoint for just dashboard statistics (for real-time updates)
    """
    try:
        # Count queries
        total_devices = db.query(HVACUnit).filter(HVACUnit.device_key.isnot(None)).count()
        total_sensors = db.query(Sensor).count()
        total_buildings = db.query(Building).count()
        
        # Devices with sensors
        devices_with_sensors = db.query(HVACUnit).join(Sensor).distinct().count()

        return {
            "total_devices": total_devices,
            "total_sensors": total_sensors,
            "total_buildings": total_buildings,
            "devices_with_sensors": devices_with_sensors,
            "average_sensors_per_device": round(total_sensors / total_devices, 1) if total_devices > 0 else 0,
            "last_updated": "now"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard stats: {str(e)}")