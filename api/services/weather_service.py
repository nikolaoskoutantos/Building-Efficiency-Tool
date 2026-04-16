from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta


def _to_naive_utc(ts_raw):
    ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else ts_raw
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _interpolate(v0, v1, ratio):
    """Linear interpolation with null-safe fallback."""
    if v0 is None and v1 is None:
        return None
    if v0 is None:
        return v1
    if v1 is None:
        return v0
    return v0 + (v1 - v0) * ratio


def _at(arr, idx):
    return arr[idx] if idx < len(arr) else None


def _weather_code_to_description(weather_codes, idx):
    code = _at(weather_codes, idx)
    return str(code) if code is not None else None


def _build_interpolated_row(lat, lon, ts, idx, ratio, attrs, weather_codes):
    return {
        "timestamp": ts,
        "lat": lat,
        "lon": lon,
        "temperature": _interpolate(_at(attrs["temperature"], idx), _at(attrs["temperature"], idx + 1), ratio),
        "humidity": _interpolate(_at(attrs["humidity"], idx), _at(attrs["humidity"], idx + 1), ratio),
        "pressure": _interpolate(_at(attrs["pressure"], idx), _at(attrs["pressure"], idx + 1), ratio),
        "wind_speed": _interpolate(_at(attrs["wind_speed"], idx), _at(attrs["wind_speed"], idx + 1), ratio),
        "wind_direction": _interpolate(_at(attrs["wind_direction"], idx), _at(attrs["wind_direction"], idx + 1), ratio),
        "precipitation": _interpolate(_at(attrs["precipitation"], idx), _at(attrs["precipitation"], idx + 1), ratio),
        "weather_description": _weather_code_to_description(weather_codes, idx),
    }


def _build_final_row(lat, lon, last_ts, last_idx, attrs, weather_codes):
    return {
        "timestamp": last_ts,
        "lat": lat,
        "lon": lon,
        "temperature": _at(attrs["temperature"], last_idx),
        "humidity": _at(attrs["humidity"], last_idx),
        "pressure": _at(attrs["pressure"], last_idx),
        "wind_speed": _at(attrs["wind_speed"], last_idx),
        "wind_direction": _at(attrs["wind_direction"], last_idx),
        "precipitation": _at(attrs["precipitation"], last_idx),
        "weather_description": _weather_code_to_description(weather_codes, last_idx),
    }


