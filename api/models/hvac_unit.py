from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from db.connection import Base

class HVACUnit(Base):
    __tablename__ = "hvac_units"

    id = Column(Integer, primary_key=True, index=True)

    building_id = Column(
        Integer,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    central_unit = Column(String, nullable=True)
    zone = Column(String, nullable=True)
    room = Column(String, nullable=True)
