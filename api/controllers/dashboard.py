from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated, Optional, List, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from db.connection import get_db
from models.hvac_models import Building
from models.hvac_unit import HVACUnit
from models.sensor import Sensor
from models.mqtt_config import MQTTBrokerConfig
import os

from utils.auth_dependencies import get_current_user_role, resolve_registered_user_id
from utils.building_sensor_weather_snapshot import fetch_building_sensor_weather_rows
router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)

# Pydantic response models
class DashboardDevice(BaseModel):
    id: int
    building_id: int
    building_name: str
    central_unit: Optional[str] = None
    zone: Optional[str] = None
    room: Optional[str] = None
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


class DashboardScheduleRow(BaseModel):
    id: Optional[int] = None
    start: str
    end: str
    enabled: bool
    setpoint: Optional[float] = None


class DashboardScheduleResponse(BaseModel):
    building_id: int
    reference_time: datetime
    rows: List[DashboardScheduleRow]


class DashboardScheduleUpdateRequest(BaseModel):
    reference_time: Optional[datetime] = None
    future_hours: float = 3
    rows: List[DashboardScheduleRow]


LOCAL_TZ = ZoneInfo("Europe/Athens")


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

        if normalized:
            prev_row, prev_start, prev_end = normalized[-1]

            if start_local < prev_end:
                if end_local <= prev_end:
                    continue
                start_local = prev_end

            if (
                prev_end == start_local
                and bool(prev_row.enabled) == bool(row.enabled)
                and (prev_row.setpoint if prev_row.enabled else None) == (row.setpoint if row.enabled else None)
            ):
                normalized[-1] = (prev_row, prev_start, end_local)
                continue

        normalized.append((row, start_local, end_local))

    return normalized


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


def _fetch_schedule_rows(
    db: Session,
    building_id: int,
    ref_now: datetime,
    future_hours: float,
    hvac_unit_id: Optional[int] = None,
) -> List[dict[str, Any]]:
    window_start = ref_now.astimezone(timezone.utc).replace(tzinfo=None)
    window_end = (ref_now + timedelta(hours=future_hours)).astimezone(timezone.utc).replace(tzinfo=None)

    if hvac_unit_id is None:
        hvac_unit_id = _get_building_hvac_unit(db, building_id).id

    stmt = text(
        """
        SELECT id, start_ts, end_ts, is_on, setpoint
        FROM hvac_schedule_intervals
        WHERE building_id = :building_id
          AND hvac_unit_id = :hvac_unit_id
          AND end_ts > :window_start
          AND start_ts < :window_end
        ORDER BY start_ts, id
        """
    )
    rows = [
        dict(row)
        for row in db.execute(
            stmt,
            {
                "building_id": building_id,
                "hvac_unit_id": hvac_unit_id,
                "window_start": window_start,
                "window_end": window_end,
            },
        ).mappings().all()
    ]

    merged: List[dict[str, Any]] = []
    for row in rows:
        start_utc = row["start_ts"].replace(tzinfo=timezone.utc)
        end_utc = row["end_ts"].replace(tzinfo=timezone.utc)
        candidate = {
            "id": row["id"],
            "start_ts": start_utc,
            "end_ts": end_utc,
            "enabled": bool(row["is_on"]),
            "setpoint": row.get("setpoint"),
        }

        if (
            merged
            and merged[-1]["enabled"] == candidate["enabled"]
            and merged[-1]["end_ts"] == candidate["start_ts"]
        ):
            merged[-1]["end_ts"] = candidate["end_ts"]
            if merged[-1]["enabled"] and merged[-1]["setpoint"] is None:
                merged[-1]["setpoint"] = candidate["setpoint"]
        else:
            merged.append(candidate)

    return [
        {
            "id": row["id"],
            "start": _to_local_time_label(row["start_ts"]),
            "end": _to_local_time_label(row["end_ts"]),
            "enabled": row["enabled"],
            "setpoint": row["setpoint"],
        }
        for row in merged
    ]


