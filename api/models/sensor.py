from sqlalchemy import Column, Integer, Float, String
from db import Base

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    rate_of_sampling = Column(Float, nullable=False)
    raw_data_id = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)
