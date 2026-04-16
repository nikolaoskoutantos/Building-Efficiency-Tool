from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.connection import get_db
from models.optimization_snapshot import (
    OptimizationInputSnapshotBatch,
    OptimizationInputSnapshotRow,
)
from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.building_sensor_weather_snapshot import (
    create_snapshot_batch,
    fetch_building_sensor_weather_rows,
    get_snapshot_payload,
    hash_snapshot_payload,
)
from utils.policies import has_permission

router = APIRouter(
    prefix="/building-sensor-weather",
    tags=["Building Sensor Weather"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)

@router.get(
    "/",
    summary="Get combined sensor and weather data for a building",
    responses={500: {"description": "Internal Server Error"}},
)
def get_building_sensor_weather(
    building_id: Annotated[int, Query(description="Building ID")],
    start_time: Annotated[datetime, Query(description="Start time (ISO format)")],
    end_time: Annotated[datetime, Query(description="End time (ISO format)")],
    db: Annotated[Session, Depends(get_db)],
    user=Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))
):
    user_id = resolve_registered_user_id(user, db)
    if not has_permission(user_id, "building", building_id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to access this building's data.")
    try:
        rows = fetch_building_sensor_weather_rows(db, building_id, start_time, end_time)
        batch = create_snapshot_batch(
            db,
            building_id=building_id,
            start_time=start_time,
            end_time=end_time,
            rows=rows,
            created_by_user_id=user_id,
            source_label="building_sensor_weather:get",
        )
        return {
            "snapshot_id": batch.id,
            "hash": batch.snapshot_hash,
            "created_at": batch.created_at.isoformat(),
            "data": {
                "building_id": building_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "rows": rows,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying data: {str(e)}")

@router.post("/verify", summary="Verify hash for building sensor weather data", responses={500: {"description": "Internal Server Error"}})
def verify_building_sensor_weather(
    building_id: Annotated[int, Query(description="Building ID")],
    start_time: Annotated[datetime, Query(description="Start time (ISO format)")],
    end_time: Annotated[datetime, Query(description="End time (ISO format)")],
    hash_value: Annotated[str, Query(description="Hash to verify")],
    db: Annotated[Session, Depends(get_db)],
    user=Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))
):
    try:
        user_id = resolve_registered_user_id(user, db)
        if not has_permission(user_id, "building", building_id, db):
            raise HTTPException(status_code=403, detail="You are not authorized to verify this building's data.")
        batch = (
            db.query(OptimizationInputSnapshotBatch)
            .filter(
                OptimizationInputSnapshotBatch.building_id == building_id,
                OptimizationInputSnapshotBatch.start_time == start_time,
                OptimizationInputSnapshotBatch.end_time == end_time,
                OptimizationInputSnapshotBatch.snapshot_hash == hash_value,
            )
            .order_by(OptimizationInputSnapshotBatch.created_at.desc())
            .first()
        )
        if not batch:
            raise HTTPException(status_code=404, detail="No stored snapshot found for the provided hash and time range.")

        rows = (
            db.query(OptimizationInputSnapshotRow)
            .filter(OptimizationInputSnapshotRow.snapshot_batch_id == batch.id)
            .order_by(OptimizationInputSnapshotRow.id.asc())
            .all()
        )
        payload = get_snapshot_payload(batch, rows)
        computed_hash = hash_snapshot_payload(payload)
        return {
            "valid": computed_hash == hash_value,
            "computed_hash": computed_hash,
            "snapshot_id": batch.id,
            "created_at": batch.created_at.isoformat(),
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error verifying hash: {str(e)}")