def _replace_schedule_rows(
    db: Session,
    building_id: int,
    user_id: int,
    ref_now: datetime,
    future_hours: float,
    rows: List[DashboardScheduleRow],
) -> List[dict[str, Any]]:
    hvac_unit = _get_building_hvac_unit(db, building_id)
    window_start = ref_now.astimezone(timezone.utc).replace(tzinfo=None)
    window_end = (ref_now + timedelta(hours=future_hours)).astimezone(timezone.utc).replace(tzinfo=None)

    materialized_rows = _normalize_materialized_schedule_rows(_materialize_schedule_rows_local(ref_now, rows))
    materialized_utc_ranges = [
        (
            row,
            start_local.astimezone(timezone.utc).replace(tzinfo=None),
            end_local.astimezone(timezone.utc).replace(tzinfo=None),
        )
        for row, start_local, end_local in materialized_rows
    ]

    delete_window_start = min(
        [window_start, *[start_ts for _, start_ts, _ in materialized_utc_ranges]]
    )
    delete_window_end = max(
        [window_end, *[end_ts for _, _, end_ts in materialized_utc_ranges]]
    )

    db.execute(
        text(
            """
            DELETE FROM hvac_schedule_intervals
            WHERE building_id = :building_id
              AND hvac_unit_id = :hvac_unit_id
              AND end_ts > :window_start
              AND start_ts < :window_end
            """
        ),
        {
            "building_id": building_id,
            "hvac_unit_id": hvac_unit.id,
            "window_start": delete_window_start,
            "window_end": delete_window_end,
        },
    )

    insert_stmt = text(
        """
        INSERT INTO hvac_schedule_intervals (
            building_id,
            hvac_unit_id,
            start_ts,
            end_ts,
            is_on,
            setpoint,
            created_by_user_id
        )
        VALUES (
            :building_id,
            :hvac_unit_id,
            :start_ts,
            :end_ts,
            :is_on,
            :setpoint,
            :created_by_user_id
        )
        ON CONFLICT (hvac_unit_id, start_ts)
        DO UPDATE SET
            building_id = EXCLUDED.building_id,
            end_ts = EXCLUDED.end_ts,
            is_on = EXCLUDED.is_on,
            setpoint = EXCLUDED.setpoint,
            created_by_user_id = EXCLUDED.created_by_user_id
        """
    )

    for row, start_ts, end_ts in materialized_utc_ranges:
        db.execute(
            insert_stmt,
            {
                "building_id": building_id,
                "hvac_unit_id": hvac_unit.id,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "is_on": bool(row.enabled),
                "setpoint": row.setpoint if row.enabled else None,
                "created_by_user_id": user_id,
            },
        )

    db.commit()
    return _fetch_schedule_rows(db, building_id, ref_now, future_hours, hvac_unit.id)


