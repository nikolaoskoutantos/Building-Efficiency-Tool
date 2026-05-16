BUILDING_NOT_FOUND = "Building not found"
BUILDING_DELETED = "Building deleted"
USER_ID_MISSING = "User ID missing in token."
FORBIDDEN_BUILDING = "You are not authorized to access this building."
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import SessionLocal
from models.hvac_models import Building, UserBuilding

from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
router = APIRouter(
    prefix="/buildings",
    tags=["Buildings"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)

class BuildingCreate(BaseModel):
    name: str
    address: Optional[str] = None
    lat: Optional[str] = None
    lon: Optional[str] = None

class BuildingRead(BuildingCreate):
    id: int
    status: Optional[str] = None
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/",
    response_model=List[BuildingRead],
    responses={404: {"description": "No buildings found"}}
)
def get_buildings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))],
    include_pending: bool = False,
):
    user_id = resolve_registered_user_id(user, db)
    mappings = db.query(UserBuilding).filter(UserBuilding.user_id == user_id)
    if not include_pending:
        mappings = mappings.filter(UserBuilding.status == "active")

    mapping_rows = mappings.all()
    if not mapping_rows:
        return []

    status_by_building_id = {row.building_id: row.status for row in mapping_rows}
    allowed_building_ids = list(status_by_building_id.keys())
    buildings = db.query(Building).filter(Building.id.in_(allowed_building_ids)).all()

    return [
        BuildingRead(
            id=building.id,
            name=building.name,
            address=building.address,
            lat=building.lat,
            lon=building.lon,
            status=status_by_building_id.get(building.id),
        )
        for building in buildings
    ]

@router.post(
    "/",
    response_model=BuildingRead,
    responses={
        404: {"description": "Building not found"},
        403: {"description": "Forbidden: User not authorized or missing user ID in token"}
    }
)
def create_building(
    building: BuildingCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    user_id = resolve_registered_user_id(user, db)
    db_building = Building(**building.dict())
    db.add(db_building)
    db.commit()
    db.refresh(db_building)

    creator_role = str(user.get("role", "BUILDING_MANAGER")).lower()
    db.add(UserBuilding(
        user_id=user_id,
        building_id=db_building.id,
        role=creator_role,
        status="pending",
    ))
    db.commit()

    return db_building

@router.get(
    "/{building_id}",
    response_model=BuildingRead,
    responses={
        404: {"description": "Building not found"},
        403: {"description": "Forbidden: User not authorized or missing user ID in token"}
    }
)
def get_building(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    user_id = resolve_registered_user_id(user, db)
    from utils.policies import has_permission
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING)
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)
    return building

@router.put(
    "/{building_id}",
    response_model=BuildingRead,
    responses={
        404: {"description": "Building not found"},
        403: {"description": "Forbidden: User not authorized or missing user ID in token"}
    }
)
def update_building(
    building_id: int,
    building: BuildingCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    user_id = resolve_registered_user_id(user, db)
    from utils.policies import has_permission
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to modify this building.")
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)
    db_building.name = building.name
    db_building.address = building.address
    db_building.lat = building.lat
    db_building.lon = building.lon
    db.commit()
    db.refresh(db_building)
    return db_building

@router.delete(
    "/{building_id}",
    responses={
        200: {"description": "Building deleted"},
        404: {"description": "Building not found"},
        403: {"description": "Forbidden: User not authorized or missing user ID in token"}
    }
)
def delete_building(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    user_id = resolve_registered_user_id(user, db)
    from utils.policies import has_permission
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to delete this building.")
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)
    db.delete(db_building)
    db.commit()
    return {"detail": BUILDING_DELETED}


# --- Topology ---

class TopologyRoom(BaseModel):
    id: int
    name: str
    zone_id: Optional[int] = None

class RoomCreate(BaseModel):
    name: str
    zone_id: Optional[int] = None

class RoomRead(TopologyRoom):
    pass

