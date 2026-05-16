from sqlalchemy import (
    BigInteger, Boolean, Column, ForeignKey, Numeric, Text, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.sql import func
from db.connection import Base

FK_BUILDINGS_ID = "buildings.id"
ONDELETE_CASCADE = "CASCADE"


class Thermostat(Base):
    __tablename__ = "thermostats"

    id = Column(BigInteger, primary_key=True)
    building_id = Column(BigInteger, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_CASCADE), nullable=False)
    name = Column(Text, nullable=False)
    manufacturer = Column(Text, nullable=True)
    model = Column(Text, nullable=True)
    external_bms_id = Column(Text, nullable=True)
    is_controllable = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("building_id", "name", name="uq_thermostats_building_name"),
    )


class ZoneThermostat(Base):
    __tablename__ = "zone_thermostats"

    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_CASCADE), nullable=False, primary_key=True)
    thermostat_id = Column(BigInteger, ForeignKey("thermostats.id", ondelete=ONDELETE_CASCADE), nullable=False, primary_key=True)
    role = Column(Text, nullable=True, default="primary")
    control_weight = Column(Numeric, nullable=True, default=1.0)