def _expand_hourly_to_5min_rows(lat, lon, hourly):
    """
    Expand Open-Meteo hourly arrays into 5-minute rows.
    - Numeric weather values are linearly interpolated between consecutive hours.
    - weather_code is carried from the current hour bucket.
    """
    times = hourly.get("time", [])
    if not times:
        return []

    attrs = {
        "temperature": [_safe_float(v) for v in hourly.get("temperature_2m", [])],
        "humidity": [_safe_float(v) for v in hourly.get("relative_humidity_2m", [])],
        "pressure": [_safe_float(v) for v in hourly.get("surface_pressure", [])],
        "wind_speed": [_safe_float(v) for v in hourly.get("wind_speed_10m", [])],
        "wind_direction": [_safe_float(v) for v in hourly.get("wind_direction_10m", [])],
        "precipitation": [_safe_float(v) for v in hourly.get("precipitation", [])],
    }
    weather_codes = hourly.get("weather_code", [])

    parsed_times = []
    for t in times:
        try:
            parsed_times.append(_to_naive_utc(t))
        except Exception:
            parsed_times.append(None)

    rows = []

    for i in range(len(parsed_times) - 1):
        t0 = parsed_times[i]
        t1 = parsed_times[i + 1]
        if t0 is None or t1 is None or t1 <= t0:
            continue

        step_count = int((t1 - t0).total_seconds() // 300)
        if step_count <= 0:
            step_count = 1

        for step in range(step_count):
            ratio = step / step_count
            ts = t0 + timedelta(minutes=5 * step)
            rows.append(_build_interpolated_row(lat, lon, ts, i, ratio, attrs, weather_codes))

    # Include final timestamp row as-is
    last_idx = len(parsed_times) - 1
    last_ts = parsed_times[last_idx]
    if last_ts is not None:
        rows.append(_build_final_row(lat, lon, last_ts, last_idx, attrs, weather_codes))

    return rows

async def save_open_meteo_hourly(async_db: AsyncSession, weather_json: dict):
    """
    Parses Open-Meteo hourly response and replaces stored weather rows for the
    target location with the latest Open-Meteo forecast.
    """
    lat = float(weather_json["latitude"])
    lon = float(weather_json["longitude"])

    hourly = weather_json.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("Missing hourly.time")

    stmt = text("""
        INSERT INTO weather_data
            ("timestamp", lat, lon, temperature, humidity, pressure, wind_speed, wind_direction, precipitation, weather_description)
        VALUES
            (:timestamp, :lat, :lon, :temperature, :humidity, :pressure, :wind_speed, :wind_direction, :precipitation, :weather_description)
        ON CONFLICT ("timestamp", lat, lon)
        DO UPDATE SET
            temperature=EXCLUDED.temperature,
            humidity=EXCLUDED.humidity,
            pressure=EXCLUDED.pressure,
            wind_speed=EXCLUDED.wind_speed,
            wind_direction=EXCLUDED.wind_direction,
            precipitation=EXCLUDED.precipitation,
            weather_description=EXCLUDED.weather_description;
    """)

    rows = _expand_hourly_to_5min_rows(lat, lon, hourly)
    # Keep weather_data authoritative to the latest provider payload for a
    # location so stale mock/demo rows do not keep leaking into the UI.
    await async_db.execute(
        text(
            """
            DELETE FROM weather_data
            WHERE lat = :lat
              AND lon = :lon
            """
        ),
        {"lat": lat, "lon": lon},
    )

    for row in rows:
        await async_db.execute(stmt, row)

    await async_db.commit()

import os
import asyncio
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

OPEN_METEO_URL = os.getenv('OPEN_METEO_URL', 'https://api.open-meteo.com/v1/forecast')
MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', 20))
RETRY_LIMIT = int(os.getenv('RETRY_LIMIT', 2))
logger = logging.getLogger("weather_scheduler")

async def fetch_weather(lat, lon, session):
    """
    Fetch weather from the configured provider (OpenWeatherMap or Open-Meteo).
    """
    url = OPEN_METEO_URL
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation,weather_code",
        "forecast_days": 5,
        "timezone": "UTC"
    }
    headers = {}
    for attempt in range(RETRY_LIMIT + 1):
        try:
            async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            if attempt < RETRY_LIMIT:
                await asyncio.sleep(1)
                continue
            logger.error(f"Failed to fetch weather for ({lat}, {lon}): {e}")
            return None

async def upsert_weather(async_db: AsyncSession, lat, lon, weather_json):
    hourly = weather_json.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("Open-Meteo response missing hourly.time")

    # pick last hour in response (latest)
    i = len(times) - 1

    timestamp = datetime.fromisoformat(times[i])
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)

    def at(key):
        arr = hourly.get(key, [])
        return arr[i] if i < len(arr) else None

    temperature = at("temperature_2m")
    humidity = at("relative_humidity_2m")
    pressure = at("surface_pressure")
    wind_speed = at("wind_speed_10m")
    wind_direction = at("wind_direction_10m")
    precipitation = at("precipitation")
    weather_code = at("weather_code")
    weather_description = str(weather_code) if weather_code is not None else None

    stmt = text("""
        INSERT INTO weather_data ("timestamp", lat, lon, temperature, humidity, pressure, wind_speed, wind_direction, precipitation, weather_description)
        VALUES (:timestamp, :lat, :lon, :temperature, :humidity, :pressure, :wind_speed, :wind_direction, :precipitation, :weather_description)
        ON CONFLICT ("timestamp", lat, lon)
        DO UPDATE SET
            temperature=EXCLUDED.temperature,
            humidity=EXCLUDED.humidity,
            pressure=EXCLUDED.pressure,
            wind_speed=EXCLUDED.wind_speed,
            wind_direction=EXCLUDED.wind_direction,
            precipitation=EXCLUDED.precipitation,
            weather_description=EXCLUDED.weather_description;
    """)
    await async_db.execute(stmt, {
        "timestamp": timestamp,
        "lat": lat,
        "lon": lon,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "precipitation": precipitation,
        "weather_description": weather_description
    })
    await async_db.commit()