class TopologyZone(BaseModel):
    id: int
    name: str

class TopologyThermostat(BaseModel):
    id: int
    name: str
    is_controllable: bool = False

class BuildingTopologyResponse(BaseModel):
    rooms: List[TopologyRoom]
    zones: List[TopologyZone]
    thermostats: List[TopologyThermostat]

class TopologyDeleteResponse(BaseModel):
    detail: str

@router.post(
    "/{building_id}/rooms",
    response_model=RoomRead,
    responses={
        403: {"description": "Forbidden"},
        404: {"description": "Building not found"},
        409: {"description": "Room already exists"},
    }
)
def create_building_room(
    building_id: int,
    payload: RoomCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    from utils.policies import has_permission
    from models.topology import Room

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to modify this building.")

    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)

    room_name = (payload.name or "").strip()
    if not room_name:
        raise HTTPException(status_code=400, detail="Room name is required.")

    existing = db.query(Room).filter(Room.building_id == building_id, Room.name == room_name).first()
    if existing:
        raise HTTPException(status_code=409, detail="A room with this name already exists.")

    room = Room(building_id=building_id, name=room_name)
    db.add(room)
    db.flush()

    if payload.zone_id:
        from models.topology import ZoneRoom, HVACZone
        zone = db.query(HVACZone).filter(HVACZone.id == payload.zone_id, HVACZone.building_id == building_id).first()
        if zone:
            db.add(ZoneRoom(zone_id=zone.id, room_id=room.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A room with this name already exists.")

    db.refresh(room)
    return RoomRead(id=room.id, name=room.name)

@router.delete(
    "/{building_id}/rooms/{room_id}",
    response_model=TopologyDeleteResponse,
    responses={
        403: {"description": "Forbidden"},
        404: {"description": "Room not found"},
        409: {"description": "Room still in use"},
    }
)
def delete_building_room(
    building_id: int,
    room_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    from utils.policies import has_permission
    from models.topology import Room, ZoneRoom
    from models.sensor import Sensor

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to modify this building.")

    room = db.query(Room).filter(Room.id == room_id, Room.building_id == building_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")

    assigned_sensor_count = db.query(Sensor).filter(Sensor.room_id == room_id).count()
    if assigned_sensor_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete room while sensors are still assigned to it. Unassign the sensors first.",
        )

    linked_zone_count = db.query(ZoneRoom).filter(ZoneRoom.room_id == room_id).count()
    if linked_zone_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete room while it is still linked to one or more zones. Remove the zone-room links first.",
        )

    db.delete(room)
    db.commit()
    return TopologyDeleteResponse(detail="Room deleted.")

@router.delete(
    "/{building_id}/zones/{zone_id}",
    response_model=TopologyDeleteResponse,
    responses={
        403: {"description": "Forbidden"},
        404: {"description": "Zone not found"},
        409: {"description": "Zone still in use"},
    }
)
def delete_building_zone(
    building_id: int,
    zone_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
):
    from utils.policies import has_permission
    from models.topology import HVACZone, ZoneRoom
    from models.sensor import Sensor
    from models.thermostat import ZoneThermostat
    from models.zone_schedule import ZoneSchedule

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to modify this building.")

    zone = db.query(HVACZone).filter(HVACZone.id == zone_id, HVACZone.building_id == building_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")

    assigned_sensor_count = db.query(Sensor).filter(Sensor.zone_id == zone_id).count()
    if assigned_sensor_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete zone while sensors are still assigned to it. Unassign the sensors first.",
        )

    linked_room_count = db.query(ZoneRoom).filter(ZoneRoom.zone_id == zone_id).count()
    if linked_room_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete zone while rooms are still linked to it. Remove the room links first.",
        )

    linked_thermostat_count = db.query(ZoneThermostat).filter(ZoneThermostat.zone_id == zone_id).count()
    if linked_thermostat_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete zone while thermostats are still linked to it. Remove the thermostat links first.",
        )

    linked_schedule_count = db.query(ZoneSchedule).filter(ZoneSchedule.zone_id == zone_id).count()
    if linked_schedule_count > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete zone while schedules still reference it. Remove the schedules first.",
        )

    db.delete(zone)
    db.commit()
    return TopologyDeleteResponse(detail="Zone deleted.")

