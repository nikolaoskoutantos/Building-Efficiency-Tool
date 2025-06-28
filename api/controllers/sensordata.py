from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models.sensordata import SensorData
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/sensordata", tags=["SensorData"])

# Pydantic schemas
class SensorDataBase(BaseModel):
    sensor_id: int
    timestamp: datetime = None
    value: float

class SensorDataCreate(SensorDataBase):
    pass

class SensorDataRead(SensorDataBase):
    id: int
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=SensorDataRead)
def create_sensor_data(data: SensorDataCreate, db: Session = Depends(get_db)):
    db_data = SensorData(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data

@router.get("/", response_model=List[SensorDataRead])
def read_sensor_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(SensorData).offset(skip).limit(limit).all()

@router.get("/{data_id}", response_model=SensorDataRead)
def read_single_sensor_data(data_id: int, db: Session = Depends(get_db)):
    data = db.query(SensorData).filter(SensorData.id == data_id).first()
    if not data:
        raise HTTPException(status_code=404, detail="SensorData not found")
    return data

@router.delete("/{data_id}")
def delete_sensor_data(data_id: int, db: Session = Depends(get_db)):
    db_data = db.query(SensorData).filter(SensorData.id == data_id).first()
    if not db_data:
        raise HTTPException(status_code=404, detail="SensorData not found")
    db.delete(db_data)
    db.commit()
    return {"detail": "SensorData deleted"}
