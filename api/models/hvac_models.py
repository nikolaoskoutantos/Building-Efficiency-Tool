from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, String
from sqlalchemy.sql import func
from db.connection import Base

# String constants to avoid duplication (SonarQube S1192)
TABLE_BUILDINGS = "buildings"
TABLE_USERS = "users" 
TABLE_USER_BUILDINGS = "user_buildings"
TABLE_HVAC_UNITS = "hvac_units"
TABLE_HVAC_SCHEDULE_INTERVALS = "hvac_schedule_intervals"

# Foreign key references
FK_BUILDINGS_ID = "buildings.id"
FK_USERS_ID = "users.id"
FK_HVAC_UNITS_ID = "hvac_units.id"

# OnDelete actions
ONDELETE_CASCADE = "CASCADE"
ONDELETE_SET_NULL = "SET NULL"

# Building model
class Building(Base):
    __tablename__ = TABLE_BUILDINGS
    id = Column(Integer, primary_key=True, index=True)
    did = Column(String, unique=True, nullable=True)  # Decentralized Identifier
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    lat = Column(String, nullable=True)  # Latitude as string for flexibility
    lon = Column(String, nullable=True)  # Longitude as string for flexibility

# User model
class User(Base):
    __tablename__ = TABLE_USERS
    id = Column(Integer, primary_key=True)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    
    # Personal Information
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)  # Physical address
    
    # Building Management
    default_building_id = Column(Integer, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_SET_NULL), nullable=True)
    
    # Blockchain & Crypto
    public_key = Column(String, nullable=True)  # Public key for encryption/signatures
    
    # API Configuration
    api_base_url = Column(String, nullable=True)  # Custom API endpoint preference
    
    # System fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

# UserBuilding mapping table
from sqlalchemy import UniqueConstraint
class UserBuilding(Base):
    __tablename__ = TABLE_USER_BUILDINGS
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(FK_USERS_ID, ondelete=ONDELETE_CASCADE), nullable=False)
    building_id = Column(Integer, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_CASCADE), nullable=False)
    role = Column(String, nullable=False)  # owner, admin, operator, viewer
    status = Column(String, nullable=False, default="active")  # active, revoked
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint('user_id', 'building_id', name='_user_building_uc'),)



class HVACScheduleInterval(Base):
    __tablename__ = TABLE_HVAC_SCHEDULE_INTERVALS

    id = Column(Integer, primary_key=True, index=True)

    building_id = Column(Integer, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_CASCADE), nullable=False)

    # NEW: schedule belongs to an HVAC unit (not a sensor row)
    hvac_unit_id = Column(Integer, ForeignKey(FK_HVAC_UNITS_ID, ondelete=ONDELETE_CASCADE), nullable=False)

    # UTC naive timestamps (timestamp without time zone)
    start_ts = Column(DateTime(timezone=False), nullable=False)
    end_ts = Column(DateTime(timezone=False), nullable=False)

    is_on = Column(Boolean, nullable=False, default=True)
    setpoint = Column(Float, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey(FK_USERS_ID, ondelete=ONDELETE_SET_NULL), nullable=True)

    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("hvac_unit_id", "start_ts", name="uq_hvac_schedule_hvacunit_start"),
        Index("ix_hvac_schedule_bld_hvacunit_start", "building_id", "hvac_unit_id", "start_ts"),
        Index("ix_hvac_schedule_hvacunit_timerange", "hvac_unit_id", "start_ts", "end_ts"),
    )