def _aggregate_sensor_weather_rows(raw_rows: List[dict[str, Any]]) -> List[dict[str, Any]]:
    by_ts: Dict[datetime, dict[str, Any]] = {}

    for row in raw_rows:
        ts = row.get("sensor_timestamp")
        if ts is None:
            continue

        bucket = by_ts.setdefault(
            ts,
            {
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
            },
        )

        sensor_type = (row.get("sensor_type") or "").lower()
        sensor_value = row.get("sensor_value")
        if sensor_type == "temperature":
            bucket["temperature"] = sensor_value
        elif sensor_type == "presence":
            bucket["presence"] = sensor_value
        elif sensor_type == "energy":
            bucket["energy"] = sensor_value

        if row.get("hvac_is_on"):
            bucket["active_hvac_intervals"] = max(bucket["active_hvac_intervals"] or 0, 1)

    return [by_ts[ts] for ts in sorted(by_ts.keys())]


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

    hvac_stmt = text(
        """
        SELECT start_ts, end_ts, is_on, setpoint
        FROM hvac_schedule_intervals
        WHERE building_id = :building_id
          AND end_ts >= :start_ts
          AND start_ts <= :end_ts
        ORDER BY start_ts
        """
    )
    optimization_stmt = text(
        """
        SELECT optimization_time, input_hash, output_hash, energy_saving_kwh,
               baseline_consumption_kwh, optimized_consumption_kwh,
               environmental_points, notes, is_optimized
        FROM optimization_results
        WHERE building_id = :building_id
          AND optimization_time <= :end_ts
        ORDER BY optimization_time
        """
    )

    hvac_rows = [dict(row) for row in db.execute(hvac_stmt, {"building_id": building_id, "start_ts": start_ts, "end_ts": end_ts}).mappings().all()]
    optimization_rows = [dict(row) for row in db.execute(optimization_stmt, {"building_id": building_id, "end_ts": end_ts}).mappings().all()]

    enriched: List[dict[str, Any]] = []
    optimization_index = 0
    latest_optimization: Optional[dict[str, Any]] = None

    for row in future_rows:
        ts = row["ts"]
        active = [item for item in hvac_rows if item["start_ts"] <= ts < item["end_ts"]]

        while optimization_index < len(optimization_rows) and optimization_rows[optimization_index]["optimization_time"] <= ts:
            latest_optimization = optimization_rows[optimization_index]
            optimization_index += 1

        enriched_row = {
            "ts": ts,
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
            "hvac_is_on": any(item.get("is_on") for item in active),
            "hvac_setpoint": next((item.get("setpoint") for item in active if item.get("is_on")), None),
            "active_hvac_intervals": sum(1 for item in active if item.get("is_on")),
            "optimization_time": None if latest_optimization is None else latest_optimization.get("optimization_time"),
            "input_hash": None if latest_optimization is None else latest_optimization.get("input_hash"),
            "output_hash": None if latest_optimization is None else latest_optimization.get("output_hash"),
            "energy_saving_kwh": None if latest_optimization is None else latest_optimization.get("energy_saving_kwh"),
            "baseline_consumption_kwh": None if latest_optimization is None else latest_optimization.get("baseline_consumption_kwh"),
            "optimized_consumption_kwh": None if latest_optimization is None else latest_optimization.get("optimized_consumption_kwh"),
            "environmental_points": None if latest_optimization is None else latest_optimization.get("environmental_points"),
            "notes": None if latest_optimization is None else latest_optimization.get("notes"),
            "is_optimized": None if latest_optimization is None else latest_optimization.get("is_optimized"),
        }
        enriched.append(enriched_row)

    return enriched


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


def _build_optimization_context(building_id: int, rows: List[dict[str, Any]], ref_now: datetime) -> DashboardOptimizationContext:
    current = next((row for row in reversed(rows) if row.get("ts") and row["ts"] <= ref_now), None)
    if current is None:
        return DashboardOptimizationContext(
            building_id=building_id,
            outdoor_temperatures=[],
            duration=12,
            missing_fields=["temperature", "ts", "outdoor_temperatures", "hvac_setpoint"],
        )

    outdoor_temperatures = _fill_outdoor_temperatures(rows, ref_now, duration=12)
    missing_fields: List[str] = []
    if current.get("temperature") is None:
        missing_fields.append("temperature")
    fallback_setpoint = current.get("hvac_setpoint")
    if fallback_setpoint is None:
        previous_with_setpoint = next(
            (row for row in reversed(rows) if row.get("ts") and row["ts"] <= ref_now and row.get("hvac_setpoint") is not None),
            None,
        )
        fallback_setpoint = None if previous_with_setpoint is None else previous_with_setpoint.get("hvac_setpoint")
    if fallback_setpoint is None:
        missing_fields.append("hvac_setpoint")
    if not outdoor_temperatures or all(value == 0.0 for value in outdoor_temperatures):
        missing_fields.append("outdoor_temperatures")

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


