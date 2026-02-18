from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, String
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

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

# UserBuilding mapping table
from sqlalchemy import UniqueConstraint
class UserBuilding(Base):
    __tablename__ = "user_buildings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # owner, admin, operator, viewer
    status = Column(String, nullable=False, default="active")  # active, revoked
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint('user_id', 'building_id', name='_user_building_uc'),)



class HVACScheduleInterval(Base):
    __tablename__ = "hvac_schedule_intervals"

    id = Column(Integer, primary_key=True, index=True)

    building_id = Column(Integer, ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)

    # NEW: schedule belongs to an HVAC unit (not a sensor row)
    hvac_unit_id = Column(Integer, ForeignKey("hvac_units.id", ondelete="CASCADE"), nullable=False)

    # UTC naive timestamps (timestamp without time zone)
    start_ts = Column(DateTime(timezone=False), nullable=False)
    end_ts = Column(DateTime(timezone=False), nullable=False)

    is_on = Column(Boolean, nullable=False, default=True)
    setpoint = Column(Float, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("hvac_unit_id", "start_ts", name="uq_hvac_schedule_hvacunit_start"),
        Index("ix_hvac_schedule_bld_hvacunit_start", "building_id", "hvac_unit_id", "start_ts"),
        Index("ix_hvac_schedule_hvacunit_timerange", "hvac_unit_id", "start_ts", "end_ts"),
    )
