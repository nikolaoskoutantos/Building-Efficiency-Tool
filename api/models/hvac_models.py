from sqlalchemy import String, Column, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from db import Base
# Building model
class Building(Base):
    __tablename__ = "buildings"
    id = Column(Integer, primary_key=True, index=True)
    did = Column(String, unique=True, nullable=False)  # Decentralized Identifier
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    lat = Column(String, nullable=True)  # Latitude as string for flexibility
    lon = Column(String, nullable=True)  # Longitude as string for flexibility

class HVACSchedule(Base):
    __tablename__ = "hvac_schedules"

    id = Column(Integer, primary_key=True, index=True)
    hvac_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)  # Link to HVAC device (sensor)
    periods = Column(JSON, nullable=False)  # List of {start, end, enabled}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
