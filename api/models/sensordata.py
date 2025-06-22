from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from db import Base
from datetime import datetime

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    value = Column(Float, nullable=False)
