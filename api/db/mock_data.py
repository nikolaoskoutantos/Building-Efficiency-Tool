import datetime
import math
import uuid
import secrets
import bcrypt
from sqlalchemy import and_
from db.connection import SessionLocal
from models.optimization import OptimizationResult
from utils.unit_resolver import canonicalize_unit

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
        "skip_primary_device": True,
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
        "extra_devices": [
            {
                "room": "Postaz di Lavoro 26-27",
                "zone": "StA",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "temperature", "unit": "celsius", "payload_path": "0/0/7", "label": "Temp Att StA Postaz di Lavoro 26-27"},
                    {"type": "humidity", "unit": "%", "payload_path": "0/0/8", "label": "Umr Att StA Postaz di Lavoro 26-27"},
                ],
            },
            {
                "room": "Locale 29-30",
                "zone": "StB",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "temperature", "unit": "celsius", "payload_path": "0/0/9", "label": "Temp Att StB Locale 29-30"},
                    {"type": "humidity", "unit": "%", "payload_path": "0/0/10", "label": "Umr Att StB Locale 29-30"},
                ],
            },
            {
                "room": "Postaz di Lavoro 24-25",
                "zone": "StC",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "temperature", "unit": "celsius", "payload_path": "0/0/11", "label": "Temp Att StC Postaz di Lavoro 24-25"},
                    {"type": "humidity", "unit": "%", "payload_path": "0/0/12", "label": "Umr Att StC Postaz di Lavoro 24-25"},
                    {"type": "power", "unit": "W", "payload_path": "0/0/13", "label": "W-Postaz di Lavoro 24-25"},
                    {"type": "current", "unit": "A", "payload_path": "0/0/14", "label": "A-Postaz di Lavoro 24-25"},
                    {"type": "voltage", "unit": "V", "payload_path": "0/0/15", "label": "V-Postaz di Lavoro 24-25"},
                ],
            },
            {
                "room": "Postaz di Lavoro 26-29",
                "zone": "Workstations",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "power", "unit": "W", "payload_path": "0/0/16", "label": "W-Postaz di Lavoro 26-29"},
                    {"type": "current", "unit": "A", "payload_path": "0/0/17", "label": "A-Postaz di Lavoro 26-29"},
                    {"type": "voltage", "unit": "V", "payload_path": "0/0/18", "label": "V-Postaz di Lavoro 26-29"},
                ],
            },
            {
                "room": "CDZ",
                "zone": "HVAC",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "power", "unit": "W", "payload_path": "0/0/19", "label": "W-CDZ"},
                    {"type": "current", "unit": "A", "payload_path": "0/0/20", "label": "A-CDZ"},
                    {"type": "voltage", "unit": "V", "payload_path": "0/0/21", "label": "V-CDZ"},
                ],
            },
            {
                "room": "Illum Locale 24-25",
                "zone": "Lighting",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "power", "unit": "W", "payload_path": "0/0/22", "label": "W-Illum Locale 24-25"},
                    {"type": "current", "unit": "A", "payload_path": "0/0/23", "label": "A-Illum Locale 24-25"},
                    {"type": "voltage", "unit": "V", "payload_path": "0/0/24", "label": "V-Illum Locale 24-25"},
                ],
            },
            {
                "room": "Illum Locale 26-27",
                "zone": "Lighting",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "power", "unit": "W", "payload_path": "0/0/25", "label": "W-Illum Locale 26-27"},
                    {"type": "current", "unit": "A", "payload_path": "0/0/26", "label": "A-Illum Locale 26-27"},
                    {"type": "voltage", "unit": "V", "payload_path": "0/0/27", "label": "V-Illum Locale 26-27"},
                ],
            },
            {
                "room": "Illum Locale 29-30",
                "zone": "Lighting",
                "central_unit": "Florence KNX",
                "seed_timeseries": False,
                "sensors": [
                    {"type": "power", "unit": "W", "payload_path": "0/0/28", "label": "W-Illum Locale 29-30"},
                    {"type": "current", "unit": "A", "payload_path": "0/0/29", "label": "A-Illum Locale 29-30"},
                    {"type": "voltage", "unit": "V", "payload_path": "0/0/30", "label": "V-Illum Locale 29-30"},
                ],
            },
        ],
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
        "skip_primary_device": True,
    },
]

