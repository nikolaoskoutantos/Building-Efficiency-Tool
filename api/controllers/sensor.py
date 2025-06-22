from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensor import Sensor
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/sensors", tags=["Sensors"])

# Pydantic schemas
class SensorBase(BaseModel):
    lat: float
    lon: float
    rate_of_sampling: float
    raw_data_id: int
    unit: str

class SensorCreate(SensorBase):
    pass

class SensorRead(SensorBase):
    id: int
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=SensorRead)
def create_sensor(sensor: SensorCreate, db: Session = Depends(get_db)):
    db_sensor = Sensor(**sensor.dict())
    db.add(db_sensor)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@router.get("/", response_model=List[SensorRead])
def read_sensors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Sensor).offset(skip).limit(limit).all()

@router.get("/{sensor_id}", response_model=SensorRead)
def read_sensor(sensor_id: int, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor

@router.put("/{sensor_id}", response_model=SensorRead)
def update_sensor(sensor_id: int, sensor: SensorCreate, db: Session = Depends(get_db)):
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not db_sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    for key, value in sensor.dict().items():
        setattr(db_sensor, key, value)
    db.commit()
    db.refresh(db_sensor)
    return db_sensor

@router.delete("/{sensor_id}")
def delete_sensor(sensor_id: int, db: Session = Depends(get_db)):
    db_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not db_sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    db.delete(db_sensor)
    db.commit()
    return {"detail": "Sensor deleted"}
