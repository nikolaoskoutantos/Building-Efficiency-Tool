BUILDING_NOT_FOUND = "Building not found"
BUILDING_DELETED = "Building deleted"
USER_ID_MISSING = "User ID missing in token."
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from db import SessionLocal
from models.hvac_models import Building

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
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    from models.hvac_models import UserBuilding
    user_id = resolve_registered_user_id(user, db)
    allowed_building_ids = [
        row.building_id
        for row in db.query(UserBuilding).filter_by(user_id=user_id, status="active").all()
    ]
    return db.query(Building).filter(Building.id.in_(allowed_building_ids)).all()

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
    resolve_registered_user_id(user, db)
    db_building = Building(**building.dict())
    db.add(db_building)
    db.commit()
    db.refresh(db_building)
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
        raise HTTPException(status_code=403, detail="You are not authorized to access this building.")
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
