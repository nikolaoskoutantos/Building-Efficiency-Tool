from sqlalchemy import BigInteger, Column, ForeignKey, String, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from db.connection import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(BigInteger, primary_key=True, index=True)
    jti = Column(String(36), unique=True, nullable=False, index=True)  # UUID v4
    hvac_unit_id = Column(BigInteger, ForeignKey("hvac_units.id", ondelete="CASCADE"), nullable=False, index=True)
    issued_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)  # NULL = still valid
