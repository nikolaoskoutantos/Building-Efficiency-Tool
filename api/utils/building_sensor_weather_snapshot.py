from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.optimization_snapshot import (
    OptimizationInputSnapshotBatch,
    OptimizationInputSnapshotRow,
)
from utils.hashing import hash_object


def _convert_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _to_naive_timestamp(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _convert_value(value) for key, value in row.items()}


def fetch_building_sensor_weather_rows(
    db: Session,
    building_id: int,
    start_time: datetime,
    end_time: datetime,
) -> list[dict[str, Any]]:
    stmt = text(
        "SELECT * FROM public.get_building_sensor_weather(:building_id, :start_time, :end_time)"
    )
    result = db.execute(
        stmt,
        {
            "building_id": building_id,
            "start_time": _to_naive_timestamp(start_time),
            "end_time": _to_naive_timestamp(end_time),
        },
    )
    return [dict(row) for row in result.mappings().all()]


def build_snapshot_payload(
    building_id: int,
    start_time: datetime,
    end_time: datetime,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_rows = [_normalize_row(row) for row in rows]
    return {
        "building_id": building_id,
        "start_time": _convert_value(start_time),
        "end_time": _convert_value(end_time),
        "rows": normalized_rows,
    }


def hash_snapshot_payload(payload: dict[str, Any]) -> str:
    return hash_object(payload)


def create_snapshot_batch(
    db: Session,
    building_id: int,
    start_time: datetime,
    end_time: datetime,
    rows: list[dict[str, Any]],
    created_by_user_id: int | None,
    source_label: str | None = None,
) -> OptimizationInputSnapshotBatch:
    payload = build_snapshot_payload(building_id, start_time, end_time, rows)
    snapshot_hash = hash_snapshot_payload(payload)

    batch = OptimizationInputSnapshotBatch(
        building_id=building_id,
        start_time=start_time,
        end_time=end_time,
        snapshot_hash=snapshot_hash,
        created_by_user_id=created_by_user_id,
    )
    db.add(batch)
    db.flush()

    snapshot_rows: list[OptimizationInputSnapshotRow] = []
    for row in rows:
        normalized = _normalize_row(row)
        snapshot_rows.append(
            OptimizationInputSnapshotRow(
                snapshot_batch_id=batch.id,
                sensor_id=row.get("sensor_id"),
                sensor_type=row.get("sensor_type"),
                sensor_value=row.get("sensor_value"),
                sensor_timestamp=row.get("sensor_timestamp"),
                measurement_type=row.get("measurement_type"),
                sensor_unit=row.get("sensor_unit"),
                weather_timestamp=row.get("weather_timestamp"),
                temperature=row.get("temperature"),
                humidity=row.get("humidity"),
                pressure=row.get("pressure"),
                wind_speed=row.get("wind_speed"),
                wind_direction=row.get("wind_direction"),
                precipitation=row.get("precipitation"),
                weather_description=row.get("weather_description"),
                hvac_interval_id=row.get("hvac_interval_id"),
                hvac_is_on=row.get("hvac_is_on"),
                hvac_setpoint=row.get("hvac_setpoint"),
                hvac_interval_start=row.get("hvac_interval_start"),
                hvac_interval_end=row.get("hvac_interval_end"),
                row_hash=hash_object(normalized),
                source_label=source_label,
            )
        )

    db.add_all(snapshot_rows)
    db.commit()
    db.refresh(batch)
    return batch


def get_snapshot_payload(batch: OptimizationInputSnapshotBatch, rows: list[OptimizationInputSnapshotRow]) -> dict[str, Any]:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(
            _normalize_row(
                {
                    "sensor_id": row.sensor_id,
                    "sensor_type": row.sensor_type,
                    "sensor_value": row.sensor_value,
                    "sensor_timestamp": row.sensor_timestamp,
                    "measurement_type": row.measurement_type,
                    "sensor_unit": row.sensor_unit,
                    "weather_timestamp": row.weather_timestamp,
                    "temperature": row.temperature,
                    "humidity": row.humidity,
                    "pressure": row.pressure,
                    "wind_speed": row.wind_speed,
                    "wind_direction": row.wind_direction,
                    "precipitation": row.precipitation,
                    "weather_description": row.weather_description,
                    "hvac_interval_id": row.hvac_interval_id,
                    "hvac_is_on": row.hvac_is_on,
                    "hvac_setpoint": row.hvac_setpoint,
                    "hvac_interval_start": row.hvac_interval_start,
                    "hvac_interval_end": row.hvac_interval_end,
                }
            )
        )

    return {
        "building_id": batch.building_id,
        "start_time": _convert_value(batch.start_time),
        "end_time": _convert_value(batch.end_time),
        "rows": normalized_rows,
    }
