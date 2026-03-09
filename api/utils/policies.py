from sqlalchemy.orm import Session
from models.hvac_models import UserBuilding
from models.hvac_unit import HVACUnit
from models.sensor import Sensor


def has_permission(user_id: int, resource_type: str, resource_id: int, db: Session) -> bool:
    """
    Checks if the user has permission to access the given resource (device/sensor/building).
    Uses a single JOIN query instead of two sequential queries.
    Returns True if allowed, False otherwise.
    """
    if resource_type == "building":
        return (
            db.query(UserBuilding)
            .filter_by(user_id=user_id, building_id=resource_id, status="active")
            .first() is not None
        )

    elif resource_type == "device":
        return (
            db.query(UserBuilding)
            .join(HVACUnit, HVACUnit.building_id == UserBuilding.building_id)
            .filter(
                HVACUnit.id == resource_id,
                UserBuilding.user_id == user_id,
                UserBuilding.status == "active",
            )
            .first() is not None
        )

    elif resource_type == "sensor":
        return (
            db.query(UserBuilding)
            .join(Sensor, Sensor.building_id == UserBuilding.building_id)
            .filter(
                Sensor.id == resource_id,
                UserBuilding.user_id == user_id,
                UserBuilding.status == "active",
            )
            .first() is not None
        )

    return False