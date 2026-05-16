from sqlalchemy import (
    BigInteger, Column, ForeignKey, Integer, Numeric, Text, Time, TIMESTAMP
)
from sqlalchemy.sql import func
from db.connection import Base

ONDELETE_CASCADE = "CASCADE"


class ZoneSchedule(Base):
    __tablename__ = "zone_schedules"

    id = Column(BigInteger, primary_key=True)
    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_CASCADE), nullable=False)
    schedule_type = Column(Text, nullable=False)  # comfort, occupancy, dr_event, manual_override
    name = Column(Text, nullable=True)
    valid_from = Column(TIMESTAMP(timezone=True), nullable=True)
    valid_to = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ZoneScheduleInterval(Base):
    __tablename__ = "zone_schedule_intervals"

    id = Column(BigInteger, primary_key=True)
    schedule_id = Column(BigInteger, ForeignKey("zone_schedules.id", ondelete=ONDELETE_CASCADE), nullable=False)
    day_of_week = Column(Integer, nullable=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    target_setpoint_c = Column(Numeric, nullable=True)
    min_setpoint_c = Column(Numeric, nullable=True)
    max_setpoint_c = Column(Numeric, nullable=True)
    expected_occupancy = Column(Integer, nullable=True)
    hvac_mode = Column(Text, nullable=True)  # cooling, heating, auto, off
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
