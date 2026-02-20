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

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MAX_CONCURRENCY = 20
RETRY_LIMIT = 2

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
        # Default to Open-Meteo for Web3 or fallback
        url = f"{OPEN_METEO_URL}?latitude={lat}&longitude={lon}&current_weather=true"
        params = None
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
    if 'current_weather' in weather_json:
        # Open-Meteo
        current = weather_json.get("current_weather", {})
        timestamp = current.get("time")
        if not timestamp:
            timestamp = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        else:
            timestamp = datetime.fromisoformat(timestamp)
        temperature = current.get("temperature")
        wind_speed = current.get("windspeed")
        wind_direction = current.get("winddirection")
        humidity = None
        pressure = None
        precipitation = None
        weather_description = None
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

async def refresh_weather_for_all_buildings(async_db_maker):
    from models.building import Building  # Adjust import as needed
    start = datetime.now()
    processed = succeeded = failed = 0
    async with async_db_maker() as db:
        buildings = (await db.execute(text("SELECT id, lat, lon FROM buildings WHERE lat IS NOT NULL AND lon IS NOT NULL"))).fetchall()
    logger.info(f"Found {len(buildings)} buildings to process.")
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with aiohttp.ClientSession() as session:
        async def process_building(row):
            nonlocal processed, succeeded, failed
            async with sem:
                lat, lon = float(row.lat), float(row.lon)
                weather = await fetch_weather(lat, lon, session)
                processed += 1
                if weather:
                    try:
                        async with async_db_maker() as db2:
                            await upsert_weather(db2, lat, lon, weather)
                        succeeded += 1
                    except Exception as e:
                        logger.error(f"DB upsert failed for ({lat}, {lon}): {e}")
                        failed += 1
                else:
                    failed += 1
        await asyncio.gather(*(process_building(row) for row in buildings))
    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Weather refresh: processed={processed}, succeeded={succeeded}, failed={failed}, time={elapsed:.1f}s")

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