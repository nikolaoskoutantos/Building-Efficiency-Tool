SCHEDULE_NOT_FOUND = "Schedule not found"
SCHEDULE_DELETED = "Schedule deleted"

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated, Optional
import uuid
import secrets
import bcrypt
from datetime import datetime, timezone
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from db import SessionLocal
from models.hvac_models import HVACScheduleInterval


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
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))]
)



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
        from_attributes = True


@router.get(
    "/",
    response_model=List[ScheduleRead],
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
@router.get(
    "/",
    response_model=List[ScheduleRead],
    responses={
        403: {"description": "Forbidden: User not authorized to access this HVAC unit's schedules."},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def get_schedules(
    hvac_id: int = None,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    from utils.policies import has_permission
    user_id = user.get("user_id") if user else None
    q = db.query(HVACScheduleInterval)
    if hvac_id is not None:
        # Permission check for HVAC unit
        if user_id is None or not has_permission(user_id, "device", hvac_id, db):
            raise HTTPException(status_code=403, detail="You are not authorized to access this HVAC unit's schedules.")
        q = q.filter(HVACScheduleInterval.hvac_unit_id == hvac_id)
    return q.order_by(HVACScheduleInterval.created_at.desc()).all()

@router.post(
    "/",
    response_model=ScheduleRead,
    responses={
        400: {"description": "Invalid input"},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
@router.post(
    "/",
    response_model=ScheduleRead,
    responses={
        403: {"description": "Forbidden: User not authorized to create schedules for this HVAC unit."},
        400: {"description": "Invalid input"},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def create_schedule(
    schedule: ScheduleCreate,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    from utils.policies import has_permission
    user_id = user.get("user_id") if user else None
    if user_id is None or not has_permission(user_id, "device", schedule.hvac_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to create schedules for this HVAC unit.")
    # For compatibility, create one interval per period
    created_intervals = []
    for period in schedule.periods:
        db_interval = HVACScheduleInterval(
            hvac_unit_id=schedule.hvac_id,
            start_ts=datetime.strptime(period.start, '%H:%M'),
            end_ts=datetime.strptime(period.end, '%H:%M'),
            is_on=period.enabled,
            setpoint=None,
            building_id=None,
            created_by_user_id=None
        )
        db.add(db_interval)
        created_intervals.append(db_interval)
    db.commit()
    for interval in created_intervals:
        db.refresh(interval)
    return created_intervals[0] if created_intervals else None

@router.get(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
@router.get(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={
        403: {"description": "Forbidden: User not authorized to access this schedule."},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def get_schedule(
    schedule_id: int,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    from utils.policies import has_permission
    user_id = user.get("user_id") if user else None
    schedule = db.query(HVACScheduleInterval).filter(HVACScheduleInterval.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    if user_id is None or not has_permission(user_id, "device", schedule.hvac_unit_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to access this schedule.")
    return schedule

@router.put(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={
        400: {"description": "Invalid input"},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
@router.put(
    "/{schedule_id}",
    response_model=ScheduleRead,
    responses={
        403: {"description": "Forbidden: User not authorized to update this schedule."},
        400: {"description": "Invalid input"},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def update_schedule(
    schedule_id: int,
    schedule: ScheduleCreate,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    from utils.policies import has_permission
    user_id = user.get("user_id") if user else None
    db_schedule = db.query(HVACScheduleInterval).filter(HVACScheduleInterval.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    if user_id is None or not has_permission(user_id, "device", db_schedule.hvac_unit_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to update this schedule.")
    db_schedule.hvac_unit_id = schedule.hvac_id
    # Only update the first period for compatibility
    if schedule.periods:
        period = schedule.periods[0]
        db_schedule.start_ts = datetime.strptime(period.start, '%H:%M')
        db_schedule.end_ts = datetime.strptime(period.end, '%H:%M')
        db_schedule.is_on = period.enabled
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.delete(
    "/{schedule_id}",
    responses={
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
@router.delete(
    "/{schedule_id}",
    responses={
        403: {"description": "Forbidden: User not authorized to delete this schedule."},
        404: {"description": "Schedule not found"},
        500: {"description": "Internal server error"}
    }
)
def delete_schedule(
    schedule_id: int,
    db: DbSession = None,
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))] = None
):
    from utils.policies import has_permission
    user_id = user.get("user_id") if user else None
    db_schedule = db.query(HVACScheduleInterval).filter(HVACScheduleInterval.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail=SCHEDULE_NOT_FOUND)
    if user_id is None or not has_permission(user_id, "device", db_schedule.hvac_unit_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to delete this schedule.")
    db.delete(db_schedule)
    db.commit()
    return {"detail": SCHEDULE_DELETED}
