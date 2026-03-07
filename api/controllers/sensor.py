
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensor import Sensor
from typing import List
from pydantic import BaseModel

# Error message constants
SENSOR_NOT_FOUND_MSG = "Sensor not found"

router = APIRouter(prefix="/sensors", tags=["Sensors"])

# Pydantic schemas
class SensorBase(BaseModel):
    building_id: int
    hvac_unit_id: Optional[int] = None
    type: Optional[str] = None
    lat: float
    lon: float
    rate_of_sampling: Optional[float] = 5.0  # Default 5 seconds
    unit: str
    room: Optional[str] = None
    zone: Optional[str] = None
    central_unit: Optional[str] = None
    payload_path: Optional[str] = None

class SensorCreate(SensorBase):
    pass

class SensorUpdate(BaseModel):
    building_id: Optional[int] = None
    hvac_unit_id: Optional[int] = None
    type: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    rate_of_sampling: Optional[float] = None
    unit: Optional[str] = None
    room: Optional[str] = None
    zone: Optional[str] = None
    central_unit: Optional[str] = None
    payload_path: Optional[str] = None

class SensorRead(SensorBase):
    id: int
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/",
    response_model=SensorRead,
    responses={404: {"description": "Sensor not found"}}
)
def create_sensor(sensor: SensorCreate, db: Annotated[Session, Depends(get_db)]):
    db_sensor = Sensor(**sensor.model_dump())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@router.get(
    "/",
    response_model=List[SensorRead]
)
def read_sensors(db: Annotated[Session, Depends(get_db)], skip: int = 0, limit: int = 100):
    return db.query(Sensor).offset(skip).limit(limit).all()

@router.get(
    "/{sensor_id}",
    response_model=SensorRead,
    responses={404: {"description": "Sensor not found"}}
)
def read_sensor(sensor_id: int, db: Annotated[Session, Depends(get_db)]):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND_MSG)
    return sensor

@router.put(
    "/{sensor_id}",
    response_model=SensorRead,
    responses={404: {"description": "Sensor not found"}}
)
def update_sensor(sensor_id: int, sensor: SensorUpdate, db: Annotated[Session, Depends(get_db)]):
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not db_sensor:
        raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND_MSG)
    for key, value in sensor.model_dump(exclude_unset=True).items():
        setattr(db_sensor, key, value)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@router.delete(
    "/{sensor_id}",
    responses={200: {"description": "Sensor deleted"}, 404: {"description": "Sensor not found"}}
)
def delete_sensor(sensor_id: int, db: Annotated[Session, Depends(get_db)]):
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not db_sensor:
        raise HTTPException(status_code=404, detail=SENSOR_NOT_FOUND_MSG)
    db.delete(db_sensor)
    db.commit()
    return {"detail": "Sensor deleted"}
