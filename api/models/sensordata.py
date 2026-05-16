
from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Index, Integer, Numeric, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from db import Base

# SonarQube S1192: Avoid duplicated string literals
SENSORS_ID_FK = "sensors.id"
BUILDINGS_ID_FK = "buildings.id"

class WeatherData(Base):
    __tablename__ = "weather_data"

    __table_args__ = (
        UniqueConstraint("timestamp", "lat", "lon", name="ux_weather_data_ts_lat_lon"),
        Index("ix_weather_data_lat_lon_ts", "lat", "lon", "timestamp"),
    )
    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    temperature = Column(Float)
    humidity = Column(Float)
    pressure = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    precipitation = Column(Float)
    weather_description = Column(String(100))


class SensorData(Base):
    __tablename__ = "sensor_data"

    __table_args__ = (
        UniqueConstraint("sensor_id", "ts", name="uq_sensor_data_sensor_ts"),
        Index("idx_sensor_data_sensor_ts", "sensor_id", "ts"),
        Index("idx_sensor_data_building_ts", "building_id", "ts"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    sensor_id = Column(BigInteger, ForeignKey(SENSORS_ID_FK, ondelete="CASCADE"), nullable=False)
    building_id = Column(BigInteger, ForeignKey(BUILDINGS_ID_FK, ondelete="CASCADE"), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), nullable=False)
    value = Column(Numeric, nullable=True)        # numeric readings (temperature, power, CO2, ...)
    value_text = Column(Text, nullable=True)      # text readings  (hvac_status, mode, ...)
    value_bool = Column(Boolean, nullable=True)   # boolean readings (occupancy, on/off, ...)
    quality = Column(Text, nullable=True, default="valid")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class SensorDataRaw(Base):
    """Staging table — every raw reading from a device lands here.
    The aggregate_sensor_data_5m() PostgreSQL function (pg_cron, every 5 min)
    reads from this table, bins by 5-minute bucket via date_bin(), applies the
    unit-driven aggregation policy from sensor_units.aggregation_method, and
    upserts into sensor_data.
    """
    __tablename__ = "sensor_data_raw"

    __table_args__ = (
        Index("idx_sensor_data_raw_sensor_ts", "sensor_id", "ts"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    sensor_id = Column(BigInteger, ForeignKey(SENSORS_ID_FK, ondelete="CASCADE"), nullable=False)
    building_id = Column(BigInteger, ForeignKey(BUILDINGS_ID_FK, ondelete="CASCADE"), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), nullable=False)
    value = Column(Numeric, nullable=True)        # numeric readings
    value_text = Column(Text, nullable=True)      # text readings  (hvac_status, mode, ...)
    value_bool = Column(Boolean, nullable=True)   # boolean readings (occupancy, on/off, ...)
    payload = Column(JSONB, nullable=True)        # full raw JSON payload for debugging
    # Device-supplied message ID for MQTT replay detection.
    # Partial UNIQUE(sensor_id, msg_id) index (WHERE msg_id IS NOT NULL) rejects
    # duplicate messages from the same sensor.
    msg_id = Column(postgresql.UUID(as_uuid=False), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
