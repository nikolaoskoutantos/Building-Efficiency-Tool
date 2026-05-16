import math
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated, Optional, List, Dict, Any
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from db.connection import get_db
from models.hvac_models import Building
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from models.mqtt_config import MQTTBrokerConfig
from models.topology import HVACZone, ZoneHVACUnit
from models.zone_schedule import ZoneSchedule, ZoneScheduleInterval
import os

from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.building_sensor_weather_snapshot import fetch_building_sensor_weather_rows

DASHBOARD_ALLOWED_ROLES = ["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]
DASHBOARD_SCHEDULE_EDIT_ROLES = ["BUILDING_MANAGER", "ADMIN"]
BUILDING_RESOURCE_TYPE = "building"
FORBIDDEN_BUILDING_DETAIL = "You are not authorized for this building."
FORBIDDEN_BUILDING_RESPONSE_DESCRIPTION = "Forbidden: User not authorized for this building."
FORBIDDEN_ANY_BUILDINGS_DETAIL = "You are not authorized for any buildings."

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))]
)

ZERO_FLOAT_ABS_TOLERANCE = 1e-9

# Pydantic response models
class DashboardDevice(BaseModel):
    id: int
    building_id: int
    building_name: str
    name: str
    unit_type: str
    device_key: str
    sensor_count: int = 0
    created_at: Optional[str] = None

