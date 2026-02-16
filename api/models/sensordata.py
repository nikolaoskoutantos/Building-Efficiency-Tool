from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from db import Base
from datetime import datetime

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
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    value = Column(Float, nullable=False)
    measurement_type = Column(String(50), nullable=False, default='temperature')
    unit = Column(String(20), default='celsius')

class HVACSensorData(Base):
    __tablename__ = "hvac_sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    indoor_temp = Column(Float, nullable=False)
    outdoor_temp = Column(Float, nullable=False)
    hvac_operation = Column(Integer, nullable=False)  # 0 = OFF, 1 = ON
    energy_consumption = Column(Float, nullable=False)
    setpoint_temp = Column(Float, nullable=True)  # Only when HVAC is ON
    outlet_temp = Column(Float, nullable=True)  # Only when HVAC is ON
    inlet_temp = Column(Float, nullable=True)  # Only when HVAC is ON
    unit = Column(String(20), default='celsius')
