from sqlalchemy import BigInteger, Column, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from db.connection import Base


class DeviceCommand(Base):
    __tablename__ = "device_commands"

    id = Column(BigInteger, primary_key=True, index=True)
    hvac_unit_id = Column(
        BigInteger,
        ForeignKey("hvac_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_id = Column(
        BigInteger,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
    )
    # e.g. "set_setpoint", "set_mode", "reboot", "custom"
    command_type = Column(String(64), nullable=False)
    # Full payload published to the device over MQTT
    payload = Column(JSONB, nullable=False)
    # pending → published → acked | failed
    status = Column(String(16), nullable=False, default="pending")
    # Exact MQTT topic used: building/{building_id}/device/{device_key}/cmd
    topic = Column(Text, nullable=False)
    # User who issued this command (nullable – allow service-level issuance)
    issued_by_user_id = Column(BigInteger, nullable=True)
    issued_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    # Set when device ACKs the command (optional device-side support)
    acked_at = Column(TIMESTAMP(timezone=True), nullable=True)
