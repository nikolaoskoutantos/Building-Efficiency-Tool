"""
Weather service for fetching and storing weather data from external APIs, supporting async scheduled operation.
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # Only import if/when APScheduler is installed

# Load .env for config-driven API selection
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))
MODE = os.getenv('MODE', 'Web2')
BASE_URL = os.getenv('WEATHER_BASE_URL', 'https://api.openweathermap.org/data/2.5/weather')
API_KEY = os.getenv('WEATHER_API_KEY')
BEARER_TOKEN = os.getenv('WEATHER_BEARER_TOKEN')
UNITS = os.getenv('WEATHER_UNITS', 'metric')
IPFS_GATEWAY = os.getenv('IPFS_GATEWAY', 'https://ipfs.io/ipfs/')

# Load from .env or use defaults
OPEN_METEO_URL = os.getenv('OPEN_METEO_URL', 'https://api.open-meteo.com/v1/forecast')
MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', 20))
RETRY_LIMIT = int(os.getenv('RETRY_LIMIT', 2))

logger = logging.getLogger("weather_scheduler")

async def fetch_weather(lat, lon, session):
    """
    Fetch weather from the configured provider (OpenWeatherMap or Open-Meteo).
    """
    if MODE == 'Web2':
        params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": UNITS
        }
        headers = {}
        if BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
        url = BASE_URL
    else:
        # Open-Meteo with current=...
        url = OPEN_METEO_URL
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,precipitation,weather_code",
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
    # Support both OpenWeatherMap and Open-Meteo response formats
    if 'current' in weather_json:
        # Open-Meteo
        current = weather_json.get("current", {})
        timestamp = current.get("time")
        if timestamp:
            timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        temperature = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        pressure = current.get("surface_pressure")
        wind_speed = current.get("wind_speed_10m")
        wind_direction = current.get("wind_direction_10m")
        precipitation = current.get("precipitation")
        weather_code = current.get("weather_code")
        weather_description = str(weather_code) if weather_code is not None else None
    else:
        # OpenWeatherMap
        timestamp = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        temperature = weather_json.get("main", {}).get("temp")
        humidity = weather_json.get("main", {}).get("humidity")
        pressure = weather_json.get("main", {}).get("pressure")
        wind_speed = weather_json.get("wind", {}).get("speed")
        wind_direction = weather_json.get("wind", {}).get("deg")
        precipitation = weather_json.get("rain", {}).get("1h", 0)
        weather_description = weather_json.get("weather", [{}])[0].get("description")

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
        # Convert ISO string timestamp to UTC-aware datetime if needed
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
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

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch bulk weather: {e}")
            return

    # Open-Meteo returns a list of results, one per location
    if not isinstance(data, list):
        logger.error("Unexpected Open-Meteo response format (expected list).")
        return

    async with async_db_maker() as db:
        await _insert_bulk_weather_data(db, data)
    logger.info(f"Bulk weather data inserted for {len(data)} locations.")


async def _process_building(row, sem, session, async_db_maker, counters):
    async with sem:
        lat, lon = float(row.lat), float(row.lon)
        weather = await fetch_weather(lat, lon, session)
        counters['processed'] += 1
        if weather:
            try:
                async with async_db_maker() as db2:
                    await upsert_weather(db2, lat, lon, weather)
                counters['succeeded'] += 1
            except Exception as e:
                logger.error(f"DB upsert failed for ({lat}, {lon}): {e}")
                counters['failed'] += 1
        else:
            counters['failed'] += 1

async def refresh_weather_for_all_buildings(async_db_maker):
    from models.building import Building  # Adjust import as needed
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
    import asyncio
    scheduler = AsyncIOScheduler(timezone="Europe/Athens")
    scheduler.add_job(
        lambda: asyncio.create_task(refresh_weather_for_all_buildings(async_db_maker)),
        "cron",
        hour="*"
    )
    scheduler.start()