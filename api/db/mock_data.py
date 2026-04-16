import datetime
import math
import uuid
import secrets
import bcrypt
from sqlalchemy import and_
from db.connection import SessionLocal
from models.optimization import OptimizationResult

TESTER_CONFIGS = [
    {
        "wallet_address": "0xD2906edA1Abd3e48F2D36B7411b617f7C66408f5",
        "building_name": "Pilot1",
        "building_address": "Athens, Patision",
        "lat": "37.99423304",
        "lon": "23.73211663",
        "public_key": "044caba519022b385cd9b3640b8946c71afdd95c206358504bf15281b8974bc6",
        "label": "Tester1",
        "role": "building_manager",
        "building_did": "0xA",
        "room": "101",
        "zone": "A",
        "central_unit": "CU1",
    },
    {
        "wallet_address": "0x5d79CedDb741E02B0226BdD7ac1AD22F8e81c1AD",
        "building_name": "Tester2_Building",
        "building_address": "Athens, Neos Kosmos",
        "lat": "37.95902423",
        "lon": "23.72964976",
        "public_key": "4c98a03788ad6293c2527463f1e7e0fd3ea3d5e76ad0dce8b8a178095676e439",
        "label": "Tester2",
        "role": "building_manager",
        "building_did": "0xB",
        "room": "201",
        "zone": "B",
        "central_unit": "CU2",
    },
    {
        "wallet_address": "0x38db3F32F4742076904CD5a1C1AE382CF43d3fA9",
        "building_name": "Tester3_Building",
        "building_address": "Florence, Near Rail Station",
        "lat": "43.77373665",
        "lon": "11.24634045",
        "public_key": "fdc6cb2f6f13e2739891c53f0aad80c640e736527fa289585a958e344c9d96a4",
        "label": "Tester3",
        "role": "admin",
        "building_did": "0xC",
        "room": "301",
        "zone": "C",
        "central_unit": "CU3",
    },
    {
        "wallet_address": "0xE8375C8E6eB3c48Dfafb1f573651a6b12aAa273C",
        "building_name": "Pilot1",
        "building_address": "Athens, Patision",
        "lat": "37.99423304",
        "lon": "23.73211663",
        "public_key": "e8375c8e6eb3c48dfafb1f573651a6b12aaa273c",
        "label": "Tester4",
        "role": "building_manager",
        "building_did": "0xA",
        "room": "102",
        "zone": "A",
        "central_unit": "CU1",
    },
]

SENSOR_DEFINITIONS = [
    ("temperature", "celsius"),
    ("presence", "bool"),
    ("energy", "kWh"),
]

MOCK_SERVICES = [
    {
        "name": "Weather Data Service",
        "description": "Provides current and forecast weather data for the QoE platform.",
        "smart_contract_id": "0x1234567890abcdef1234567890abcdef12345678",
        "link_cost": 0.1,
        "callback_wallet_addresses": "0xabcdef1234567890abcdef1234567890abcdef12",
        "input_parameters": {
            "service": "openmeteo",
            "lat": 37.99423304,
            "lon": 23.73211663,
        },
        "knowledge_asset": {
            "data_source": "openmeteo",
            "data_type": "weather",
            "scope": ["current", "forecast"],
        },
    },
    {
        "name": "Environmental Data",
        "description": "Provides environmental and climate-oriented data products for comparison and rating flows.",
        "smart_contract_id": "0x2345678901bcdef12345678901bcdef123456789",
        "link_cost": 0.15,
        "callback_wallet_addresses": "0xbcdef12345678901bcdef12345678901bcdef123",
        "input_parameters": {
            "service": "openweather",
            "lat": 37.99423304,
            "lon": 23.73211663,
        },
        "knowledge_asset": {
            "data_source": "openweather",
            "data_type": "environmental",
            "scope": ["current", "forecast"],
        },
    },
]

OPTIMIZATION_SCENARIOS = [
    {"offset_hours": 2, "baseline": 7.4, "optimized": 6.1, "saving": 1.3, "points": 8.0, "applied": True},
    {"offset_hours": 6, "baseline": 6.9, "optimized": 5.6, "saving": 1.3, "points": 9.0, "applied": True},
    {"offset_hours": 10, "baseline": 7.8, "optimized": 6.2, "saving": 1.6, "points": 11.0, "applied": True},
    {"offset_hours": 14, "baseline": 6.5, "optimized": 5.9, "saving": 0.6, "points": 5.0, "applied": False},
    {"offset_hours": 18, "baseline": 8.1, "optimized": 6.7, "saving": 1.4, "points": 12.0, "applied": True},
    {"offset_hours": 26, "baseline": 7.0, "optimized": 5.8, "saving": 1.2, "points": 8.5, "applied": True},
    {"offset_hours": 32, "baseline": 6.8, "optimized": 6.0, "saving": 0.8, "points": 6.5, "applied": False},
    {"offset_hours": 38, "baseline": 7.6, "optimized": 6.3, "saving": 1.3, "points": 10.5, "applied": True},
    {"offset_hours": 46, "baseline": 8.3, "optimized": 6.6, "saving": 1.7, "points": 13.0, "applied": True},
    {"offset_hours": 54, "baseline": 7.2, "optimized": 5.7, "saving": 1.5, "points": 10.0, "applied": True},
    {"offset_hours": 62, "baseline": 6.7, "optimized": 5.9, "saving": 0.8, "points": 6.0, "applied": False},
    {"offset_hours": 70, "baseline": 7.9, "optimized": 6.4, "saving": 1.5, "points": 11.5, "applied": True},
]