class DashboardBuilding(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    lat: Optional[str] = None
    lon: Optional[str] = None

class DashboardMQTTConfig(BaseModel):
    broker_url: str
    broker_port: int
    broker_username: Optional[str] = None
    broker_password: Optional[str] = None

class DashboardUserSettings(BaseModel):
    default_building_id: Optional[int] = None
    theme: Optional[str] = None
    notifications_enabled: bool = True
    auto_refresh_devices: bool = True

class DashboardResponse(BaseModel):
    devices: List[DashboardDevice]
    buildings: List[DashboardBuilding]
    mqtt_config: DashboardMQTTConfig
    user_settings: DashboardUserSettings
    stats: Dict[str, Any]


class DashboardTimeGridRow(BaseModel):
    ts: datetime
    data_kind: Optional[str] = None

    @field_validator('ts', mode='before')
    @classmethod
    def ensure_ts_utc(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    temperature: Optional[float] = None
    presence: Optional[float] = None
    energy: Optional[float] = None
    outdoor_temperature: Optional[float] = None
    outdoor_humidity: Optional[float] = None
    outdoor_pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    precipitation: Optional[float] = None
    weather_description: Optional[str] = None
    weather_source_timestamp: Optional[datetime] = None
    hvac_is_on: Optional[bool] = None
    hvac_setpoint: Optional[float] = None
    active_hvac_intervals: Optional[int] = None
    optimization_time: Optional[datetime] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    energy_saving_kwh: Optional[float] = None
    baseline_consumption_kwh: Optional[float] = None
    optimized_consumption_kwh: Optional[float] = None
    environmental_points: Optional[float] = None
    notes: Optional[str] = None
    is_optimized: Optional[bool] = None


class DashboardOptimizationContext(BaseModel):
    building_id: int
    starting_temperature: Optional[float] = None
    starting_time: Optional[str] = None
    outdoor_temperatures: List[float]
    setpoint: Optional[float] = None
    duration: int
    optimization_type: str = "normal"
    is_ready: bool = False
    missing_fields: List[str] = []


class DashboardTimeGridResponse(BaseModel):
    building_id: int
    reference_time: datetime
    rows: List[DashboardTimeGridRow]
    current_row: Optional[DashboardTimeGridRow] = None
    optimization_context: DashboardOptimizationContext
    latest_optimization_result: Optional[Dict[str, Any]] = None


class DashboardScheduleRow(BaseModel):
    id: Optional[int] = None
    start: str
    end: str
    enabled: bool
    setpoint: Optional[float] = None
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None


class DashboardScheduleResponse(BaseModel):
    building_id: int
    reference_time: datetime
    timezone: str = "Europe/Athens"
    rows: List[DashboardScheduleRow]


class DashboardScheduleUpdateRequest(BaseModel):
    reference_time: Optional[datetime] = None
    future_hours: float = 3
    rows: List[DashboardScheduleRow]


LOCAL_TZ = ZoneInfo("Europe/Athens")
SCHEDULE_PRIORITY = {
    "manual_override": 0,
    "dr_event": 1,
    "occupancy": 2,
    "comfort": 3,
}
SCHEDULE_OFF_MODE = "off"
SCHEDULE_ENABLED_MODE = "auto"
SCHEDULE_DASHBOARD_OVERRIDE_NAME = "Dashboard Override"


def _to_iso_minute_utc(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M")


def _floor_to_5min(value: datetime) -> datetime:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    minute = aware.minute - (aware.minute % 5)
    return aware.replace(minute=minute, second=0, microsecond=0)


def _to_local_time_label(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    local_dt = aware.astimezone(LOCAL_TZ)
    return local_dt.strftime("%H:%M")


def _parse_local_schedule_time(ref_now: datetime, time_label: str) -> datetime:
    local_ref = ref_now.astimezone(LOCAL_TZ)
    hours, minutes = [int(part) for part in time_label.split(":")]
    return local_ref.replace(hour=hours, minute=minutes, second=0, microsecond=0)


def _materialize_schedule_rows_local(ref_now: datetime, rows: List[DashboardScheduleRow]) -> List[tuple[DashboardScheduleRow, datetime, datetime]]:
    local_ref = ref_now.astimezone(LOCAL_TZ)
    ref_clock_minutes = local_ref.hour * 60 + local_ref.minute
    day_offset = 0
    previous_start_minutes: Optional[int] = None
    materialized: List[tuple[DashboardScheduleRow, datetime, datetime]] = []

    for index, row in enumerate(rows):
        start_hours, start_minutes = [int(part) for part in row.start.split(":")]
        end_hours, end_minutes = [int(part) for part in row.end.split(":")]

        start_clock_minutes = start_hours * 60 + start_minutes
        end_clock_minutes = end_hours * 60 + end_minutes

        if index == 0 and start_clock_minutes < ref_clock_minutes:
            day_offset = 1
        elif previous_start_minutes is not None and start_clock_minutes < previous_start_minutes:
            day_offset += 1

        start_local = local_ref.replace(hour=start_hours, minute=start_minutes, second=0, microsecond=0) + timedelta(days=day_offset)
        end_local = local_ref.replace(hour=end_hours, minute=end_minutes, second=0, microsecond=0) + timedelta(days=day_offset)

        if end_clock_minutes <= start_clock_minutes:
            end_local += timedelta(days=1)

        materialized.append((row, start_local, end_local))
        previous_start_minutes = start_clock_minutes

    return materialized


def _normalize_materialized_schedule_rows(
    materialized_rows: List[tuple[DashboardScheduleRow, datetime, datetime]]
) -> List[tuple[DashboardScheduleRow, datetime, datetime]]:
    if not materialized_rows:
        return []

    normalized: List[tuple[DashboardScheduleRow, datetime, datetime]] = []

    for row, start_local, end_local in sorted(materialized_rows, key=lambda item: (item[1], item[2])):
        if end_local <= start_local:
            continue
        _append_normalized_schedule_row(normalized, row, start_local, end_local)

    return normalized


def _append_normalized_schedule_row(
    normalized: List[tuple[DashboardScheduleRow, datetime, datetime]],
    row: DashboardScheduleRow,
    start_local: datetime,
    end_local: datetime,
) -> None:
    if not normalized:
        normalized.append((row, start_local, end_local))
        return

    _, _, prev_end = normalized[-1]
    trimmed_range = _trim_schedule_range_against_previous(prev_end, start_local, end_local)
    if trimmed_range is None:
        return

    start_local, end_local = trimmed_range
    normalized.append((row, start_local, end_local))


def _trim_schedule_range_against_previous(
    previous_end: datetime,
    start_local: datetime,
    end_local: datetime,
) -> Optional[tuple[datetime, datetime]]:
    if start_local >= previous_end:
        return start_local, end_local
    if end_local <= previous_end:
        return None
    return previous_end, end_local


def _get_building_hvac_unit(db: Session, building_id: int) -> HVACUnit:
    hvac_unit = (
        db.query(HVACUnit)
        .filter(HVACUnit.building_id == building_id)
        .order_by(HVACUnit.id.asc())
        .first()
    )
    if hvac_unit is None:
        raise HTTPException(status_code=404, detail="No HVAC unit found for this building.")
    return hvac_unit


def _ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _ensure_local(value: datetime) -> datetime:
    return _ensure_utc(value).astimezone(LOCAL_TZ)


def _get_building_hvac_zone(
    db: Session,
    building_id: int,
    hvac_unit_id: Optional[int] = None,
    zone_id: Optional[int] = None,
) -> tuple[HVACUnit, HVACZone]:
    # When zone_id is provided directly, resolve zone first then derive unit from it.
    # This supports multi-zone industrial units where the caller already knows the zone.
    if zone_id is not None:
        zone = (
            db.query(HVACZone)
            .filter(HVACZone.id == zone_id, HVACZone.building_id == building_id)
            .first()
        )
        if zone is None:
            raise HTTPException(status_code=404, detail="Zone not found for this building.")
        # Derive the HVAC unit from the zone (prefer the requested unit if supplied)
        unit_query = (
            db.query(HVACUnit)
            .join(ZoneHVACUnit, ZoneHVACUnit.hvac_unit_id == HVACUnit.id)
            .filter(ZoneHVACUnit.zone_id == zone.id, HVACUnit.building_id == building_id)
        )
        if hvac_unit_id is not None:
            unit_query = unit_query.filter(HVACUnit.id == hvac_unit_id)
        hvac_unit = unit_query.order_by(HVACUnit.id.asc()).first()
        if hvac_unit is None:
            raise HTTPException(status_code=404, detail="No HVAC unit found for this zone.")
        return hvac_unit, zone

    if hvac_unit_id is None:
        hvac_unit = _get_building_hvac_unit(db, building_id)
    else:
        hvac_unit = (
            db.query(HVACUnit)
            .filter(HVACUnit.id == hvac_unit_id, HVACUnit.building_id == building_id)
            .first()
        )
        if hvac_unit is None:
            raise HTTPException(status_code=404, detail="HVAC unit not found for this building.")

    zone = (
        db.query(HVACZone)
        .join(ZoneHVACUnit, ZoneHVACUnit.zone_id == HVACZone.id)
        .filter(
            HVACZone.building_id == building_id,
            ZoneHVACUnit.hvac_unit_id == hvac_unit.id,
        )
        .order_by(HVACZone.id.asc())
        .first()
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="No HVAC zone mapping found for this building.")

    return hvac_unit, zone


def _schedule_is_enabled(interval: ZoneScheduleInterval) -> bool:
    return (interval.hvac_mode or SCHEDULE_ENABLED_MODE).lower() != SCHEDULE_OFF_MODE


def _occurrence_entry(
    schedule: ZoneSchedule,
    interval: ZoneScheduleInterval,
    priority: int,
    enabled: bool,
    setpoint: Any,
    start_ts: datetime,
    end_ts: datetime,
) -> dict[str, Any]:
    return {
        "schedule_id": schedule.id,
        "interval_id": interval.id,
        "priority": priority,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "enabled": enabled,
        "setpoint": setpoint,
    }


def _build_manual_override_occurrences(
    schedule: ZoneSchedule,
    interval: ZoneScheduleInterval,
    priority: int,
    enabled: bool,
    setpoint: Any,
    window_start: datetime,
    window_end: datetime,
) -> List[dict[str, Any]]:
    start_utc = max(_ensure_utc(schedule.valid_from), window_start)
    end_utc = min(_ensure_utc(schedule.valid_to), window_end)
    if end_utc > start_utc:
        return [_occurrence_entry(schedule, interval, priority, enabled, setpoint, start_utc, end_utc)]
    return []


def _build_recurring_day_occurrence(
    schedule: ZoneSchedule,
    interval: ZoneScheduleInterval,
    priority: int,
    enabled: bool,
    setpoint: Any,
    current_date: Any,
    valid_from_local: Optional[datetime],
    valid_to_local: Optional[datetime],
    window_start_local: datetime,
    window_end_local: datetime,
) -> Optional[dict[str, Any]]:
    if interval.day_of_week is not None and current_date.isoweekday() != interval.day_of_week:
        return None
    start_local = datetime.combine(current_date, interval.start_time, tzinfo=LOCAL_TZ)
    end_local = datetime.combine(current_date, interval.end_time, tzinfo=LOCAL_TZ)
    if end_local <= start_local:
        end_local += timedelta(days=1)
    if valid_from_local and end_local <= valid_from_local:
        return None
    if valid_to_local and start_local >= valid_to_local:
        return None
    bounded_start = max(start_local, valid_from_local or start_local, window_start_local)
    bounded_end = min(end_local, valid_to_local or end_local, window_end_local)
    if bounded_end <= bounded_start:
        return None
    return _occurrence_entry(
        schedule, interval, priority, enabled, setpoint,
        bounded_start.astimezone(timezone.utc),
        bounded_end.astimezone(timezone.utc),
    )


def _build_recurring_occurrences(
    schedule: ZoneSchedule,
    interval: ZoneScheduleInterval,
    priority: int,
    enabled: bool,
    setpoint: Any,
    window_start: datetime,
    window_end: datetime,
) -> List[dict[str, Any]]:
    window_start_local = window_start.astimezone(LOCAL_TZ)
    window_end_local = window_end.astimezone(LOCAL_TZ)
    valid_from_local = _ensure_local(schedule.valid_from) if schedule.valid_from else None
    valid_to_local = _ensure_local(schedule.valid_to) if schedule.valid_to else None
    current_date = (window_start_local - timedelta(days=1)).date()
    end_date = (window_end_local + timedelta(days=1)).date()
    occurrences: List[dict[str, Any]] = []
    while current_date <= end_date:
        entry = _build_recurring_day_occurrence(
            schedule, interval, priority, enabled, setpoint,
            current_date, valid_from_local, valid_to_local, window_start_local, window_end_local,
        )
        if entry is not None:
            occurrences.append(entry)
        current_date += timedelta(days=1)
    return occurrences


def _materialize_schedule_interval_occurrences(
    schedule: ZoneSchedule,
    interval: ZoneScheduleInterval,
    window_start: datetime,
    window_end: datetime,
) -> List[dict[str, Any]]:
    priority = SCHEDULE_PRIORITY.get(schedule.schedule_type, 99)
    enabled = _schedule_is_enabled(interval)
    setpoint = None if not enabled else interval.target_setpoint_c
    if schedule.schedule_type == "manual_override" and schedule.valid_from and schedule.valid_to:
        return _build_manual_override_occurrences(schedule, interval, priority, enabled, setpoint, window_start, window_end)
    return _build_recurring_occurrences(schedule, interval, priority, enabled, setpoint, window_start, window_end)


def _pick_active_schedule_occurrence(active_occurrences: List[dict[str, Any]]) -> dict[str, Any]:
    return min(
        active_occurrences,
        key=lambda item: (item["priority"], -item["schedule_id"], -item["interval_id"]),
    )


def _merge_effective_schedule_ranges(
    occurrences: List[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> List[dict[str, Any]]:
    boundaries = {window_start, window_end}
    for occurrence in occurrences:
        boundaries.add(occurrence["start_ts"])
        boundaries.add(occurrence["end_ts"])

    merged: List[dict[str, Any]] = []
    ordered_boundaries = sorted(boundaries)

    for start_ts, end_ts in zip(ordered_boundaries, ordered_boundaries[1:]):
        if end_ts <= start_ts:
            continue
        active_occurrences = [
            occurrence
            for occurrence in occurrences
            if occurrence["start_ts"] < end_ts and occurrence["end_ts"] > start_ts
        ]
        if not active_occurrences:
            continue

        selected = _pick_active_schedule_occurrence(active_occurrences)
        candidate = {
            "start_ts": start_ts,
            "end_ts": end_ts,
            "enabled": selected["enabled"],
            "setpoint": selected["setpoint"],
        }

        if (
            merged
            and merged[-1]["enabled"] == candidate["enabled"]
            and merged[-1]["setpoint"] == candidate["setpoint"]
            and merged[-1]["end_ts"] == candidate["start_ts"]
        ):
            merged[-1]["end_ts"] = candidate["end_ts"]
        else:
            merged.append(candidate)

    return merged


def _fetch_effective_hvac_schedule_ranges(
    db: Session,
    building_id: int,
    window_start: datetime,
    window_end: datetime,
    hvac_unit_id: Optional[int] = None,
) -> List[dict[str, Any]]:
    _, zone = _get_building_hvac_zone(db, building_id, hvac_unit_id)
    schedule_rows = (
        db.query(ZoneSchedule, ZoneScheduleInterval)
        .join(ZoneScheduleInterval, ZoneScheduleInterval.schedule_id == ZoneSchedule.id)
        .filter(ZoneSchedule.zone_id == zone.id)
        .all()
    )

    occurrences: List[dict[str, Any]] = []
    for schedule, interval in schedule_rows:
        occurrences.extend(
            _materialize_schedule_interval_occurrences(schedule, interval, window_start, window_end)
        )

    return _merge_effective_schedule_ranges(occurrences, window_start, window_end)


def _fetch_schedule_rows(
    db: Session,
    building_id: int,
    ref_now: datetime,
    future_hours: float,
    hvac_unit_id: Optional[int] = None,
    zone_id: Optional[int] = None,
) -> List[dict[str, Any]]:
    window_start = ref_now.astimezone(timezone.utc)
    window_end = (ref_now + timedelta(hours=future_hours)).astimezone(timezone.utc)
    _, zone = _get_building_hvac_zone(db, building_id, hvac_unit_id, zone_id)

    schedule_rows = (
        db.query(ZoneSchedule, ZoneScheduleInterval)
        .join(ZoneScheduleInterval, ZoneScheduleInterval.schedule_id == ZoneSchedule.id)
        .filter(
            ZoneSchedule.zone_id == zone.id,
            ZoneSchedule.schedule_type == "manual_override",
            ZoneSchedule.name == SCHEDULE_DASHBOARD_OVERRIDE_NAME,
            ZoneSchedule.valid_from.isnot(None),
            ZoneSchedule.valid_to.isnot(None),
            ZoneSchedule.valid_to > window_start,
            ZoneSchedule.valid_from < window_end,
        )
        .order_by(ZoneSchedule.valid_from.asc(), ZoneSchedule.id.asc(), ZoneScheduleInterval.id.asc())
        .all()
    )

    return [
        {
            "id": schedule.id,
            "start": _to_local_time_label(_ensure_utc(schedule.valid_from)),
            "end": _to_local_time_label(_ensure_utc(schedule.valid_to)),
            "enabled": _schedule_is_enabled(interval),
            "setpoint": None if not _schedule_is_enabled(interval) else interval.target_setpoint_c,
            "start_ts": _ensure_utc(schedule.valid_from),
            "end_ts": _ensure_utc(schedule.valid_to),
        }
        for schedule, interval in schedule_rows
    ]


def _replace_schedule_rows(
    db: Session,
    building_id: int,
    ref_now: datetime,
    future_hours: float,
    rows: List[DashboardScheduleRow],
    hvac_unit_id: Optional[int] = None,
    zone_id: Optional[int] = None,
) -> List[dict[str, Any]]:
    hvac_unit, zone = _get_building_hvac_zone(db, building_id, hvac_unit_id, zone_id)
    window_start = ref_now.astimezone(timezone.utc)
    window_end = (ref_now + timedelta(hours=future_hours)).astimezone(timezone.utc)

    materialized_rows = _normalize_materialized_schedule_rows(_materialize_schedule_rows_local(ref_now, rows))
    materialized_utc_ranges = [
        (
            row,
            start_local.astimezone(timezone.utc),
            end_local.astimezone(timezone.utc),
        )
        for row, start_local, end_local in materialized_rows
    ]

    delete_window_start = min(
        [window_start, *[start_ts for _, start_ts, _ in materialized_utc_ranges]]
    )
    delete_window_end = max(
        [window_end, *[end_ts for _, _, end_ts in materialized_utc_ranges]]
    )

    overlapping_override_schedules = (
        db.query(ZoneSchedule)
        .filter(
            ZoneSchedule.zone_id == zone.id,
            ZoneSchedule.schedule_type == "manual_override",
            ZoneSchedule.name == SCHEDULE_DASHBOARD_OVERRIDE_NAME,
            ZoneSchedule.valid_to.isnot(None),
            ZoneSchedule.valid_from.isnot(None),
            ZoneSchedule.valid_to > delete_window_start,
            ZoneSchedule.valid_from < delete_window_end,
        )
        .all()
    )
    for schedule in overlapping_override_schedules:
        db.query(ZoneScheduleInterval).filter(
            ZoneScheduleInterval.schedule_id == schedule.id
        ).delete(synchronize_session=False)
        db.delete(schedule)

    for row, start_ts, end_ts in materialized_utc_ranges:
        db_schedule = ZoneSchedule(
            zone_id=zone.id,
            schedule_type="manual_override",
            name=SCHEDULE_DASHBOARD_OVERRIDE_NAME,
            valid_from=start_ts,
            valid_to=end_ts,
        )
        db.add(db_schedule)
        db.flush()

        start_local = start_ts.astimezone(LOCAL_TZ)
        end_local = end_ts.astimezone(LOCAL_TZ)
        db.add(
            ZoneScheduleInterval(
                schedule_id=db_schedule.id,
                day_of_week=None,
                start_time=start_local.timetz().replace(tzinfo=None),
                end_time=end_local.timetz().replace(tzinfo=None),
                target_setpoint_c=row.setpoint if row.enabled else None,
                hvac_mode=SCHEDULE_ENABLED_MODE if row.enabled else SCHEDULE_OFF_MODE,
                expected_occupancy=0,
            )
        )

    db.commit()
    return _fetch_schedule_rows(db, building_id, ref_now, future_hours, hvac_unit.id)


def _aggregate_sensor_weather_rows(raw_rows: List[dict[str, Any]]) -> List[dict[str, Any]]:
    by_ts: Dict[datetime, dict[str, Any]] = {}

    for row in raw_rows:
        ts = row.get("sensor_timestamp")
        if ts is None:
            continue

        bucket = by_ts.setdefault(ts, _build_sensor_weather_bucket(ts, row))
        _apply_sensor_value_to_bucket(bucket, row)
        _update_bucket_hvac_activity(bucket, row)

    return [by_ts[ts] for ts in sorted(by_ts.keys())]


def _build_sensor_weather_bucket(ts: datetime, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ts": ts,
        "temperature": None,
        "presence": None,
        "energy": None,
        "outdoor_temperature": row.get("temperature"),
        "outdoor_humidity": row.get("humidity"),
        "outdoor_pressure": row.get("pressure"),
        "wind_speed": row.get("wind_speed"),
        "wind_direction": row.get("wind_direction"),
        "precipitation": row.get("precipitation"),
        "weather_description": row.get("weather_description"),
        "weather_source_timestamp": row.get("weather_timestamp"),
        "hvac_is_on": row.get("hvac_is_on"),
        "hvac_setpoint": row.get("hvac_setpoint"),
        "active_hvac_intervals": 1 if row.get("hvac_is_on") else 0,
        "optimization_time": None,
        "input_hash": None,
        "output_hash": None,
        "energy_saving_kwh": None,
        "baseline_consumption_kwh": None,
        "optimized_consumption_kwh": None,
        "environmental_points": None,
        "notes": None,
        "is_optimized": None,
    }


def _apply_sensor_value_to_bucket(bucket: dict[str, Any], row: dict[str, Any]) -> None:
    sensor_field_by_type = {
        "temperature": "temperature",
        "presence": "presence",
        "energy": "energy",
    }
    sensor_field = sensor_field_by_type.get((row.get("sensor_type") or "").lower())
    if sensor_field is not None:
        bucket[sensor_field] = row.get("sensor_value")


def _update_bucket_hvac_activity(bucket: dict[str, Any], row: dict[str, Any]) -> None:
    if row.get("hvac_is_on"):
        bucket["active_hvac_intervals"] = max(bucket["active_hvac_intervals"] or 0, 1)


def _fetch_future_weather_rows(
    db: Session,
    building_id: int,
    ref_now: datetime,
    future_hours: float,
) -> List[dict[str, Any]]:
    end_time = ref_now + timedelta(hours=future_hours)
    stmt = text(
        """
        WITH building AS (
            SELECT lat::float8 AS lat, lon::float8 AS lon
            FROM buildings
            WHERE id = :building_id
        ),
        weather_location AS (
            SELECT wc.lat, wc.lon
            FROM (
                SELECT DISTINCT wd.lat, wd.lon
                FROM weather_data wd
            ) wc
            CROSS JOIN building b
            ORDER BY abs(wc.lat - b.lat) + abs(wc.lon - b.lon)
            LIMIT 1
        ),
        future_grid AS (
            SELECT generate_series(
                :start_ts,
                :end_ts,
                interval '5 minutes'
            ) AS ts
        )
        SELECT
            g.ts,
            w.temperature AS outdoor_temperature,
            w.humidity AS outdoor_humidity,
            w.pressure AS outdoor_pressure,
            w.wind_speed,
            w.wind_direction,
            w.precipitation,
            w.weather_description,
            w.timestamp AS weather_source_timestamp
        FROM future_grid g
        CROSS JOIN building b
        LEFT JOIN weather_data w
          ON EXISTS (
                SELECT 1
                FROM weather_location wl
                WHERE wl.lat = w.lat
                  AND wl.lon = w.lon
          )
         AND w.timestamp = g.ts
        ORDER BY g.ts
        """
    )
    result = db.execute(
        stmt,
        {
            "building_id": building_id,
            "start_ts": ref_now + timedelta(minutes=5),
            "end_ts": end_time,
        },
    )
    return [dict(row) for row in result.mappings().all()]


def _attach_future_context(
    db: Session,
    building_id: int,
    future_rows: List[dict[str, Any]],
) -> List[dict[str, Any]]:
    if not future_rows:
        return []

    start_ts = future_rows[0]["ts"]
    end_ts = future_rows[-1]["ts"]

    optimization_stmt = text(
        """
        SELECT optimization_time, window_start, window_end, input_hash, output_hash,
               energy_saving_kwh, baseline_consumption_kwh, optimized_consumption_kwh,
               environmental_points, notes, is_optimized
        FROM optimization_results
        WHERE building_id = :building_id
          AND COALESCE(window_start, optimization_time) <= :end_ts
          AND :start_ts < COALESCE(window_end, optimization_time + interval '1 hour')
        ORDER BY optimization_time
        """
    )

    hvac_rows = _fetch_effective_hvac_schedule_ranges(
        db,
        building_id,
        _ensure_utc(start_ts),
        _ensure_utc(end_ts) + timedelta(minutes=5),
    )
    optimization_rows = [dict(row) for row in db.execute(optimization_stmt, {"building_id": building_id, "end_ts": end_ts, "start_ts": start_ts}).mappings().all()]

    enriched: List[dict[str, Any]] = []
    optimization_index = 0
    latest_optimization: Optional[dict[str, Any]] = None

    for row in future_rows:
        ts = row["ts"]
        active = _get_active_hvac_rows(hvac_rows, ts)
        latest_optimization, optimization_index = _advance_latest_optimization(
            optimization_rows,
            optimization_index,
            ts,
            latest_optimization,
        )
        enriched.append(_build_enriched_future_row(row, active, latest_optimization))

    return enriched


def _get_active_hvac_rows(hvac_rows: List[dict[str, Any]], ts: datetime) -> List[dict[str, Any]]:
    return [item for item in hvac_rows if item["start_ts"] <= ts < item["end_ts"]]


def _optimization_active_at(opt: dict[str, Any], ts: datetime) -> bool:
    window_start = opt.get("window_start") or opt.get("optimization_time")
    window_end = opt.get("window_end") or (opt.get("optimization_time") or window_start) + timedelta(hours=1)
    return window_start <= ts < window_end


def _advance_latest_optimization(
    optimization_rows: List[dict[str, Any]],
    optimization_index: int,
    ts: datetime,
    latest_optimization: Optional[dict[str, Any]],
) -> tuple[Optional[dict[str, Any]], int]:
    while (
        optimization_index < len(optimization_rows)
        and (optimization_rows[optimization_index].get("window_start") or optimization_rows[optimization_index]["optimization_time"]) <= ts
    ):
        latest_optimization = optimization_rows[optimization_index]
        optimization_index += 1

    if latest_optimization is not None and not _optimization_active_at(latest_optimization, ts):
        latest_optimization = None

    return latest_optimization, optimization_index


def _build_enriched_future_row(
    row: dict[str, Any],
    active_hvac_rows: List[dict[str, Any]],
    latest_optimization: Optional[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ts": row["ts"],
        "temperature": None,
        "presence": None,
        "energy": None,
        "outdoor_temperature": row.get("outdoor_temperature"),
        "outdoor_humidity": row.get("outdoor_humidity"),
        "outdoor_pressure": row.get("outdoor_pressure"),
        "wind_speed": row.get("wind_speed"),
        "wind_direction": row.get("wind_direction"),
        "precipitation": row.get("precipitation"),
        "weather_description": row.get("weather_description"),
        "weather_source_timestamp": row.get("weather_source_timestamp"),
        "hvac_is_on": any(item.get("is_on") for item in active_hvac_rows),
        "hvac_setpoint": next((item.get("setpoint") for item in active_hvac_rows if item.get("is_on")), None),
        "active_hvac_intervals": sum(1 for item in active_hvac_rows if item.get("is_on")),
        **_optimization_snapshot(latest_optimization),
    }


def _optimization_snapshot(latest_optimization: Optional[dict[str, Any]]) -> dict[str, Any]:
    if latest_optimization is None:
        return {
            "optimization_time": None,
            "input_hash": None,
            "output_hash": None,
            "energy_saving_kwh": None,
            "baseline_consumption_kwh": None,
            "optimized_consumption_kwh": None,
            "environmental_points": None,
            "notes": None,
            "is_optimized": None,
        }

    return {
        "optimization_time": latest_optimization.get("optimization_time"),
        "input_hash": latest_optimization.get("input_hash"),
        "output_hash": latest_optimization.get("output_hash"),
        "energy_saving_kwh": latest_optimization.get("energy_saving_kwh"),
        "baseline_consumption_kwh": latest_optimization.get("baseline_consumption_kwh"),
        "optimized_consumption_kwh": latest_optimization.get("optimized_consumption_kwh"),
        "environmental_points": latest_optimization.get("environmental_points"),
        "notes": latest_optimization.get("notes"),
        "is_optimized": latest_optimization.get("is_optimized"),
    }


def _fill_outdoor_temperatures(rows: List[dict[str, Any]], ref_now: datetime, duration: int = 12) -> List[float]:
    eligible = [row for row in rows if row.get("ts") and row["ts"] >= ref_now]
    current = next((row for row in reversed(rows) if row.get("ts") and row["ts"] <= ref_now), None)
    values: List[float] = []

    current_outdoor = None if current is None else current.get("outdoor_temperature")
    values.append(float(current_outdoor) if current_outdoor is not None else 0.0)

    last_value = values[0]
    for row in eligible[:duration]:
        row_value = row.get("outdoor_temperature")
        if row_value is not None:
            last_value = float(row_value)
        values.append(last_value)

    while len(values) < duration + 1:
        values.append(last_value)

    return values


def _find_setpoint_in_rows(rows: List[dict[str, Any]], ref_now: datetime) -> Optional[float]:
    prev = next((r for r in reversed(rows) if r.get("ts") and r["ts"] <= ref_now and r.get("hvac_setpoint") is not None), None)
    if prev is not None:
        return prev["hvac_setpoint"]
    nxt = next((r for r in rows if r.get("ts") and r["ts"] >= ref_now and r.get("hvac_setpoint") is not None), None)
    return nxt["hvac_setpoint"] if nxt is not None else None


def _resolve_setpoint(
    current: dict[str, Any],
    rows: List[dict[str, Any]],
    ref_now: datetime,
    schedule_setpoints: Optional[List[float]],
) -> Optional[float]:
    sp = current.get("hvac_setpoint")
    if sp is None:
        sp = _find_setpoint_in_rows(rows, ref_now)
    if sp is not None:
        return sp
    return next((s for s in schedule_setpoints if s is not None), None) if schedule_setpoints else None


def _collect_optimization_missing_fields(
    current: dict[str, Any],
    outdoor_temperatures: List[float],
    fallback_setpoint: Optional[float],
) -> List[str]:
    missing: List[str] = []
    if current.get("temperature") is None:
        missing.append("temperature")
    if fallback_setpoint is None:
        missing.append("hvac_setpoint")
    if not outdoor_temperatures or all(math.isclose(v, 0.0, abs_tol=ZERO_FLOAT_ABS_TOLERANCE) for v in outdoor_temperatures):
        missing.append("outdoor_temperatures")
    return missing


def _build_optimization_context(
    building_id: int,
    rows: List[dict[str, Any]],
    ref_now: datetime,
    schedule_setpoints: Optional[List[float]] = None,
) -> DashboardOptimizationContext:
    current = next((row for row in reversed(rows) if row.get("ts") and row["ts"] <= ref_now), None)
    if current is None:
        return DashboardOptimizationContext(
            building_id=building_id,
            outdoor_temperatures=[],
            duration=12,
            missing_fields=["temperature", "ts", "outdoor_temperatures", "hvac_setpoint"],
        )
    outdoor_temperatures = _fill_outdoor_temperatures(rows, ref_now, duration=12)
    fallback_setpoint = _resolve_setpoint(current, rows, ref_now, schedule_setpoints)
    missing_fields = _collect_optimization_missing_fields(current, outdoor_temperatures, fallback_setpoint)
    return DashboardOptimizationContext(
        building_id=building_id,
        starting_temperature=None if current.get("temperature") is None else float(current["temperature"]),
        starting_time=_to_iso_minute_utc(current["ts"]),
        outdoor_temperatures=outdoor_temperatures,
        setpoint=None if fallback_setpoint is None else float(fallback_setpoint),
        duration=12,
        is_ready=len(missing_fields) == 0,
        missing_fields=missing_fields,
    )


def _fetch_latest_optimization_result(
    db: Session,
    building_id: int,
    user_id: int,
    ref_now: Optional[datetime] = None,
    hvac_unit_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    effective_ref = ref_now or datetime.now(timezone.utc)
    stmt = text(
        """
        SELECT output_data, window_start, window_end
        FROM optimization_results
        WHERE building_id = :building_id
          AND (user_id = :user_id OR user_id IS NULL)
          AND is_optimized IS TRUE
          AND output_data IS NOT NULL
          AND COALESCE(window_start, optimization_time) <= :ref_now
          AND :ref_now < COALESCE(window_end, optimization_time + interval '1 hour')
          AND (
            :hvac_unit_id IS NULL
            OR hvac_unit_id = :hvac_unit_id
            OR hvac_unit_id IS NULL
          )
        ORDER BY
          CASE WHEN hvac_unit_id IS NOT DISTINCT FROM :hvac_unit_id THEN 0 ELSE 1 END,
          optimization_time DESC
        LIMIT 1
        """
    )
    row = db.execute(stmt, {
        "building_id": building_id,
        "user_id": user_id,
        "ref_now": effective_ref,
        "hvac_unit_id": hvac_unit_id,
    }).mappings().first()
    if row is None:
        return None
    result = dict(row.get("output_data") or {})
    ws = row.get("window_start")
    we = row.get("window_end")
    if ws is not None:
        result["window_start"] = _ensure_utc(ws).isoformat()
    if we is not None:
        result["window_end"] = _ensure_utc(we).isoformat()
    return result


def _ensure_row_timestamps_utc(row: dict[str, Any]) -> dict[str, Any]:
    for key, value in row.items():
        if isinstance(value, datetime) and value.tzinfo is None:
            row[key] = value.replace(tzinfo=timezone.utc)
    return row


def _fetch_efficiency_tool_rows(
    db: Session,
    building_id: int,
    ref_now: datetime,
    past_hours: float,
    future_hours: float,
    hvac_unit_id: Optional[int] = None,
) -> List[dict[str, Any]]:
    stmt = text(
        """
        SELECT *
        FROM public.efficiency_tool_timeseries(
            :building_id,
            :ref_now,
            make_interval(hours => :past_hours),
            make_interval(hours => :future_hours),
            :hvac_unit_id
        )
        ORDER BY ts
        """
    )
    result = db.execute(
        stmt,
        {
            "building_id": building_id,
            "ref_now": ref_now,
            "past_hours": int(past_hours),
            "future_hours": int(future_hours),
            "hvac_unit_id": hvac_unit_id,
        },
    )
    return [_ensure_row_timestamps_utc(dict(row)) for row in result.mappings().all()]


@router.get("/", 
    response_model=DashboardResponse,
    responses={
        500: {"description": "Internal server error."},
        403: {"description": "Forbidden: User not authorized or missing user ID in token"}
    }
)
async def get_dashboard_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))]
):
    """
    Unified dashboard endpoint that loads all necessary data in a single optimized query.
    Returns devices, buildings, MQTT config, user settings, and statistics.
    """
    try:
        # Validate user/building association
        user_id = resolve_registered_user_id(user, db)
        from models.hvac_models import UserBuilding
        # Only allow buildings the user is registered to
        user_buildings = db.query(UserBuilding).filter_by(user_id=user_id, status="active").all()
        allowed_building_ids = [ub.building_id for ub in user_buildings]
        if not allowed_building_ids:
            raise HTTPException(status_code=403, detail=FORBIDDEN_ANY_BUILDINGS_DETAIL)
        buildings = db.query(Building).filter(Building.id.in_(allowed_building_ids)).all()
        buildings_data = [
            DashboardBuilding(
                id=building.id,
                name=building.name,
                address=building.address,
                lat=building.lat,
                lon=building.lon
            )
            for building in buildings
        ]

        # 2. Load devices with sensor counts in a single optimized query
        devices_query = db.query(
            HVACUnit.id,
            HVACUnit.building_id,
            Building.name.label('building_name'),
            HVACUnit.name,
            HVACUnit.unit_type,
            HVACUnit.device_key,
            func.count(Sensor.id).label('sensor_count')
        ).join(
            Building, HVACUnit.building_id == Building.id
        ).outerjoin(
            Sensor, Sensor.hvac_unit_id == HVACUnit.id
        ).filter(
            HVACUnit.device_key.isnot(None),
            HVACUnit.building_id.in_(allowed_building_ids)
        ).group_by(
            HVACUnit.id,
            HVACUnit.building_id,
            Building.name,
            HVACUnit.name,
            HVACUnit.unit_type,
            HVACUnit.device_key,
        ).all()

        devices_data = [
            DashboardDevice(
                id=device.id,
                building_id=device.building_id,
                building_name=device.building_name,
                name=device.name,
                unit_type=device.unit_type,
                device_key=device.device_key,
                sensor_count=device.sensor_count,
                created_at=None
            )
            for device in devices_query
        ]

        # 3. Load MQTT configuration - try from DB first, then .env fallback
        mqtt_config_db = db.query(MQTTBrokerConfig).first()
        
        if mqtt_config_db:
            mqtt_config = DashboardMQTTConfig(
                broker_url=mqtt_config_db.broker_url,
                broker_port=mqtt_config_db.broker_port,
                broker_username=mqtt_config_db.broker_username,
                broker_password=mqtt_config_db.broker_password
            )
        else:
            # Fallback to environment variables
            mqtt_config = DashboardMQTTConfig(
                broker_url=os.getenv("MQTT_HOST", "localhost"),
                broker_port=int(os.getenv("MQTT_PORT", "1883")),
                broker_username=os.getenv("MQTT_USER"),
                broker_password=os.getenv("MQTT_PASS")
            )

        # 4. Load user settings (assuming there's a current user context)
        # For now, return default settings - can be extended with user authentication
        user_settings = DashboardUserSettings(
            default_building_id=buildings_data[0].id if buildings_data else None,
            theme="light",
            notifications_enabled=True,
            auto_refresh_devices=True
        )

        # 5. Calculate dashboard statistics
        total_devices = len(devices_data)
        total_sensors = sum(device.sensor_count for device in devices_data)
        total_buildings = len(buildings_data)
        
        stats = {
            "total_devices": total_devices,
            "total_sensors": total_sensors,
            "total_buildings": total_buildings,
            "devices_with_sensors": len([d for d in devices_data if d.sensor_count > 0]),
            "average_sensors_per_device": round(total_sensors / total_devices, 1) if total_devices > 0 else 0
        }

        return DashboardResponse(
            devices=devices_data,
            buildings=buildings_data,
            mqtt_config=mqtt_config,
            user_settings=user_settings,
            stats=stats
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard data: {str(e)}")

@router.get("/stats",
    responses={
        403: {"description": "Forbidden: User not authorized for any buildings."},
        500: {"description": "Internal server error."}
    }
)
async def get_dashboard_stats(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))]
):
    """
    Quick endpoint for just dashboard statistics (for real-time updates)
    """
    try:
        user_id = resolve_registered_user_id(user, db)
        from models.hvac_models import UserBuilding
        user_buildings = db.query(UserBuilding).filter_by(user_id=user_id, status="active").all()
        allowed_building_ids = [ub.building_id for ub in user_buildings]
        if not allowed_building_ids:
            raise HTTPException(status_code=403, detail=FORBIDDEN_ANY_BUILDINGS_DETAIL)

        total_devices = db.query(HVACUnit).filter(
            HVACUnit.device_key.isnot(None),
            HVACUnit.building_id.in_(allowed_building_ids)
        ).count()
        total_sensors = db.query(Sensor).filter(Sensor.building_id.in_(allowed_building_ids)).count()
        total_buildings = db.query(Building).filter(Building.id.in_(allowed_building_ids)).count()
        
        # Devices with sensors
        devices_with_sensors = db.query(HVACUnit).join(Sensor).filter(
            HVACUnit.building_id.in_(allowed_building_ids)
        ).distinct().count()

        return {
            "total_devices": total_devices,
            "total_sensors": total_sensors,
            "total_buildings": total_buildings,
            "devices_with_sensors": devices_with_sensors,
            "average_sensors_per_device": round(total_sensors / total_devices, 1) if total_devices > 0 else 0,
            "last_updated": "now"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard stats: {str(e)}")


@router.get(
    "/time-grid/{building_id}",
    response_model=DashboardTimeGridResponse,
    responses={
        403: {"description": FORBIDDEN_BUILDING_RESPONSE_DESCRIPTION},
        404: {"description": "No HVAC unit or zone found for this building."},
        500: {"description": "Internal server error."},
    },
)
async def get_dashboard_time_grid(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))],
    ref_now: Annotated[Optional[datetime], Query(description="Reference time in ISO format")] = None,
    past_hours: Annotated[float, Query(description="Hours of past data to include", ge=0.5, le=24)] = 5,
    future_hours: Annotated[float, Query(description="Hours of future data to include", ge=0.5, le=24)] = 3,
    unit_id: Annotated[Optional[int], Query(description="Filter to a specific HVAC unit")] = None,
):
    """
    Return efficiency-tool timeseries for a building using the dedicated DB function.
    """
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, BUILDING_RESOURCE_TYPE, building_id, db):
            raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING_DETAIL)

        effective_ref_now = _floor_to_5min(ref_now or datetime.now(timezone.utc))
        rows = _fetch_efficiency_tool_rows(
            db,
            building_id=building_id,
            ref_now=effective_ref_now,
            past_hours=past_hours,
            future_hours=future_hours,
            hvac_unit_id=unit_id,
        )
        current_row_dict = next(
            (
                row
                for row in reversed(rows)
                if row.get("ts") and row["ts"] <= effective_ref_now and row.get("data_kind") == "history"
            ),
            None,
        )

        try:
            schedule_rows = _fetch_schedule_rows(
                db, building_id, effective_ref_now, 3.0,
                hvac_unit_id=unit_id, zone_id=None,
            )
            schedule_setpoints = [float(r["setpoint"]) for r in schedule_rows if r.get("setpoint") is not None]
        except Exception:
            schedule_setpoints = []

        optimization_context = _build_optimization_context(building_id, rows, effective_ref_now, schedule_setpoints)
        latest_optimization_result = _fetch_latest_optimization_result(
            db,
            building_id,
            user_id,
            ref_now=effective_ref_now,
            hvac_unit_id=unit_id,
        )

        return DashboardTimeGridResponse(
            building_id=building_id,
            reference_time=effective_ref_now,
            rows=[DashboardTimeGridRow(**row) for row in rows],
            current_row=None if current_row_dict is None else DashboardTimeGridRow(**current_row_dict),
            optimization_context=optimization_context,
            latest_optimization_result=latest_optimization_result,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard time grid: {str(e)}")


@router.get(
    "/hvac-schedule/{building_id}",
    response_model=DashboardScheduleResponse,
    responses={
        403: {"description": FORBIDDEN_BUILDING_RESPONSE_DESCRIPTION},
        404: {"description": "No HVAC unit found for this building."},
        500: {"description": "Internal server error."},
    },
)
async def get_dashboard_hvac_schedule(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))],
    ref_now: Annotated[Optional[datetime], Query(description="Reference time in ISO format")] = None,
    future_hours: Annotated[float, Query(description="Hours of future schedule to include", ge=0.5, le=24)] = 3,
    unit_id: Annotated[Optional[int], Query(description="Filter to a specific HVAC unit")] = None,
    zone_id: Annotated[Optional[int], Query(description="Filter to a specific zone (overrides unit_id zone resolution)")] = None,
):
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, BUILDING_RESOURCE_TYPE, building_id, db):
            raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING_DETAIL)

        effective_ref_now = _floor_to_5min(ref_now or datetime.now(timezone.utc))
        rows = _fetch_schedule_rows(db, building_id, effective_ref_now, future_hours, hvac_unit_id=unit_id, zone_id=zone_id)
        return DashboardScheduleResponse(
            building_id=building_id,
            reference_time=effective_ref_now,
            rows=[DashboardScheduleRow(**row) for row in rows],
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard HVAC schedule: {str(e)}")


@router.put(
    "/hvac-schedule/{building_id}",
    response_model=DashboardScheduleResponse,
    responses={
        403: {"description": FORBIDDEN_BUILDING_RESPONSE_DESCRIPTION},
        404: {"description": "No HVAC unit found for this building."},
        500: {"description": "Internal server error."},
    },
)
async def update_dashboard_hvac_schedule(
    building_id: int,
    payload: DashboardScheduleUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_SCHEDULE_EDIT_ROLES))],
    unit_id: Annotated[Optional[int], Query(description="Target a specific HVAC unit")] = None,
    zone_id: Annotated[Optional[int], Query(description="Target a specific zone (overrides unit_id zone resolution)")] = None,
):
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, BUILDING_RESOURCE_TYPE, building_id, db):
            raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING_DETAIL)

        effective_ref_now = _floor_to_5min(payload.reference_time or datetime.now(timezone.utc))
        rows = _replace_schedule_rows(
            db=db,
            building_id=building_id,
            ref_now=effective_ref_now,
            future_hours=payload.future_hours,
            rows=payload.rows,
            hvac_unit_id=unit_id,
            zone_id=zone_id,
        )
        return DashboardScheduleResponse(
            building_id=building_id,
            reference_time=effective_ref_now,
            rows=[DashboardScheduleRow(**row) for row in rows],
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update dashboard HVAC schedule: {str(e)}")


# ──────────────────────────────────────────────
# Zone listing endpoint
# ──────────────────────────────────────────────

class DashboardZone(BaseModel):
    id: int
    name: str
    zone_type: Optional[str] = None


class DashboardZonesResponse(BaseModel):
    building_id: int
    unit_id: Optional[int] = None
    zones: List[DashboardZone]


@router.get(
    "/zones/{building_id}",
    response_model=DashboardZonesResponse,
    responses={
        403: {"description": FORBIDDEN_BUILDING_RESPONSE_DESCRIPTION},
        500: {"description": "Internal server error."},
    },
)
async def get_building_zones(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))],
    unit_id: Annotated[Optional[int], Query(description="Filter zones to those linked to this HVAC unit")] = None,
):
    """Return zones for a building, optionally filtered to a specific HVAC unit."""
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, BUILDING_RESOURCE_TYPE, building_id, db):
            raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING_DETAIL)

        query = db.query(HVACZone).filter(HVACZone.building_id == building_id)
        if unit_id is not None:
            query = (
                query
                .join(ZoneHVACUnit, ZoneHVACUnit.zone_id == HVACZone.id)
                .filter(ZoneHVACUnit.hvac_unit_id == unit_id)
            )
        zones = query.order_by(HVACZone.id.asc()).all()

        return DashboardZonesResponse(
            building_id=building_id,
            unit_id=unit_id,
            zones=[DashboardZone(id=z.id, name=z.name, zone_type=z.zone_type) for z in zones],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load zones: {str(e)}")


# ──────────────────────────────────────────────
# Topology endpoint
# ──────────────────────────────────────────────

class TopologySensor(BaseModel):
    id: int
    name: str
    sensor_type: str
    unit: Optional[str] = None
    value: Optional[float] = None
    value_text: Optional[str] = None
    value_bool: Optional[bool] = None
    last_seen: Optional[str] = None
    hvac_unit_id: Optional[int] = None
    zone_id: Optional[int] = None
    payload_path: Optional[str] = None
    is_controllable: bool = False
    command_payload_template: Optional[str] = None


class TopologyZone(BaseModel):
    id: int
    name: str
    hvac_is_on: bool = False
    temperature: Optional[float] = None
    setpoint: Optional[float] = None
    thermostat_id: Optional[int] = None
    thermostat_name: Optional[str] = None
    is_controllable: bool = False
    external_bms_id: Optional[str] = None
    sensors: List[TopologySensor] = []


class TopologyUnit(BaseModel):
    id: int
    name: str
    unit_type: str
    connection_status: Optional[str] = None
    zones: List[TopologyZone] = []


class TopologyResponse(BaseModel):
    building_id: int
    units: List[TopologyUnit]


def _fetch_topology(db: Session, building_id: int) -> List[dict]:
    rows = db.execute(
        text("""
            WITH zone_primary_thermostat AS (
                SELECT DISTINCT ON (zt.zone_id)
                    zt.zone_id,
                    th.id               AS thermostat_id,
                    th.name             AS thermostat_name,
                    th.is_controllable,
                    th.external_bms_id
                FROM zone_thermostats zt
                JOIN thermostats th ON th.id = zt.thermostat_id
                ORDER BY zt.zone_id, (zt.role = 'primary') DESC, zt.thermostat_id
            ),
            latest_zone_state AS (
                SELECT DISTINCT ON (zone_id)
                    zone_id,
                    hvac_status,
                    measured_temp_c,
                    setpoint_c,
                    ts
                FROM zone_states
                WHERE ts <= NOW()
                ORDER BY zone_id, ts DESC
            ),
            latest_sensor_value AS (
                SELECT DISTINCT ON (sensor_id)
                    sensor_id,
                    value,
                    value_text,
                    value_bool,
                    ts
                FROM sensor_data
                WHERE ts <= NOW()
                ORDER BY sensor_id, ts DESC
            )
            SELECT
                u.id                    AS unit_id,
                u.name                  AS unit_name,
                u.unit_type,
                u.connection_status,
                z.id                    AS zone_id,
                z.name                  AS zone_name,
                lzs.hvac_status,
                lzs.measured_temp_c     AS temperature,
                lzs.setpoint_c          AS setpoint,
                zpt.thermostat_id       AS zone_thermostat_id,
                zpt.thermostat_name     AS zone_thermostat_name,
                COALESCE(zpt.is_controllable, false) AS zone_is_controllable,
                zpt.external_bms_id     AS zone_thermostat_bms_id,
                s.id                    AS sensor_id,
                s.name                  AS sensor_name,
                s.sensor_type,
                s.unit                  AS sensor_unit,
                s.hvac_unit_id                  AS sensor_hvac_unit_id,
                s.payload_path                  AS sensor_payload_path,
                s.is_controllable               AS sensor_is_controllable,
                s.command_payload_template      AS sensor_command_payload_template,
                lsv.value               AS sensor_value,
                lsv.value_text          AS sensor_value_text,
                lsv.value_bool          AS sensor_value_bool,
                lsv.ts                  AS sensor_last_seen
            FROM hvac_units u
            LEFT JOIN zone_hvac_units zhu ON zhu.hvac_unit_id = u.id
            LEFT JOIN hvac_zones z        ON z.id = zhu.zone_id
            LEFT JOIN latest_zone_state lzs      ON lzs.zone_id = z.id
            LEFT JOIN zone_primary_thermostat zpt ON zpt.zone_id = z.id
            LEFT JOIN sensors s                   ON s.zone_id = z.id
            LEFT JOIN thermostats th      ON th.id = s.thermostat_id
            LEFT JOIN latest_sensor_value lsv ON lsv.sensor_id = s.id
            WHERE u.building_id = :building_id
            ORDER BY u.id, z.id, s.id
        """),
        {"building_id": building_id},
    )
    return [dict(r) for r in rows.mappings().all()]


def _topology_zone_entry(row: dict) -> dict:
    return {
        "id": row["zone_id"],
        "name": row["zone_name"],
        "hvac_is_on": (row["hvac_status"] or "").lower() not in ("off", ""),
        "temperature": float(row["temperature"]) if row["temperature"] is not None else None,
        "setpoint": float(row["setpoint"]) if row["setpoint"] is not None else None,
        "thermostat_id": row["zone_thermostat_id"],
        "thermostat_name": row["zone_thermostat_name"],
        "is_controllable": bool(row["zone_is_controllable"]),
        "external_bms_id": row["zone_thermostat_bms_id"],
        "sensors": {},
    }


def _topology_sensor_entry(row: dict, zid: int) -> dict:
    return {
        "id": row["sensor_id"],
        "name": row["sensor_name"],
        "sensor_type": row["sensor_type"],
        "unit": row["sensor_unit"],
        "hvac_unit_id": row["sensor_hvac_unit_id"],
        "zone_id": zid,
        "payload_path": row["sensor_payload_path"],
        "is_controllable": bool(row["sensor_is_controllable"]),
        "command_payload_template": row["sensor_command_payload_template"],
        "value": float(row["sensor_value"]) if row["sensor_value"] is not None else None,
        "value_text": row["sensor_value_text"],
        "value_bool": bool(row["sensor_value_bool"]) if row["sensor_value_bool"] is not None else None,
        "last_seen": row["sensor_last_seen"].isoformat() if row["sensor_last_seen"] else None,
    }


def _assemble_topology_units(units: dict) -> List[TopologyUnit]:
    unit_list = []
    for u in units.values():
        zone_list = []
        for z in u["zones"].values():
            sensor_list = [TopologySensor(**s) for s in z["sensors"].values()]
            zone_is_controllable = any(s.is_controllable for s in sensor_list)
            zone_list.append(TopologyZone(
                **{k: v for k, v in z.items() if k not in ("sensors", "is_controllable")},
                is_controllable=zone_is_controllable,
                sensors=sensor_list,
            ))
        unit_list.append(TopologyUnit(
            **{k: v for k, v in u.items() if k != "zones"},
            zones=zone_list,
        ))
    return unit_list


def _build_topology_response(building_id: int, rows: List[dict]) -> TopologyResponse:
    units: dict = {}
    for row in rows:
        uid = row["unit_id"]
        if uid not in units:
            units[uid] = {"id": uid, "name": row["unit_name"], "unit_type": row["unit_type"] or "unknown", "connection_status": row["connection_status"], "zones": {}}
        if row["zone_id"] is None:
            continue
        zid = row["zone_id"]
        zones = units[uid]["zones"]
        if zid not in zones:
            zones[zid] = _topology_zone_entry(row)
        if row["sensor_id"] is None:
            continue
        sid = row["sensor_id"]
        if sid not in zones[zid]["sensors"]:
            zones[zid]["sensors"][sid] = _topology_sensor_entry(row, zid)
    return TopologyResponse(building_id=building_id, units=_assemble_topology_units(units))


@router.get(
    "/topology/{building_id}",
    response_model=TopologyResponse,
    responses={
        403: {"description": FORBIDDEN_BUILDING_RESPONSE_DESCRIPTION},
        500: {"description": "Internal server error."},
    },
)
async def get_building_topology(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(DASHBOARD_ALLOWED_ROLES))],
):
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission
        if not has_permission(user_id, BUILDING_RESOURCE_TYPE, building_id, db):
            raise HTTPException(status_code=403, detail=FORBIDDEN_BUILDING_DETAIL)
        rows = _fetch_topology(db, building_id)
        return _build_topology_response(building_id, rows)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load topology: {str(e)}")