# Canonical sensor type → unit symbol mapping used for generic tester buildings.
# Symbols must match entries in the sensor_units table (seeded at cold-start).
SENSOR_DEFINITIONS = [
    ("temperature", "°C"),
    ("presence", "bool"),
    ("energy", "kWh"),
]

# All canonical sensor units. Must stay in sync with schema / migration seed data.
CANONICAL_UNITS = [
    # symbol, quantity, display_name, aliases, si_symbol, conversion_factor, aggregation_method
    ("°C",   "temperature",   "Degrees Celsius",     ["celsius","degc","deg_c","degree_celsius","degrees_celsius","c"],      "K",   None,        "mean"),
    ("°F",   "temperature",   "Degrees Fahrenheit",  ["fahrenheit","degf","deg_f","degree_fahrenheit"],                      "K",   None,        "mean"),
    ("K",    "temperature",   "Kelvin",              ["kelvin"],                                                              "K",   1.0,         "mean"),
    ("%",    "ratio",         "Percent",             ["%rh","pct","percent","humidity_pct","humidity_%"],                    None,  0.01,        "mean"),
    ("W",    "power",         "Watt",                ["watt","watts"],                                                        "W",   1.0,         "mean"),
    ("kW",   "power",         "Kilowatt",            ["kilowatt","kilowatts"],                                                "W",   1000.0,      "mean"),
    ("kWh",  "energy",        "Kilowatt-hour",       ["kwh","kilowatt_hour","kilowatt_hours","kilowatthour"],                "J",   3_600_000.0, "sum"),
    ("Wh",   "energy",        "Watt-hour",           ["wh","watt_hour","watthour"],                                          "J",   3_600.0,     "sum"),
    ("A",    "current",       "Ampere",              ["ampere","amp","amps","amperes"],                                      "A",   1.0,         "mean"),
    ("V",    "voltage",       "Volt",                ["volt","volts"],                                                        "V",   1.0,         "mean"),
    ("ppm",  "concentration", "Parts per million",   ["parts_per_million","co2_ppm"],                                        None,  None,        "mean"),
    ("hPa",  "pressure",      "Hectopascal",         ["hpa","hectopascal","mbar","millibar","mb"],                          "Pa",  100.0,       "mean"),
    ("Pa",   "pressure",      "Pascal",              ["pascal","pa"],                                                         "Pa",  1.0,         "mean"),
    ("m/s",  "speed",         "Metres per second",   ["m_s","ms","meters_per_second","metres_per_second","meter_per_second"], "m/s", 1.0,         "mean"),
    ("mm",   "length",        "Millimetre",          ["millimeter","millimetre","millimeters","millimetres"],                "m",   0.001,       "sum"),
    ("bool", "dimensionless", "Boolean",             ["boolean","on_off","binary","true_false"],                             None,  None,        "majority"),
    ("lx",   "illuminance",   "Lux",                 ["lux"],                                                                 "lx",  1.0,         "mean"),
    ("dB",   "sound_level",   "Decibel",             ["decibel","decibels"],                                                 None,  None,        "mean"),
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
    unit_name = config.get("central_unit") or config.get("name", "default-unit")
    hvac_unit = db.query(HVACUnit).filter_by(
        building_id=building.id,
        name=unit_name,
    ).first()

    if not hvac_unit:
        device_key = str(uuid.uuid4())
        device_secret_hash = bcrypt.hashpw(secrets.token_urlsafe(48).encode(), bcrypt.gensalt()).decode()
        now = datetime.datetime.now().isoformat()
        hvac_unit = HVACUnit(
            building_id=building.id,
            name=unit_name,
            unit_type=config.get("unit_type", "unknown"),
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


def seed_sensor_units(db, SensorUnit):
    """Ensure all canonical sensor units exist in the DB (idempotent)."""
    existing_rows = {row.symbol: row for row in db.query(SensorUnit).all()}
    existing = set(existing_rows.keys())
    new_rows = [
        SensorUnit(
            symbol=symbol,
            quantity=quantity,
            display_name=display_name,
            aliases=aliases,
            si_symbol=si_symbol,
            conversion_factor=conversion_factor,
            aggregation_method=aggregation_method,
        )
        for symbol, quantity, display_name, aliases, si_symbol, conversion_factor, aggregation_method
        in CANONICAL_UNITS
        if symbol not in existing
    ]
    updated = 0
    for symbol, quantity, display_name, aliases, si_symbol, conversion_factor, aggregation_method in CANONICAL_UNITS:
        row = existing_rows.get(symbol)
        if not row:
            continue
        if getattr(row, "aggregation_method", None) != aggregation_method:
            row.aggregation_method = aggregation_method
            updated += 1
    if new_rows:
        db.bulk_save_objects(new_rows)
    if new_rows or updated:
        db.commit()
        print(f"📐 Seeded {len(new_rows)} canonical sensor unit(s), updated {updated}")
    else:
        print("📐 Sensor units already seeded")


def get_or_create_sensor(db, building, hvac_unit, config, sensor_type, unit, Sensor, payload_path=None, label=None, zone_id=None, is_controllable=False, command_payload_template=None):
    # Prefer explicit label, then a payload_path-based slug, then type-id fallback.
    # This prevents name collisions when multiple sensors of the same type exist
    # on the same HVACUnit (e.g. Florence KNX rooms all share one unit).
    if label:
        sensor_name = label
    elif payload_path:
        sensor_name = f"{sensor_type}-{payload_path.replace('/', '_')}-{hvac_unit.id}"
    else:
        sensor_name = f"{sensor_type}-{hvac_unit.id}"

    # Resolve unit string → canonical SensorUnit row (if table exists)
    canonical_unit, unit_id = canonicalize_unit(unit, db)

    if payload_path:
        sensor = db.query(Sensor).filter_by(
            building_id=building.id,
            hvac_unit_id=hvac_unit.id,
            payload_path=payload_path,
        ).first()
    else:
        sensor = db.query(Sensor).filter_by(
            building_id=building.id,
            hvac_unit_id=hvac_unit.id,
            sensor_type=sensor_type,
        ).first()

    if not sensor:
        sensor = Sensor(
            building_id=building.id,
            hvac_unit_id=hvac_unit.id,
            name=sensor_name,
            sensor_type=sensor_type,
            unit=canonical_unit,
            unit_id=unit_id,
            payload_path=payload_path,
            zone_id=zone_id,
            is_controllable=is_controllable,
            command_payload_template=command_payload_template,
        )
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
        print(f"📟 Created sensor {sensor_type} ({canonical_unit}) id={sensor.id} for {building.name}")
    else:
        updated = False
        for field, value in (
            ("sensor_type", sensor_type),
            ("unit", canonical_unit),
            ("unit_id", unit_id),
            ("payload_path", payload_path),
            ("is_controllable", is_controllable),
            ("command_payload_template", command_payload_template),
        ):
            if getattr(sensor, field) != value:
                setattr(sensor, field, value)
                updated = True
        if updated:
            db.commit()
    return sensor


def build_default_device_config(config):
    return {
        "room": config["room"],
        "zone": config["zone"],
        "central_unit": config["central_unit"],
        "seed_timeseries": True,
        "sensors": [
            {"type": sensor_type, "unit": unit}
            for sensor_type, unit in SENSOR_DEFINITIONS
        ],
    }


def iter_config_devices(config):
    if not config.get("skip_primary_device", False):
        yield build_default_device_config(config)
    for device_config in config.get("extra_devices", []):
        yield device_config


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


# ---------------------------------------------------------------------------
# Topology helpers: rooms, thermostats, zone↔room and zone↔thermostat links
# ---------------------------------------------------------------------------

def get_or_create_room(db, building, room_name, Room):
    room = db.query(Room).filter_by(building_id=building.id, name=room_name).first()
    if not room:
        room = Room(building_id=building.id, name=room_name)
        db.add(room)
        db.commit()
        db.refresh(room)
        print(f"🚪 Created room '{room_name}' for {building.name}")
    return room


def get_or_create_thermostat(db, building, thermostat_name, Thermostat, is_controllable=False, external_bms_id=None):
    thermostat = db.query(Thermostat).filter_by(building_id=building.id, name=thermostat_name).first()
    if not thermostat:
        thermostat = Thermostat(
            building_id=building.id,
            name=thermostat_name,
            is_controllable=is_controllable,
            external_bms_id=external_bms_id,
        )
        db.add(thermostat)
        db.commit()
        db.refresh(thermostat)
        print(f"🌡️  Created thermostat '{thermostat_name}' (controllable={is_controllable}, bms_id={external_bms_id}) for {building.name}")
    else:
        updated = False
        if thermostat.is_controllable != is_controllable:
            thermostat.is_controllable = is_controllable
            updated = True
        if external_bms_id and thermostat.external_bms_id != external_bms_id:
            thermostat.external_bms_id = external_bms_id
            updated = True
        if updated:
            db.commit()
    return thermostat


def get_or_create_zone_room_link(db, zone, room, ZoneRoom):
    link = db.query(ZoneRoom).filter_by(zone_id=zone.id, room_id=room.id).first()
    if not link:
        link = ZoneRoom(zone_id=zone.id, room_id=room.id, weight=1.0)
        db.add(link)
        db.commit()
        print(f"🔗 Linked room '{room.name}' to zone '{zone.name}'")
    return link


def get_or_create_zone_thermostat_link(db, zone, thermostat, ZoneThermostat):
    link = db.query(ZoneThermostat).filter_by(zone_id=zone.id, thermostat_id=thermostat.id).first()
    if not link:
        link = ZoneThermostat(zone_id=zone.id, thermostat_id=thermostat.id, role="primary", control_weight=1.0)
        db.add(link)
        db.commit()
        print(f"🔗 Linked thermostat '{thermostat.name}' to zone '{zone.name}'")
    return link


def get_or_create_zone(db, building, zone_name, HVACZone):
    zone = db.query(HVACZone).filter_by(building_id=building.id, name=zone_name).first()
    if not zone:
        zone = HVACZone(building_id=building.id, name=zone_name, zone_type="thermal")
        db.add(zone)
        db.commit()
        db.refresh(zone)
        print(f"🗺️  Created zone '{zone_name}' for {building.name}")
    else:
        print(f"🗺️  Zone '{zone_name}' already exists for {building.name}")
    return zone


def get_or_create_zone_hvac_link(db, zone, hvac_unit, ZoneHVACUnit):
    link = db.query(ZoneHVACUnit).filter_by(zone_id=zone.id, hvac_unit_id=hvac_unit.id).first()
    if not link:
        link = ZoneHVACUnit(
            zone_id=zone.id,
            hvac_unit_id=hvac_unit.id,
            role="serves",
            allocation_weight=1.0,
        )
        db.add(link)
        db.commit()
        print(f"🔗 Linked HVAC unit id={hvac_unit.id} to zone '{zone.name}'")
    return link


def seed_zone_schedule(db, zone, start, ZoneSchedule, ZoneScheduleInterval):
    """
    Creates three schedules for the zone:
      1. Weekday Comfort   — Mon-Fri, three intervals (work / evening setback / night off)
      2. Weekend Setback   — Sat-Sun, full-day off/low setpoint
      3. User Override     — manual override on seeded day 2, 10:00-14:00 (setpoint 23 °C)
    All are idempotent — skipped if the schedule name already exists for this zone.
    """
    # ------------------------------------------------------------------ #
    # 1. Weekday Comfort schedule                                          #
    # ------------------------------------------------------------------ #
    weekday_sched = db.query(ZoneSchedule).filter_by(
        zone_id=zone.id, name="Weekday Comfort"
    ).first()
    if not weekday_sched:
        weekday_sched = ZoneSchedule(
            zone_id=zone.id,
            schedule_type="comfort",
            name="Weekday Comfort",
        )
        db.add(weekday_sched)
        db.commit()
        db.refresh(weekday_sched)

        intervals = []
        for day in range(1, 6):  # 1=Monday … 5=Friday
            intervals += [
                # Occupied work hours
                ZoneScheduleInterval(
                    schedule_id=weekday_sched.id,
                    day_of_week=day,
                    start_time=datetime.time(8, 0),
                    end_time=datetime.time(18, 0),
                    target_setpoint_c=21.5,
                    min_setpoint_c=20.0,
                    max_setpoint_c=24.0,
                    expected_occupancy=10,
                    hvac_mode="auto",
                ),
                # Evening setback
                ZoneScheduleInterval(
                    schedule_id=weekday_sched.id,
                    day_of_week=day,
                    start_time=datetime.time(18, 0),
                    end_time=datetime.time(23, 0),
                    target_setpoint_c=18.0,
                    min_setpoint_c=16.0,
                    max_setpoint_c=26.0,
                    expected_occupancy=0,
                    hvac_mode="auto",
                ),
                # Night off
                ZoneScheduleInterval(
                    schedule_id=weekday_sched.id,
                    day_of_week=day,
                    start_time=datetime.time(0, 0),
                    end_time=datetime.time(8, 0),
                    target_setpoint_c=16.0,
                    min_setpoint_c=14.0,
                    max_setpoint_c=28.0,
                    expected_occupancy=0,
                    hvac_mode="off",
                ),
            ]
        db.bulk_save_objects(intervals)
        db.commit()
        print(f"📅 Created Weekday Comfort schedule for zone '{zone.name}'")

    # ------------------------------------------------------------------ #
    # 2. Weekend Setback schedule                                          #
    # ------------------------------------------------------------------ #
    weekend_sched = db.query(ZoneSchedule).filter_by(
        zone_id=zone.id, name="Weekend Setback"
    ).first()
    if not weekend_sched:
        weekend_sched = ZoneSchedule(
            zone_id=zone.id,
            schedule_type="comfort",
            name="Weekend Setback",
        )
        db.add(weekend_sched)
        db.commit()
        db.refresh(weekend_sched)

        weekend_intervals = []
        for day in (6, 7):  # 6=Saturday, 7=Sunday
            weekend_intervals.append(
                ZoneScheduleInterval(
                    schedule_id=weekend_sched.id,
                    day_of_week=day,
                    start_time=datetime.time(0, 0),
                    end_time=datetime.time(23, 59),
                    target_setpoint_c=16.0,
                    min_setpoint_c=14.0,
                    max_setpoint_c=28.0,
                    expected_occupancy=0,
                    hvac_mode="off",
                )
            )
        db.bulk_save_objects(weekend_intervals)
        db.commit()
        print(f"📅 Created Weekend Setback schedule for zone '{zone.name}'")

    # ------------------------------------------------------------------ #
    # 3. Simulated user manual override — day 2, 10:00-14:00              #
    # User felt too warm and raised setpoint to 23 °C                     #
    # ------------------------------------------------------------------ #
    override_sched = db.query(ZoneSchedule).filter_by(
        zone_id=zone.id, name="User Override Day 2"
    ).first()
    if not override_sched:
        override_day = start + datetime.timedelta(days=1)
        override_sched = ZoneSchedule(
            zone_id=zone.id,
            schedule_type="manual_override",
            name="User Override Day 2",
            valid_from=override_day.replace(hour=10, minute=0, second=0, microsecond=0),
            valid_to=override_day.replace(hour=14, minute=0, second=0, microsecond=0),
        )
        db.add(override_sched)
        db.commit()
        db.refresh(override_sched)

        db.add(ZoneScheduleInterval(
            schedule_id=override_sched.id,
            day_of_week=None,   # override applies regardless of day-of-week
            start_time=datetime.time(10, 0),
            end_time=datetime.time(14, 0),
            target_setpoint_c=23.0,
            min_setpoint_c=22.0,
            max_setpoint_c=25.0,
            expected_occupancy=5,
            hvac_mode="cooling",
        ))
        db.commit()
        print(f"📅 Created User Override schedule for zone '{zone.name}'")


def seed_zone_states(db, zone, hvac_unit, start, end, ZoneState):
    """
    Seeds zone_states for every 5-min bucket in [start, end).
    Simulates:
      - Measured temperature  (same formula as sensor seeding)
      - Active setpoint       (follows weekday / weekend / user-override logic)
      - Humidity (40-65 %)
      - CO2 ppm (400 base, rises when occupied)
      - Occupancy flag
      - HVAC status + controller output %
    Deletes existing rows in the window before re-seeding.
    """
    db.query(ZoneState).filter(
        ZoneState.zone_id == zone.id,
        ZoneState.ts >= start,
        ZoneState.ts < end,
    ).delete(synchronize_session=False)
    db.commit()

    unit_phase     = (zone.building_id % 5) * 0.4 + (hvac_unit.id % 7) * 0.45
    unit_base_temp = 22.2 + 0.4 * (hvac_unit.id % 3)
    time_steps = []
    ts = start
    while ts < end:
        time_steps.append(ts)
        ts += datetime.timedelta(minutes=5)

    state_rows = []
    for i, t in enumerate(time_steps):
        # Normalise to naive UTC (consistent with rest of mock data)
        t_plain = t.replace(tzinfo=None) if t.tzinfo else t

        hour_fraction = t_plain.hour + (t_plain.minute / 60.0)
        day_of_week = t_plain.weekday()      # 0=Mon … 6=Sun
        is_weekday = day_of_week < 5
        work_hours = 8 <= hour_fraction < 18
        midday_setback = 13 <= hour_fraction < 14.5
        is_on = is_weekday and work_hours and not midday_setback

        day_offset = (t_plain.date() - start.date()).days
        user_override = (day_offset == 1 and 10 <= hour_fraction < 14)

        # Active setpoint — mirrors schedule definitions above
        if user_override:
            setpoint = 23.0
        elif is_on:
            setpoint = 21.5
        elif is_weekday and work_hours:
            setpoint = 18.0     # evening setback
        else:
            setpoint = 16.0     # night / weekend

        # Temperature simulation
        daily_wave = math.sin((2 * math.pi * i) / 288.0 + unit_phase)
        short_wave  = math.sin((2 * math.pi * i) / 36.0  + unit_phase * 1.7)
        measured_temp = unit_base_temp + 0.9 * daily_wave + 0.25 * short_wave - (0.35 if is_on else 0.0)
        if user_override:
            measured_temp += 1.2   # room warmer during override
        measured_temp = round(max(20.5, min(25.2, measured_temp)), 2)

        delta_t = round(measured_temp - setpoint, 2)

        # Humidity 40-65 %
        humidity = 45.0 + 10.0 * math.sin((2 * math.pi * i) / 288.0 + 1.2)
        if is_on:
            humidity += 5.0
        humidity = round(max(35.0, min(65.0, humidity)), 1)

        # CO2 — base 420 ppm, +280 when occupied
        occupancy_wave = math.sin((2 * math.pi * (hour_fraction - 8)) / 10.0)
        occupied = is_on and occupancy_wave > -0.15
        if 12 <= hour_fraction < 13:
            occupied = occupied and (i % 4 != 0)
        co2 = 420.0 + (280.0 if occupied else 0.0) + 40.0 * short_wave
        co2 = round(max(400.0, min(1200.0, co2)), 0)

        # HVAC status + controller output
        if not is_on and not user_override:
            hvac_status = "off"
            ctrl_output = 0.0
        elif delta_t > 0.5:
            hvac_status = "cooling"
            ctrl_output = round(min(100.0, delta_t * 25.0), 1)
        elif delta_t < -0.5:
            hvac_status = "heating"
            ctrl_output = round(min(100.0, abs(delta_t) * 25.0), 1)
        else:
            hvac_status = "idle"
            ctrl_output = 0.0

        state_rows.append(ZoneState(
            zone_id=zone.id,
            ts=t,
            measured_temp_c=measured_temp,
            setpoint_c=round(setpoint, 1),
            delta_t_c=delta_t,
            humidity_pct=humidity,
            co2_ppm=co2,
            occupancy=1 if occupied else 0,
            hvac_unit_id=hvac_unit.id,
            controller_output_pct=ctrl_output,
            hvac_status=hvac_status,
        ))

    db.bulk_save_objects(state_rows)
    db.commit()
    print(f"🌡️  Seeded {len(state_rows)} zone state rows for zone '{zone.name}'")
    return len(state_rows)


def seed_building_timeseries(db, building, hvac_unit, sensors, user_id, start, end, WeatherData, SensorData):
    time_steps = []
    ts = start
    while ts < end:
        time_steps.append(ts)
        ts += datetime.timedelta(minutes=5)

    db.query(SensorData).filter(
        and_(
            SensorData.sensor_id.in_([sensor.id for sensor in sensors.values()]),
            SensorData.ts >= start,
            SensorData.ts < end,
        )
    ).delete(synchronize_session=False)

    db.commit()

    sensor_rows = []
    unit_phase    = (building.id % 5) * 0.4 + (hvac_unit.id % 7) * 0.45
    unit_base_temp = 22.2 + 0.4 * (hvac_unit.id % 3)   # 22.2 / 22.6 / 23.0 per unit

    for i, t in enumerate(time_steps):
        if t.tzinfo is not None:
            t = t.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        hour_fraction = t.hour + (t.minute / 60.0)
        work_hours = 8 <= hour_fraction <= 18
        midday_setback = 13 <= hour_fraction < 14.5
        is_on = work_hours and not midday_setback

        daily_wave = math.sin((2 * math.pi * i) / 288.0 + unit_phase)
        short_wave = math.sin((2 * math.pi * i) / 36.0 + (unit_phase * 1.7))
        occupancy_wave = math.sin((2 * math.pi * (hour_fraction - 8)) / 10.0)

        indoor_temp = unit_base_temp + (0.9 * daily_wave) + (0.25 * short_wave) - (0.35 if is_on else 0.0)
        indoor_temp = max(20.5, min(24.8, indoor_temp))

        occupied = work_hours and occupancy_wave > -0.15
        if 12 <= hour_fraction < 13:
            occupied = occupied and (i % 4 != 0)

        base_energy = 0.18 if occupied else 0.08
        hvac_energy = 0.26 if is_on else 0.0
        modulation = 0.04 * max(short_wave, -0.5)
        energy_kwh = max(0.05, round(base_energy + hvac_energy + modulation, 3))

        temp_sensor = sensors.get("temperature") or sensors.get("thermostat")
        if temp_sensor:
            sensor_rows.append(SensorData(
                sensor_id=temp_sensor.id,
                building_id=building.id,
                ts=t,
                value=round(indoor_temp, 2),
                quality="valid",
            ))
        if "presence" in sensors:
            sensor_rows.append(SensorData(
                sensor_id=sensors["presence"].id,
                building_id=building.id,
                ts=t,
                value=1.0 if occupied else 0.0,
                quality="valid",
            ))
        if "energy" in sensors:
            sensor_rows.append(SensorData(
                sensor_id=sensors["energy"].id,
                building_id=building.id,
                ts=t,
                value=energy_kwh,
                quality="valid",
            ))

    db.bulk_save_objects(sensor_rows)
    db.commit()

    return len(time_steps), 0, 0, len(sensor_rows)


def insert_mock_data():
    db = SessionLocal()
    try:
        from models.hvac_models import Building, User, UserBuilding
        from models.hvac_unit import HVACUnit
        from models.sensor import Sensor
        from models.sensor_unit import SensorUnit
        from models.sensordata import WeatherData, SensorData
        from models.service import Service
        from models.topology import HVACZone, ZoneHVACUnit, Room, ZoneRoom
        from models.thermostat import Thermostat, ZoneThermostat
        from models.zone_schedule import ZoneSchedule, ZoneScheduleInterval
        from models.zone_state import ZoneState

        print("🔄 Checking and initializing mock data...")

        # Seed canonical unit registry first — sensors depend on it
        seed_sensor_units(db, SensorUnit)

        get_or_create_mock_services(db, Service)

        now_utc = datetime.datetime.utcnow()
        today_midnight = utc_naive(datetime.datetime(now_utc.year, now_utc.month, now_utc.day, 0, 0, 0))
        start = today_midnight - datetime.timedelta(days=2)   # 2 days of history
        end   = today_midnight + datetime.timedelta(days=2)   # 2 days ahead for forecast

        total_steps = total_weather = total_schedules = total_sensor_rows = total_zone_state_rows = 0
        primary_building = None
        primary_user = None
        seeded_buildings = set()   # track which building IDs already had zones/states seeded

        for config in TESTER_CONFIGS:
            building = get_or_create_building(db, config, Building)
            user = get_or_create_user(db, config, User)
            ensure_user_building_mapping(db, user, building, config["role"], UserBuilding)

            building_primary_unit = None   # first hvac_unit created/found for this building
            for device_config in iter_config_devices(config):
                hvac_unit = get_or_create_hvac_unit(db, building, device_config, HVACUnit)
                if building_primary_unit is None:
                    building_primary_unit = hvac_unit

                sensors = {}
                for sensor_config in device_config["sensors"]:
                    sensor_type = sensor_config["type"]
                    sensors[sensor_config.get("key", sensor_type)] = get_or_create_sensor(
                        db,
                        building,
                        hvac_unit,
                        device_config,
                        sensor_type,
                        sensor_config["unit"],
                        Sensor,
                        payload_path=sensor_config.get("payload_path"),
                        label=sensor_config.get("label"),
                    )

                if device_config.get("seed_timeseries", False):
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
                    )
                    total_steps += steps
                    total_weather += weather_count
                    total_schedules += schedule_count
                    total_sensor_rows += sensor_count

            # Zone + schedules + zone states — seeded once per unique building.
            # Tester1 and Tester4 share Pilot1, so we guard with seeded_buildings.
            if building.id not in seeded_buildings:
                if config["building_name"] == "Pilot1":
                    # Pilot1: 3 split units, one per office zone — each is its own device
                    pilot_topology = [
                        {
                            "split": "Split Office 1", "zone": "Zone Office 1",
                            "room": "Office 1", "thermostat": "Thermostat Office 1",
                            "thermostat_bms_id": "split_office_1",
                            "is_controllable": True,
                            "sensors": [
                                {
                                    "type": "temperature", "unit": "°C",
                                    "payload_path": "temperature.tC",
                                    "is_controllable": True,
                                    "command_payload_template": '{"setpoint": {value}}',
                                },
                                {"type": "energy",   "unit": "Wh",   "payload_path": "aenergy.total"},
                                {"type": "presence", "unit": "bool", "payload_path": "output"},
                            ],
                        },
                        {
                            "split": "Split Office 2", "zone": "Zone Office 2",
                            "room": "Office 2", "thermostat": "Thermostat Office 2",
                            "thermostat_bms_id": "split_office_2",
                            "is_controllable": True,
                            "sensors": [
                                {
                                    "type": "temperature", "unit": "°C",
                                    "payload_path": "temperature.tC",
                                    "is_controllable": True,
                                    "command_payload_template": '{"setpoint": {value}, "mode": "auto"}',
                                },
                                {"type": "energy",  "unit": "Wh", "payload_path": "aenergy.total"},
                                {"type": "power",   "unit": "W",  "payload_path": "apower"},
                                {"type": "voltage", "unit": "V",  "payload_path": "voltage"},
                            ],
                        },
                        {
                            "split": "Split Office 3", "zone": "Zone Office 3",
                            "room": "Office 3", "thermostat": "Thermostat Office 3",
                            "thermostat_bms_id": "split_office_3",
                            "is_controllable": False,
                            "sensors": [
                                {"type": "temperature", "unit": "°C", "payload_path": "temperature.tC"},
                                {"type": "energy",      "unit": "Wh", "payload_path": "aenergy.total"},
                                {"type": "power",       "unit": "W",  "payload_path": "apower"},
                                {"type": "voltage",     "unit": "V",  "payload_path": "voltage"},
                            ],
                        },
                    ]
                    for topo in pilot_topology:
                        split_unit = get_or_create_hvac_unit(
                            db, building,
                            {"central_unit": topo["split"], "unit_type": "split"},
                            HVACUnit,
                        )

                        # Zone must exist before sensors so zone_id can be assigned
                        zone = get_or_create_zone(db, building, topo["zone"], HVACZone)
                        get_or_create_zone_hvac_link(db, zone, split_unit, ZoneHVACUnit)

                        split_sensors = {}
                        for s_cfg in topo["sensors"]:
                            split_sensors[s_cfg["type"]] = get_or_create_sensor(
                                db, building, split_unit, {}, s_cfg["type"], s_cfg["unit"], Sensor,
                                payload_path=s_cfg.get("payload_path"),
                                zone_id=zone.id,
                                is_controllable=s_cfg.get("is_controllable", False),
                                command_payload_template=s_cfg.get("command_payload_template"),
                            )

                        steps, wc, sc, src = seed_building_timeseries(
                            db, building, split_unit, split_sensors, user.id, start, end, WeatherData, SensorData
                        )
                        total_steps += steps
                        total_weather += wc
                        total_sensor_rows += src

                        room = get_or_create_room(db, building, topo["room"], Room)
                        get_or_create_zone_room_link(db, zone, room, ZoneRoom)
                        thermostat = get_or_create_thermostat(
                            db, building, topo["thermostat"], Thermostat,
                            is_controllable=topo.get("is_controllable", False),
                            external_bms_id=topo.get("thermostat_bms_id"),
                        )
                        get_or_create_zone_thermostat_link(db, zone, thermostat, ZoneThermostat)
                        seed_zone_schedule(db, zone, start, ZoneSchedule, ZoneScheduleInterval)
                        total_zone_state_rows += seed_zone_states(
                            db, zone, split_unit, start, end, ZoneState
                        )
                else:
                    zone = get_or_create_zone(db, building, "Main Zone", HVACZone)
                    get_or_create_zone_hvac_link(db, zone, building_primary_unit, ZoneHVACUnit)
                    seed_zone_schedule(db, zone, start, ZoneSchedule, ZoneScheduleInterval)
                    total_zone_state_rows += seed_zone_states(
                        db, zone, building_primary_unit, start, end, ZoneState
                    )
                seeded_buildings.add(building.id)

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
            f"{total_sensor_rows} sensor rows, {total_zone_state_rows} zone state rows "
            f"across {len(TESTER_CONFIGS)} tester scenarios"
        )

    except Exception as e:
        db.rollback()
        print(f"❌ Error during mock data initialization: {str(e)}")
        raise
    finally:
        db.close()
