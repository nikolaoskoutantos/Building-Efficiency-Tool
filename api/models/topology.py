from sqlalchemy import (
    BigInteger, Column, ForeignKey, Integer, Numeric, Text, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.sql import func
from db.connection import Base

FK_BUILDINGS_ID = "buildings.id"
ONDELETE_CASCADE = "CASCADE"
ONDELETE_SET_NULL = "SET NULL"


class Floor(Base):
    __tablename__ = "floors"

    id = Column(BigInteger, primary_key=True)
    building_id = Column(BigInteger, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_CASCADE), nullable=False)
    name = Column(Text, nullable=False)
    level = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("building_id", "name", name="uq_floors_building_name"),
    )


class Room(Base):
    __tablename__ = "rooms"

    id = Column(BigInteger, primary_key=True)
    building_id = Column(BigInteger, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_CASCADE), nullable=False)
    floor_id = Column(BigInteger, ForeignKey("floors.id", ondelete=ONDELETE_SET_NULL), nullable=True)
    name = Column(Text, nullable=False)
    area_m2 = Column(Numeric, nullable=True)
    volume_m3 = Column(Numeric, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("building_id", "name", name="uq_rooms_building_name"),
    )


class HVACZone(Base):
    __tablename__ = "hvac_zones"

    id = Column(BigInteger, primary_key=True)
    building_id = Column(BigInteger, ForeignKey(FK_BUILDINGS_ID, ondelete=ONDELETE_CASCADE), nullable=False)
    name = Column(Text, nullable=False)
    zone_type = Column(Text, nullable=True, default="thermal")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("building_id", "name", name="uq_hvac_zones_building_name"),
    )


class ZoneRoom(Base):
    __tablename__ = "zone_rooms"

    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_CASCADE), nullable=False, primary_key=True)
    room_id = Column(BigInteger, ForeignKey("rooms.id", ondelete=ONDELETE_CASCADE), nullable=False, primary_key=True)
    weight = Column(Numeric, nullable=True, default=1.0)


class ZoneHVACUnit(Base):
    __tablename__ = "zone_hvac_units"

    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_CASCADE), nullable=False, primary_key=True)
    hvac_unit_id = Column(BigInteger, ForeignKey("hvac_units.id", ondelete=ONDELETE_CASCADE), nullable=False, primary_key=True)
    role = Column(Text, nullable=True, default="serves")
    allocation_weight = Column(Numeric, nullable=True, default=1.0)
