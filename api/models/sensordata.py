
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Index
from db import Base
from datetime import datetime

# SonarQube S1192: Avoid duplicated string literals
SENSORS_ID_FK = "sensors.id"

class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Float, nullable=True)
    precipitation = Column(Float, nullable=True)
    weather_description = Column(String(100), nullable=True)

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey(SENSORS_ID_FK), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    value = Column(Float, nullable=False)
    measurement_type = Column(String(50), nullable=False, default='temperature')
    unit = Column(String(20), default='celsius')

class HVACSensorData(Base):
    __tablename__ = "hvac_sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey(SENSORS_ID_FK), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    indoor_temp = Column(Float, nullable=False)
    outdoor_temp = Column(Float, nullable=False)
    hvac_operation = Column(Integer, nullable=False)
    energy_consumption = Column(Float, nullable=False)
    setpoint_temp = Column(Float, nullable=True)  # Only when HVAC is ON
    outlet_temp = Column(Float, nullable=True)  # Only when HVAC is ON
    inlet_temp = Column(Float, nullable=True)  # Only when HVAC is ON
    unit = Column(String(20), default='celsius')

class SensorDataRaw(Base):
    __tablename__ = "sensor_data_raw"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey(SENSORS_ID_FK), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    value = Column(Float, nullable=True)                 # single numeric if you normalize
    measurement_type = Column(String(50), nullable=False) # e.g. 'apower_w', 'energy_wh'
    unit = Column(String(20), nullable=True)

    payload = Column(JSON, nullable=True)  # optional: store full Shelly JSON message

    __table_args__ = (
        Index("ix_sensor_data_raw_sensor_ts", "sensor_id", "timestamp"),
    )