import datetime
from sqlalchemy import and_
from db.connection import SessionLocal

def utc_naive(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(tzinfo=None)

def insert_mock_data():
    db = SessionLocal()
    try:
        from models.hvac_models import Building, User, UserBuilding, HVACScheduleInterval
        from models.hvac_unit import HVACUnit
        from models.sensor import Sensor
        from models.sensordata import WeatherData, SensorData

        print("🔄 Checking and initializing mock data...")

        # 1) Building
        pilot_building = db.query(Building).filter_by(name="Pilot1").first()
        if not pilot_building:
            pilot_building = Building(
                did="0xA",
                name="Pilot1",
                address="Athens, Greece",
                lat="37.99",
                lon="23.73",
            )
            db.add(pilot_building)
            db.commit()
            db.refresh(pilot_building)
            print("🏢 Added building: Pilot1")
        else:
            print("🏢 Building Pilot1 already exists")

        # 2) User
        user_wallet = "0xUSERWALLET1234567890"
        user = db.query(User).filter_by(wallet_address=user_wallet).first()
        if not user:
            user = User(wallet_address=user_wallet)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"👤 Added user: {user_wallet}")

        # 3) User ↔ Building mapping
        ub = db.query(UserBuilding).filter_by(user_id=user.id, building_id=pilot_building.id).first()
        if not ub:
            ub = UserBuilding(
                user_id=user.id,
                building_id=pilot_building.id,
                role="building_manager",
                status="active",
            )
            db.add(ub)
            db.commit()
            print("🔗 Mapped user to building")

        # 4) Create ONE HVAC unit for this building (new table)
        hvac_unit = db.query(HVACUnit).filter_by(
            building_id=pilot_building.id,
            room="101",
            zone="A",
            central_unit="CU1",
        ).first()

        if not hvac_unit:
            hvac_unit = HVACUnit(
                building_id=pilot_building.id,
                room="101",
                zone="A",
                central_unit="CU1",
            )
            db.add(hvac_unit)
            db.commit()
            db.refresh(hvac_unit)
            print(f"❄️ Created HVAC unit id={hvac_unit.id}")
        else:
            print(f"❄️ HVAC unit already exists id={hvac_unit.id}")

        # 5) Create sensors attached to HVAC unit (hvac_unit_id)
        def get_or_create_sensor(sensor_type: str, unit: str):
            s = db.query(Sensor).filter_by(
                building_id=pilot_building.id,
                hvac_unit_id=hvac_unit.id,
                type=sensor_type,
                room="101",
                zone="A",
                central_unit="CU1",
            ).first()
            if not s:
                s = Sensor(
                    building_id=pilot_building.id,
                    hvac_unit_id=hvac_unit.id,
                    type=sensor_type,
                    lat=float(pilot_building.lat),
                    lon=float(pilot_building.lon),
                    rate_of_sampling=5.0,
                    raw_data_id=0,
                    unit=unit,
                    room="101",
                    zone="A",
                    central_unit="CU1",
                )
                db.add(s)
                db.commit()
                db.refresh(s)
                print(f"📟 Created sensor {sensor_type} id={s.id}")
            return s

        temp_s = get_or_create_sensor("temperature", "celsius")
        pres_s = get_or_create_sensor("presence", "bool")
        enrg_s = get_or_create_sensor("energy", "kWh")

        # 6) Time grid
        days = 3
        step_min = 5
        now_utc = datetime.datetime.utcnow()
        start = utc_naive(datetime.datetime(now_utc.year, now_utc.month, now_utc.day, 0, 0, 0))
        end = start + datetime.timedelta(days=days)

        time_steps = []
        ts = start
        while ts < end:
            time_steps.append(ts)
            ts += datetime.timedelta(minutes=step_min)

        # 7) Clean existing data in range
        db.query(WeatherData).filter(
            and_(
                WeatherData.lat == float(pilot_building.lat),
                WeatherData.lon == float(pilot_building.lon),
                WeatherData.timestamp >= start,
                WeatherData.timestamp < end,
            )
        ).delete(synchronize_session=False)

        db.query(SensorData).filter(
            and_(
                SensorData.sensor_id.in_([temp_s.id, pres_s.id, enrg_s.id]),
                SensorData.timestamp >= start,
                SensorData.timestamp < end,
            )
        ).delete(synchronize_session=False)

        # NOTE: renamed hvac_id -> hvac_unit_id
        db.query(HVACScheduleInterval).filter(
            and_(
                HVACScheduleInterval.building_id == pilot_building.id,
                HVACScheduleInterval.hvac_unit_id == hvac_unit.id,
                HVACScheduleInterval.start_ts >= start,
                HVACScheduleInterval.start_ts < end,
            )
        ).delete(synchronize_session=False)

        db.commit()
        print("🧹 Cleared old weather/sensor/schedule data for the range")

        # 8) Insert aligned data (bulk)
        weather_rows = []
        schedule_rows = []
        sensor_rows = []

        for i, t in enumerate(time_steps):
            weather_rows.append(
                WeatherData(
                    timestamp=t,
                    lat=float(pilot_building.lat),
                    lon=float(pilot_building.lon),
                    temperature=22.0 + (i % 3),
                    humidity=50.0 + (i % 5),
                    pressure=1010.0 + (i % 2),
                    wind_speed=3.0 + (i % 2),
                    wind_direction=180.0,
                    precipitation=0.0,
                    weather_description="clear sky",
                )
            )

            sched_start = t
            sched_end = t + datetime.timedelta(minutes=step_min)
            is_on = True if (i % 12) < 10 else False
            setpoint = 21.0 if is_on else None

            schedule_rows.append(
                HVACScheduleInterval(
                    building_id=pilot_building.id,
                    hvac_unit_id=hvac_unit.id,
                    start_ts=sched_start,
                    end_ts=sched_end,
                    is_on=is_on,
                    setpoint=setpoint,
                    created_by_user_id=user.id,
                )
            )

            sensor_rows.append(
                SensorData(
                    sensor_id=temp_s.id,
                    timestamp=t,
                    value=20.0 + (i % 4),
                    measurement_type="temperature",
                    unit="celsius",
                )
            )
            sensor_rows.append(
                SensorData(
                    sensor_id=pres_s.id,
                    timestamp=t,
                    value=1.0 if (i % 2 == 0) else 0.0,
                    measurement_type="presence",
                    unit="bool",
                )
            )
            sensor_rows.append(
                SensorData(
                    sensor_id=enrg_s.id,
                    timestamp=t,
                    value=0.5 + 0.1 * (i % 5),
                    measurement_type="energy",
                    unit="kWh",
                )
            )

        db.bulk_save_objects(weather_rows)
        db.bulk_save_objects(schedule_rows)
        db.bulk_save_objects(sensor_rows)
        db.commit()

        print(
            f"✅ Inserted mock data: {len(time_steps)} timesteps, "
            f"{len(weather_rows)} weather rows, {len(schedule_rows)} schedule rows, "
            f"{len(sensor_rows)} sensor rows"
        )

    except Exception as e:
        db.rollback()
        print(f"❌ Error during mock data initialization: {str(e)}")
        raise
    finally:
        db.close()