@router.get(
    "/{building_id}/topology",
    response_model=BuildingTopologyResponse,
    responses={
        403: {"description": "Forbidden"},
        404: {"description": "Building not found"},
    }
)
def get_building_topology(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Return rooms, HVAC zones and thermostats for a building (used to populate sensor assignment dropdowns)."""
    from utils.policies import has_permission
    from models.topology import Room, HVACZone
    from models.thermostat import Thermostat

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING)
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)

    from models.topology import ZoneRoom
    rooms_q = (
        db.query(Room, ZoneRoom.zone_id)
        .outerjoin(ZoneRoom, ZoneRoom.room_id == Room.id)
        .filter(Room.building_id == building_id)
        .order_by(Room.name)
        .all()
    )
    zones = db.query(HVACZone).filter(HVACZone.building_id == building_id).order_by(HVACZone.name).all()
    thermostats = db.query(Thermostat).filter(Thermostat.building_id == building_id).order_by(Thermostat.name).all()

    return BuildingTopologyResponse(
        rooms=[TopologyRoom(id=r.id, name=r.name, zone_id=zone_id) for r, zone_id in rooms_q],
        zones=[TopologyZone(id=z.id, name=z.name) for z in zones],
        thermostats=[TopologyThermostat(id=t.id, name=t.name, is_controllable=bool(t.is_controllable)) for t in thermostats],
    )


class ZoneRoomLinkRequest(BaseModel):
    zone_id: int
    room_id: int


@router.post("/{building_id}/zone-rooms", status_code=204)
def link_room_to_zone(
    building_id: int,
    body: ZoneRoomLinkRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))],
):
    """Link an existing room to a zone (idempotent)."""
    from utils.policies import has_permission
    from models.topology import ZoneRoom, HVACZone, Room

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING)
    if not db.query(HVACZone).filter(HVACZone.id == body.zone_id, HVACZone.building_id == building_id).first():
        raise HTTPException(status_code=404, detail="Zone not found.")
    if not db.query(Room).filter(Room.id == body.room_id, Room.building_id == building_id).first():
        raise HTTPException(status_code=404, detail="Room not found.")
    exists = db.query(ZoneRoom).filter(ZoneRoom.zone_id == body.zone_id, ZoneRoom.room_id == body.room_id).first()
    if not exists:
        db.add(ZoneRoom(zone_id=body.zone_id, room_id=body.room_id))
        db.commit()


class ThermostatUpsertRequest(BaseModel):
    name: str
    is_controllable: bool = True


@router.post(
    "/{building_id}/thermostats",
    response_model=TopologyThermostat,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Building not found"}},
)
def upsert_thermostat(
    building_id: int,
    body: ThermostatUpsertRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))],
):
    """Upsert a thermostat by (building_id, name). Called when a controllable sensor is saved in the form draft so the thermostat dropdown updates immediately without a full device save."""
    from utils.policies import has_permission
    from models.thermostat import Thermostat

    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING)
    if not db.query(Building).filter(Building.id == building_id).first():
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)

    thermostat = db.query(Thermostat).filter(
        Thermostat.building_id == building_id,
        Thermostat.name == body.name,
    ).first()
    if thermostat:
        thermostat.is_controllable = body.is_controllable
    else:
        thermostat = Thermostat(building_id=building_id, name=body.name, is_controllable=body.is_controllable)
        db.add(thermostat)
    db.commit()
    db.refresh(thermostat)
    return TopologyThermostat(id=thermostat.id, name=thermostat.name, is_controllable=bool(thermostat.is_controllable))
