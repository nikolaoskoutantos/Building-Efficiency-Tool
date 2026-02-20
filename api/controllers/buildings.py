BUILDING_NOT_FOUND = "Building not found"
BUILDING_DELETED = "Building deleted"
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from db import SessionLocal
from models.hvac_models import Building

router = APIRouter(prefix="/buildings", tags=["Buildings"])

class BuildingCreate(BaseModel):
    name: str
    address: Optional[str] = None

class BuildingRead(BuildingCreate):
    id: int
    class Config:
        orm_mode = True

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
def get_buildings(db: Annotated[Session, Depends(get_db)]):
    return db.query(Building).all()

@router.post(
    "/",
    response_model=BuildingRead,
    responses={404: {"description": "Building not found"}}
)
def create_building(building: BuildingCreate, db: Annotated[Session, Depends(get_db)]):
    db_building = Building(**building.dict())
    db.add(db_building)
    db.commit()
    db.refresh(db_building)
    return db_building

@router.get(
    "/{building_id}",
    response_model=BuildingRead,
    responses={404: {"description": "Building not found"}}
)
def get_building(building_id: int, db: Annotated[Session, Depends(get_db)]):
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)
    return building

@router.put(
    "/{building_id}",
    response_model=BuildingRead,
    responses={404: {"description": "Building not found"}}
)
def update_building(building_id: int, building: BuildingCreate, db: Annotated[Session, Depends(get_db)]):
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
    responses={200: {"description": "Building deleted"}, 404: {"description": "Building not found"}}
)
def delete_building(building_id: int, db: Annotated[Session, Depends(get_db)]):
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        raise HTTPException(status_code=404, detail=BUILDING_NOT_FOUND)
    db.delete(db_building)
    db.commit()
    return {"detail": BUILDING_DELETED}
