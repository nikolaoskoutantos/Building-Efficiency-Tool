from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.connection import Base  # make sure this matches your Base import

ONDELETE_CASCADE = "CASCADE"
ONDELETE_SET_NULL = "SET NULL"


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(BigInteger, primary_key=True, index=True)

    building_id = Column(
        BigInteger,
        ForeignKey("buildings.id", ondelete=ONDELETE_CASCADE),
        nullable=False
    )

    name = Column(Text, nullable=False)
    sensor_type = Column(Text, nullable=False)  # temperature, setpoint, humidity, co2, occupancy, hvac_power, hvac_status, etc.
    unit = Column(Text, nullable=True)  # raw string kept for backward compat; prefer unit_id
    unit_id = Column(
        BigInteger,
        ForeignKey("sensor_units.id", ondelete=ONDELETE_SET_NULL),
        nullable=True,
        index=True,
    )
    unit_ref = relationship("SensorUnit", foreign_keys=[unit_id], lazy="select")

    # Physical location references (FK replaces old string room/zone/central_unit)
    room_id = Column(BigInteger, ForeignKey("rooms.id", ondelete=ONDELETE_SET_NULL), nullable=True, index=True)
    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_SET_NULL), nullable=True, index=True)
    thermostat_id = Column(BigInteger, ForeignKey("thermostats.id", ondelete=ONDELETE_SET_NULL), nullable=True)
    hvac_unit_id = Column(BigInteger, ForeignKey("hvac_units.id", ondelete=ONDELETE_SET_NULL), nullable=True, index=True)

    # External system identifiers
    external_sensor_id = Column(Text, nullable=True)
    external_bms_id = Column(Text, nullable=True)

    # MQTT payload extraction path (kept for IoT device ingestion)
    payload_path = Column(Text, nullable=True)

    # Bidirectional control — sensor can also receive commands
    is_controllable = Column(Boolean, nullable=False, server_default="false")
    command_payload_template = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("building_id", "name", name="uq_sensors_building_name"),
        UniqueConstraint("building_id", "external_sensor_id", name="uq_sensors_building_external_id"),
    )