# --- Bulk weather helpers (top-level scope) ---
async def _insert_bulk_weather_data(db, data):
    """Helper to insert weather data for each location and hour."""
    for loc in data:
        await _process_bulk_location(db, loc)
    await db.commit()

async def _process_bulk_location(db, loc):
    """Helper to process a single location's weather data for bulk insert."""
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    hourly = loc.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return
    weather_attrs = _extract_weather_attrs(hourly)
    await _insert_all_weather_rows(db, times, lat, lon, weather_attrs)

async def _insert_all_weather_rows(db, times, lat, lon, weather_attrs):
    for i, t in enumerate(times):
        row = _get_weather_row_for_index(weather_attrs, i)
        await _insert_weather_row(db, t, lat, lon, *row)

def _extract_weather_attrs(hourly):
    """Extract weather attributes from hourly data as lists."""
    return {
        "temperature": hourly.get("temperature_2m", []),
        "humidity": hourly.get("relative_humidity_2m", []),
        "pressure": hourly.get("surface_pressure", []),
        "wind_speed": hourly.get("wind_speed_10m", []),
        "wind_direction": hourly.get("wind_direction_10m", []),
        "precipitation": hourly.get("precipitation", []),
        "weather_description": [str(w) for w in hourly.get("weather_code", [])],
    }

def _get_weather_row_for_index(attrs, i):
    """Return a tuple of weather values for the i-th index, handling missing data."""
    return (
        attrs["temperature"][i] if i < len(attrs["temperature"]) else None,
        attrs["humidity"][i] if i < len(attrs["humidity"]) else None,
        attrs["pressure"][i] if i < len(attrs["pressure"]) else None,
        attrs["wind_speed"][i] if i < len(attrs["wind_speed"]) else None,
        attrs["wind_direction"][i] if i < len(attrs["wind_direction"]) else None,
        attrs["precipitation"][i] if i < len(attrs["precipitation"]) else None,
        attrs["weather_description"][i] if i < len(attrs["weather_description"]) else None,
    )

async def _insert_weather_row(db, timestamp, lat, lon, temperature, humidity, pressure, wind_speed, wind_direction, precipitation, weather_description):
    try:
        # Convert ISO string timestamp to naive UTC datetime if needed
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        if isinstance(timestamp, datetime) and timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        stmt = text('''
            INSERT INTO weather_data ("timestamp", lat, lon, temperature, humidity, pressure, wind_speed, wind_direction, precipitation, weather_description)
            VALUES (:timestamp, :lat, :lon, :temperature, :humidity, :pressure, :wind_speed, :wind_direction, :precipitation, :weather_description)
            ON CONFLICT ("timestamp", lat, lon)
            DO UPDATE SET
                temperature=EXCLUDED.temperature,
                humidity=EXCLUDED.humidity,
                pressure=EXCLUDED.pressure,
                wind_speed=EXCLUDED.wind_speed,
                wind_direction=EXCLUDED.wind_direction,
                precipitation=EXCLUDED.precipitation,
                weather_description=EXCLUDED.weather_description;
        ''')
        await db.execute(stmt, {
            "timestamp": timestamp,
            "lat": lat,
            "lon": lon,
            "temperature": temperature,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "precipitation": precipitation,
            "weather_description": weather_description
        })
    except Exception as e:
        logger.error(f"Failed to insert weather for ({lat},{lon}) at {timestamp}: {e}")

