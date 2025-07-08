"""
Sensor model - enhanced for PostgreSQL
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from ..connection import Base

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)  # Optional link to service
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    rate_of_sampling = Column(Float, nullable=False)
    raw_data_id = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)
    sensor_type = Column(String, nullable=True)  # e.g., "temperature", "humidity", etc.
    is_active = Column(Boolean, default=True)
    last_reading = Column(Float, nullable=True)
    last_reading_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Sensor(id={self.id}, lat={self.lat}, lon={self.lon}, unit='{self.unit}')>"
