from sqlalchemy import Column, Integer, Float, String, ForeignKey
from db import Base

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=True)  # Link to building
    hvac_id = Column(Integer, ForeignKey("sensors.id"), nullable=True)  # If this is a sensor attached to an HVAC
    type = Column(String, nullable=True)  # 'hvac', 'temperature', etc.
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    rate_of_sampling = Column(Float, nullable=False)
    raw_data_id = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)
    room = Column(String, nullable=True)  # Room name or number
    zone = Column(String, nullable=True)  # Zone identifier
    central_unit = Column(String, nullable=True)  # Central unit association