async def fetch_and_store_bulk_weather(async_db_maker):
    """
    Fetch weather for all buildings using a single Open-Meteo API call and store results in weather_data table.
    """
    from sqlalchemy import text
    import math

    async with async_db_maker() as db:
        locations = (await db.execute(text("SELECT DISTINCT lat, lon FROM buildings WHERE lat IS NOT NULL AND lon IS NOT NULL"))).fetchall()
    if not locations:
        logger.info("No buildings with lat/lon found.")
        return

    # Prepare lat/lon lists for Open-Meteo
    lat_list = []
    lon_list = []
    for row in locations:
        try:
            lat = float(row.lat)
            lon = float(row.lon)
            lat_list.append(str(lat))
            lon_list.append(str(lon))
        except Exception as e:
            logger.warning(f"Skipping location due to invalid lat/lon: {e}")

    if not lat_list or not lon_list:
        logger.info("No valid lat/lon pairs to query.")
        return

    # Build Open-Meteo API request
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={','.join(lat_list)}&longitude={','.join(lon_list)}"
        f"&hourly=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation,weather_code"
        f"&forecast_days=3&timezone=UTC"
    )
    logger.info(f"Requesting Open-Meteo bulk weather for {len(lat_list)} locations.")
    print(f"[DEBUG] Open-Meteo request URL: {url}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
                print(f"[DEBUG] Open-Meteo response: {str(data)[:1000]}")  # Print first 1000 chars for brevity
        except Exception as e:
            logger.error(f"Failed to fetch bulk weather: {e}")
            return

    # Open-Meteo returns a dict for single location, list for multiple
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        logger.error("Unexpected Open-Meteo response format (expected dict or list).")
        return

    async with async_db_maker() as db:
        for loc in data:
            await save_open_meteo_hourly(db, loc)
    logger.info(f"Bulk weather data inserted for {len(data)} locations.")

async def _process_building(row, sem, session, async_db_maker, counters):
    async with sem:
        lat, lon = float(row.lat), float(row.lon)
        weather = await fetch_weather(lat, lon, session)
        counters['processed'] += 1
        if weather:
            try:
                async with async_db_maker() as db2:
                    # IMPORTANT: save all hourly rows, not one row
                    await save_open_meteo_hourly(db2, weather)
                counters['succeeded'] += 1
            except Exception as e:
                logger.error(f"DB upsert failed for ({lat}, {lon}): {e}")
                counters['failed'] += 1
        else:
            counters['failed'] += 1

async def refresh_weather_for_all_buildings(async_db_maker):
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.hvac_models import Building  # Absolute import for CLI compatibility
    start = datetime.now()
    counters = {'processed': 0, 'succeeded': 0, 'failed': 0}
    async with async_db_maker() as db:
        buildings = (await db.execute(text("SELECT id, lat, lon FROM buildings WHERE lat IS NOT NULL AND lon IS NOT NULL"))).fetchall()
    logger.info(f"Found {len(buildings)} buildings to process.")
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*(_process_building(row, sem, session, async_db_maker, counters) for row in buildings))
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Weather refresh: processed={counters['processed']}, succeeded={counters['succeeded']}, failed={counters['failed']}, time={elapsed:.1f}s")

# --- Scheduler setup helper ---
def setup_weather_scheduler(async_db_maker):
    """
    Call this from main.py to enable hourly weather refresh scheduling.
    Example:
        from services.weather_service import setup_weather_scheduler
        setup_weather_scheduler(async_session_maker)
    """
    scheduler = AsyncIOScheduler(timezone="Europe/Athens")
    scheduler.add_job(
        refresh_weather_for_all_buildings,
        "cron",
        minute="*/10",
        args=[async_db_maker],
         misfire_grace_time=60
    )
    scheduler.start()
