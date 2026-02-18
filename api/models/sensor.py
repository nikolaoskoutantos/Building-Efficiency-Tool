from sqlalchemy import Column, Integer, Float, String, ForeignKey
from db.connection import Base  # make sure this matches your Base import

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)

    building_id = Column(
        Integer,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False
    )

    # NEW: link to HVACUnit (not self-reference)
    hvac_unit_id = Column(
        Integer,
        ForeignKey("hvac_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    type = Column(String, nullable=True)  # 'temperature', 'presence', etc.

    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    rate_of_sampling = Column(Float, nullable=False)
    raw_data_id = Column(Integer, nullable=False)

    unit = Column(String, nullable=False)

    room = Column(String, nullable=True)
    zone = Column(String, nullable=True)
    central_unit = Column(String, nullable=True)