def _fetch_efficiency_tool_rows(
    db: Session,
    building_id: int,
    ref_now: datetime,
    past_hours: float,
    future_hours: float,
) -> List[dict[str, Any]]:
    stmt = text(
        """
        SELECT *
        FROM public.efficiency_tool_timeseries(
            :building_id,
            :ref_now,
            make_interval(hours => :past_hours),
            make_interval(hours => :future_hours)
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
        },
    )
    return [dict(row) for row in result.mappings().all()]


@router.get("/", 
    response_model=DashboardResponse,
    responses={
        500: {"description": "Internal server error."},
        403: {"description": "Forbidden: User not authorized or missing user ID in token"}
    }
)
async def get_dashboard_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
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
            raise HTTPException(status_code=403, detail="You are not authorized for any buildings.")
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
            HVACUnit.central_unit,
            HVACUnit.zone,
            HVACUnit.room,
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
            HVACUnit.central_unit,
            HVACUnit.zone,
            HVACUnit.room,
            HVACUnit.device_key,
        ).all()

        devices_data = [
            DashboardDevice(
                id=device.id,
                building_id=device.building_id,
                building_name=device.building_name,
                central_unit=device.central_unit,
                zone=device.zone,
                room=device.room,
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
        500: {"description": "Internal server error."}
    }
)
async def get_dashboard_stats(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
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
            raise HTTPException(status_code=403, detail="You are not authorized for any buildings.")

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard stats: {str(e)}")


@router.get(
    "/time-grid/{building_id}",
    response_model=DashboardTimeGridResponse,
    responses={
        403: {"description": "Forbidden: User not authorized for this building."},
        500: {"description": "Internal server error."},
    },
)
async def get_dashboard_time_grid(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))],
    ref_now: Annotated[Optional[datetime], Query(description="Reference time in ISO format")] = None,
    past_hours: Annotated[float, Query(description="Hours of past data to include", ge=0.5, le=24)] = 5,
    future_hours: Annotated[float, Query(description="Hours of future data to include", ge=0.5, le=24)] = 3,
):
    """
    Return efficiency-tool timeseries for a building using the dedicated DB function.
    """
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, "building", building_id, db):
            raise HTTPException(status_code=403, detail="You are not authorized for this building.")

        effective_ref_now = _floor_to_5min(ref_now or datetime.now(timezone.utc))
        rows = _fetch_efficiency_tool_rows(
            db,
            building_id=building_id,
            ref_now=effective_ref_now,
            past_hours=past_hours,
            future_hours=future_hours,
        )
        current_row_dict = next(
            (
                row
                for row in reversed(rows)
                if row.get("ts") and row["ts"] <= effective_ref_now and row.get("data_kind") == "history"
            ),
            None,
        )

        optimization_context = _build_optimization_context(building_id, rows, effective_ref_now)

        return DashboardTimeGridResponse(
            building_id=building_id,
            reference_time=effective_ref_now,
            rows=[DashboardTimeGridRow(**row) for row in rows],
            current_row=None if current_row_dict is None else DashboardTimeGridRow(**current_row_dict),
            optimization_context=optimization_context,
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
        403: {"description": "Forbidden: User not authorized for this building."},
        404: {"description": "No HVAC unit found for this building."},
        500: {"description": "Internal server error."},
    },
)
async def get_dashboard_hvac_schedule(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))],
    ref_now: Annotated[Optional[datetime], Query(description="Reference time in ISO format")] = None,
    future_hours: Annotated[float, Query(description="Hours of future schedule to include", ge=0.5, le=24)] = 3,
):
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, "building", building_id, db):
            raise HTTPException(status_code=403, detail="You are not authorized for this building.")

        effective_ref_now = _floor_to_5min(ref_now or datetime.now(timezone.utc))
        rows = _fetch_schedule_rows(db, building_id, effective_ref_now, future_hours)
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
        403: {"description": "Forbidden: User not authorized for this building."},
        404: {"description": "No HVAC unit found for this building."},
        500: {"description": "Internal server error."},
    },
)
async def update_dashboard_hvac_schedule(
    building_id: int,
    payload: DashboardScheduleUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN"]))],
):
    try:
        user_id = resolve_registered_user_id(user, db)
        from utils.policies import has_permission

        if not has_permission(user_id, "building", building_id, db):
            raise HTTPException(status_code=403, detail="You are not authorized for this building.")

        effective_ref_now = _floor_to_5min(payload.reference_time or datetime.now(timezone.utc))
        rows = _replace_schedule_rows(
            db=db,
            building_id=building_id,
            user_id=user_id,
            ref_now=effective_ref_now,
            future_hours=payload.future_hours,
            rows=payload.rows,
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
