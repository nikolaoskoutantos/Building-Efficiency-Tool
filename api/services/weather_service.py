"""
Weather service for fetching and storing weather data from external APIs, supporting async scheduled operation.
"""
from datetime import datetime, timezone
    """

# Example: Fetch weather data directly from OpenWeather API (Web2)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

        url = f"{OPEN_METEO_URL}?latitude={lat}&longitude={lon}&current_weather=true"
    """
    Fetch current weather data from OpenWeather API (Web2).
    Returns parsed weather data.
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Example usage:
# result = fetch_weather_openweather(52.52, 13.405)
# print(result)
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

def fetch_weather_data(lat: float, lon: float, service: str = None, forecast: bool = False):
    """
    Fetch weather data from the external adapter (OpenWeather/OpenMeteo).
    Args:
        lat (float): Latitude
        lon (float): Longitude
        service (str): 'openweather', 'openmeteo', or None for both
        forecast (bool): True for forecast, False for current weather
    Returns:
        dict: Weather data response
    """
    url = EXTERNAL_ADAPTER_URL
    headers = {}
    if EXTERNAL_ADAPTER_API_KEY:
        headers["x-api-key"] = EXTERNAL_ADAPTER_API_KEY
    payload = {
        "data": {
            "lat": lat,
            "lon": lon,
            "service": service,
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

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

# Example usage:
# web2_result = fetch_weather_web2(52.52, 13.405, service="openweather")
# web3_result = fetch_weather_web3("Qm...CID...")