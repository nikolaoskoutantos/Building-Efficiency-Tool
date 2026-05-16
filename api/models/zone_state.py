from sqlalchemy import (
    BigInteger, Column, ForeignKey, Integer, Numeric, Text, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.sql import func
from db.connection import Base

ONDELETE_CASCADE = "CASCADE"
ONDELETE_SET_NULL = "SET NULL"


class ZoneState(Base):
    __tablename__ = "zone_states"

    id = Column(BigInteger, primary_key=True)
    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_CASCADE), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), nullable=False)

    measured_temp_c = Column(Numeric, nullable=True)
    setpoint_c = Column(Numeric, nullable=True)
    delta_t_c = Column(Numeric, nullable=True)

    humidity_pct = Column(Numeric, nullable=True)
    co2_ppm = Column(Numeric, nullable=True)
    occupancy = Column(Integer, nullable=True)

    thermostat_id = Column(BigInteger, ForeignKey("thermostats.id", ondelete=ONDELETE_SET_NULL), nullable=True)
    hvac_unit_id = Column(BigInteger, ForeignKey("hvac_units.id", ondelete=ONDELETE_SET_NULL), nullable=True)

    controller_output_pct = Column(Numeric, nullable=True)
    hvac_status = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("zone_id", "ts", name="uq_zone_states_zone_ts"),
    )
