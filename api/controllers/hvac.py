SCHEDULE_NOT_FOUND = "Schedule not found"
SCHEDULE_DELETED = "Schedule deleted"

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated, Optional
from datetime import datetime, time
from models.hvac_unit import HVACUnit
from models.zone_schedule import ZoneSchedule, ZoneScheduleInterval
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from db import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbSession = Annotated[Session, Depends(get_db)]

from utils.auth_dependencies import get_current_user_role
router = APIRouter(
    prefix="/schedules",
    tags=["HVAC Schedules"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)


class ScheduleIntervalCreate(BaseModel):
    day_of_week: Optional[int] = None  
    start_time: str  # 'HH:MM'
    end_time: str    # 'HH:MM'
    target_setpoint_c: Optional[float] = None
    min_setpoint_c: Optional[float] = None
    max_setpoint_c: Optional[float] = None
    expected_occupancy: Optional[int] = None
    hvac_mode: Optional[str] = None  # cooling, heating, auto, off


class ScheduleCreate(BaseModel):
    zone_id: int
    schedule_type: str  # comfort, occupancy, dr_event, manual_override
    name: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    intervals: Optional[List[ScheduleIntervalCreate]] = None


class ScheduleRead(BaseModel):
    id: int
    zone_id: int
    schedule_type: str
    name: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ScheduleRead])
def get_schedules(
    zone_id: Optional[int] = None,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))] = None
):
    q = db.query(ZoneSchedule)
    if zone_id is not None:
        q = q.filter(ZoneSchedule.zone_id == zone_id)
    schedules = q.order_by(ZoneSchedule.id.desc()).all()
    return schedules


@router.post("/", response_model=ScheduleRead, responses={403: {"description": "Forbidden"}})
def create_schedule(
    schedule: ScheduleCreate,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    db_schedule = ZoneSchedule(
        zone_id=schedule.zone_id,
        schedule_type=schedule.schedule_type,
        name=schedule.name,
        valid_from=schedule.valid_from,
        valid_to=schedule.valid_to,
    )
    db.add(db_schedule)
    db.flush()

    if schedule.intervals:
        for iv in schedule.intervals:
            db.add(ZoneScheduleInterval(
                schedule_id=db_schedule.id,
                day_of_week=iv.day_of_week,
                start_time=datetime.strptime(iv.start_time, "%H:%M").time(),
                end_time=datetime.strptime(iv.end_time, "%H:%M").time(),
                target_setpoint_c=iv.target_setpoint_c,
                min_setpoint_c=iv.min_setpoint_c,
                max_setpoint_c=iv.max_setpoint_c,
                expected_occupancy=iv.expected_occupancy,
                hvac_mode=iv.hvac_mode,
            ))

    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@router.get("/{schedule_id}", response_model=ScheduleRead, responses={404: {"description": "Schedule not found"}})
def get_schedule(
    schedule_id: int,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))] = None
):
    schedule = db.query(ZoneSchedule).filter(ZoneSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleRead, responses={404: {"description": "Schedule not found"}})
def update_schedule(
    schedule_id: int,
    schedule: ScheduleCreate,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    db_schedule = db.query(ZoneSchedule).filter(ZoneSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    db_schedule.zone_id = schedule.zone_id
    db_schedule.schedule_type = schedule.schedule_type
    db_schedule.name = schedule.name
    db_schedule.valid_from = schedule.valid_from
    db_schedule.valid_to = schedule.valid_to
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@router.delete("/{schedule_id}", responses={404: {"description": "Schedule not found"}})
def delete_schedule(
    schedule_id: int,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    db_schedule = db.query(ZoneSchedule).filter(ZoneSchedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    db.delete(db_schedule)
    db.commit()
    return {"detail": SCHEDULE_DELETED}
