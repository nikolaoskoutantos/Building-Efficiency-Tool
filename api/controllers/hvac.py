
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from db import SessionLocal
from models.hvac_models import HVACSchedule

router = APIRouter(prefix="/schedules", tags=["HVAC Schedules"])

class SchedulePeriod(BaseModel):
    start: str  # 'HH:mm'
    end: str    # 'HH:mm'
    enabled: bool


class ScheduleCreate(BaseModel):
    hvac_id: int
    periods: List[SchedulePeriod]


class ScheduleRead(ScheduleCreate):
    id: int
    created_at: str
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[ScheduleRead])
def get_schedules(hvac_id: int = None, db: Session = Depends(get_db)):
    q = db.query(HVACSchedule)
    if hvac_id is not None:
        q = q.filter(HVACSchedule.hvac_id == hvac_id)
    return q.order_by(HVACSchedule.created_at.desc()).all()

@router.post("/", response_model=ScheduleRead)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = HVACSchedule(hvac_id=schedule.hvac_id, periods=[p.dict() for p in schedule.periods])
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(HVACSchedule).filter(HVACSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

@router.put("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(schedule_id: int, schedule: ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = db.query(HVACSchedule).filter(HVACSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db_schedule.hvac_id = schedule.hvac_id
    db_schedule.periods = [p.dict() for p in schedule.periods]
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    db_schedule = db.query(HVACSchedule).filter(HVACSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(db_schedule)
    db.commit()
    return {"detail": "Schedule deleted"}