def utc_naive(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(tzinfo=None)


def seed_mock_optimization_results(db, building, user, start, OptimizationResult):
    added = updated = 0

    for index, scenario in enumerate(OPTIMIZATION_SCENARIOS, start=1):
        optimization_time = start + datetime.timedelta(hours=scenario["offset_hours"])
        input_hash = f"mockinputhash{index:03d}"
        output_hash = f"mockoutputhash{index:03d}"

        existing = db.query(OptimizationResult).filter_by(
            building_id=building.id,
            optimization_time=optimization_time,
            input_hash=input_hash,
            output_hash=output_hash,
        ).first()

        payload = {
            "building_id": building.id,
            "user_id": user.id,
            "optimization_time": optimization_time,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "input_data": {
                "setpoint": 21.0 if index % 2 else 22.0,
                "duration": 60,
                "scenario_index": index,
            },
            "output_data": {
                "recommended_operation": [1, 1, 0, 0, 1, 0] if scenario["applied"] else [1, 0, 1, 0, 1, 0],
                "energy_consumption": scenario["optimized"],
            },
            "energy_saving_kwh": scenario["saving"],
            "baseline_consumption_kwh": scenario["baseline"],
            "optimized_consumption_kwh": scenario["optimized"],
            "environmental_points": scenario["points"],
            "notes": (
                "Mock optimization for visualization"
                if scenario["applied"]
                else "Mock optimization for visualization - user did not apply recommendation"
            ),
            "is_optimized": scenario["applied"],
        }

        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(OptimizationResult(**payload))
            added += 1

    db.commit()
    return added, updated


def get_or_create_building(db, config, Building):
    building = db.query(Building).filter_by(name=config["building_name"]).first()
    if not building:
        building = Building(
            did=config["building_did"],
            name=config["building_name"],
            address=config["building_address"],
            lat=config["lat"],
            lon=config["lon"],
        )
        db.add(building)
        db.commit()
        db.refresh(building)
        print(f"🏢 Added building: {config['building_name']}")
    else:
        updated = False
        for field, value in (
            ("address", config["building_address"]),
            ("lat", config["lat"]),
            ("lon", config["lon"]),
            ("did", config["building_did"]),
        ):
            if getattr(building, field) != value:
                setattr(building, field, value)
                updated = True
        if updated:
            db.commit()
        print(f"🏢 Building {config['building_name']} already exists")
    return building


def get_or_create_user(db, config, User):
    normalized_wallet = config["wallet_address"].strip().lower()
    user = db.query(User).filter(User.wallet_address.ilike(normalized_wallet)).first()
    if not user and config.get("public_key"):
        user = db.query(User).filter_by(public_key=config["public_key"]).first()
    if not user:
        user = User(
            wallet_address=normalized_wallet,
            public_key=config["public_key"],
            address=config["building_address"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"👤 Added user: {config['label']}")
    else:
        updated = False
        if user.wallet_address != normalized_wallet:
            user.wallet_address = normalized_wallet
            updated = True
        if user.public_key != config["public_key"]:
            user.public_key = config["public_key"]
            updated = True
        if user.address != config["building_address"]:
            user.address = config["building_address"]
            updated = True
        if updated:
            db.commit()
        print(f"👤 User {config['label']} already exists")
    return user


def ensure_user_building_mapping(db, user, building, role, UserBuilding):
    mapping = db.query(UserBuilding).filter_by(user_id=user.id, building_id=building.id).first()
    if not mapping:
        mapping = UserBuilding(
            user_id=user.id,
            building_id=building.id,
            role=role,
            status="active",
        )
        db.add(mapping)
        db.commit()
        print(f"🔗 Mapped user to {building.name} as {role}")
    else:
        updated = False
        if mapping.role != role:
            mapping.role = role
            updated = True
        if mapping.status != "active":
            mapping.status = "active"
            updated = True
        if updated:
            db.commit()
        print(f"🔗 Mapping already exists for {building.name} as {role}")


def get_or_create_hvac_unit(db, building, config, HVACUnit):
    hvac_unit = db.query(HVACUnit).filter_by(
        building_id=building.id,
        room=config["room"],
        zone=config["zone"],
        central_unit=config["central_unit"],
    ).first()

    if not hvac_unit:
        device_key = str(uuid.uuid4())
        device_secret_hash = bcrypt.hashpw(secrets.token_urlsafe(48).encode(), bcrypt.gensalt()).decode()
        now = datetime.datetime.now().isoformat()
        hvac_unit = HVACUnit(
            building_id=building.id,
            room=config["room"],
            zone=config["zone"],
            central_unit=config["central_unit"],
            device_key=device_key,
            device_secret_hash=device_secret_hash,
            device_secret_rotated_at=now,
            device_revoked_at=None,
        )
        db.add(hvac_unit)
        db.commit()
        db.refresh(hvac_unit)
        print(f"❄️ Created HVAC unit id={hvac_unit.id} for {building.name}")
    else:
        print(f"❄️ HVAC unit already exists id={hvac_unit.id} for {building.name}")
        if not hvac_unit.device_key:
            hvac_unit.device_key = str(uuid.uuid4())
            hvac_unit.device_secret_hash = bcrypt.hashpw(secrets.token_urlsafe(48).encode(), bcrypt.gensalt()).decode()
            hvac_unit.device_secret_rotated_at = datetime.datetime.now().isoformat()
            hvac_unit.device_revoked_at = None
            db.commit()
            print(f"🔑 Updated HVAC unit id={hvac_unit.id} with device credentials")

    return hvac_unit


def get_or_create_sensor(db, building, hvac_unit, config, sensor_type, unit, Sensor):
    sensor = db.query(Sensor).filter_by(
        building_id=building.id,
        hvac_unit_id=hvac_unit.id,
        type=sensor_type,
        room=config["room"],
        zone=config["zone"],
        central_unit=config["central_unit"],
    ).first()
    if not sensor:
        sensor = Sensor(
            building_id=building.id,
            hvac_unit_id=hvac_unit.id,
            type=sensor_type,
            lat=float(building.lat),
            lon=float(building.lon),
            rate_of_sampling=5.0,
            unit=unit,
            room=config["room"],
            zone=config["zone"],
            central_unit=config["central_unit"],
        )
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
        print(f"📟 Created sensor {sensor_type} id={sensor.id} for {building.name}")
    return sensor


def get_or_create_mock_services(db, Service):
    for service_payload in MOCK_SERVICES:
        service = db.query(Service).filter_by(name=service_payload["name"]).first()
        if not service:
            service = Service(**service_payload, is_active=1)
            db.add(service)
            db.commit()
            db.refresh(service)
            print(f"🛰️ Added service: {service_payload['name']}")
            continue

        updated = False
        for field in (
            "description",
            "smart_contract_id",
            "link_cost",
            "callback_wallet_addresses",
            "input_parameters",
            "knowledge_asset",
        ):
            value = service_payload[field]
            if getattr(service, field) != value:
                setattr(service, field, value)
                updated = True

        if not service.is_active:
            service.is_active = 1
            updated = True

        if updated:
            db.commit()
            db.refresh(service)
            print(f"🛰️ Updated service: {service_payload['name']}")
        else:
            print(f"🛰️ Service already exists: {service_payload['name']}")


def seed_building_timeseries(db, building, hvac_unit, sensors, user_id, start, end, WeatherData, SensorData, HVACScheduleInterval):
    time_steps = []
    ts = start
    while ts < end:
        time_steps.append(ts)
        ts += datetime.timedelta(minutes=5)

    db.query(SensorData).filter(
        and_(
            SensorData.sensor_id.in_([sensor.id for sensor in sensors.values()]),
            SensorData.timestamp >= start,
            SensorData.timestamp < end,
        )
    ).delete(synchronize_session=False)

    db.query(HVACScheduleInterval).filter(
        and_(
            HVACScheduleInterval.building_id == building.id,
            HVACScheduleInterval.hvac_unit_id == hvac_unit.id,
            HVACScheduleInterval.start_ts >= start,
            HVACScheduleInterval.start_ts < end,
        )
    ).delete(synchronize_session=False)

    db.commit()

    schedule_rows = []
    sensor_rows = []
    building_phase = (building.id % 5) * 0.4

    for i, t in enumerate(time_steps):
        if t.tzinfo is not None:
            t = t.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        hour_fraction = t.hour + (t.minute / 60.0)
        work_hours = 8 <= hour_fraction <= 18
        midday_setback = 13 <= hour_fraction < 14.5
        is_on = work_hours and not midday_setback
        setpoint = 21.0 if is_on else None

        daily_wave = math.sin((2 * math.pi * i) / 288.0 + building_phase)
        short_wave = math.sin((2 * math.pi * i) / 36.0 + (building_phase * 1.7))
        occupancy_wave = math.sin((2 * math.pi * (hour_fraction - 8)) / 10.0)

        indoor_temp = 22.2 + (0.9 * daily_wave) + (0.25 * short_wave) - (0.35 if is_on else 0.0)
        indoor_temp = max(20.5, min(24.4, indoor_temp))

        occupied = work_hours and occupancy_wave > -0.15
        if 12 <= hour_fraction < 13:
            occupied = occupied and (i % 4 != 0)

        base_energy = 0.18 if occupied else 0.08
        hvac_energy = 0.26 if is_on else 0.0
        modulation = 0.04 * max(short_wave, -0.5)
        energy_kwh = max(0.05, round(base_energy + hvac_energy + modulation, 3))

        schedule_rows.append(
            HVACScheduleInterval(
                building_id=building.id,
                hvac_unit_id=hvac_unit.id,
                start_ts=t,
                end_ts=t + datetime.timedelta(minutes=5),
                is_on=is_on,
                setpoint=setpoint,
                created_by_user_id=user_id,
            )
        )

        sensor_rows.extend(
            [
                SensorData(
                    sensor_id=sensors["temperature"].id,
                    timestamp=t,
                    value=round(indoor_temp, 2),
                    measurement_type="temperature",
                    unit="celsius",
                ),
                SensorData(
                    sensor_id=sensors["presence"].id,
                    timestamp=t,
                    value=1.0 if occupied else 0.0,
                    measurement_type="presence",
                    unit="bool",
                ),
                SensorData(
                    sensor_id=sensors["energy"].id,
                    timestamp=t,
                    value=energy_kwh,
                    measurement_type="energy",
                    unit="kWh",
                ),
            ]
        )

    db.bulk_save_objects(schedule_rows)
    db.bulk_save_objects(sensor_rows)
    db.commit()

    return len(time_steps), 0, len(schedule_rows), len(sensor_rows)


def insert_mock_data():
    db = SessionLocal()
    try:
        from models.hvac_models import Building, User, UserBuilding, HVACScheduleInterval
        from models.hvac_unit import HVACUnit
        from models.sensor import Sensor
        from models.sensordata import WeatherData, SensorData
        from models.service import Service

        print("🔄 Checking and initializing mock data...")

        get_or_create_mock_services(db, Service)

        days = 3
        now_utc = datetime.datetime.utcnow()
        start = utc_naive(datetime.datetime(now_utc.year, now_utc.month, now_utc.day, 0, 0, 0))
        end = start + datetime.timedelta(days=days)

        total_steps = total_weather = total_schedules = total_sensor_rows = 0
        primary_building = None
        primary_user = None

        for config in TESTER_CONFIGS:
            building = get_or_create_building(db, config, Building)
            user = get_or_create_user(db, config, User)
            ensure_user_building_mapping(db, user, building, config["role"], UserBuilding)
            hvac_unit = get_or_create_hvac_unit(db, building, config, HVACUnit)
            sensors = {
                sensor_type: get_or_create_sensor(db, building, hvac_unit, config, sensor_type, unit, Sensor)
                for sensor_type, unit in SENSOR_DEFINITIONS
            }

            print(f"🧹 Refreshing weather/sensor/schedule data for {building.name}")
            steps, weather_count, schedule_count, sensor_count = seed_building_timeseries(
                db,
                building,
                hvac_unit,
                sensors,
                user.id,
                start,
                end,
                WeatherData,
                SensorData,
                HVACScheduleInterval,
            )
            total_steps += steps
            total_weather += weather_count
            total_schedules += schedule_count
            total_sensor_rows += sensor_count

            if config["building_name"] == "Pilot1":
                primary_building = building
                primary_user = user

        if primary_building is None or primary_user is None:
            raise RuntimeError("Primary Pilot1 tester configuration is missing.")

        added_opt_results, updated_opt_results = seed_mock_optimization_results(
            db,
            primary_building,
            primary_user,
            start,
            OptimizationResult,
        )
        print(
            f"📝 Seeded optimization results for visualization "
            f"(added={added_opt_results}, updated={updated_opt_results})"
        )

        print(
            f"✅ Inserted mock data: {total_steps} timesteps, "
            f"{total_weather} weather rows, {total_schedules} schedule rows, "
            f"{total_sensor_rows} sensor rows across {len(TESTER_CONFIGS)} tester scenarios"
        )

    except Exception as e:
        db.rollback()
        print(f"❌ Error during mock data initialization: {str(e)}")
        raise
    finally:
        db.close()
