from sqlalchemy import (
    BigInteger, Boolean, Column, ForeignKey, Text, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from db.connection import Base

ONDELETE_CASCADE = "CASCADE"


class HVACControlModel(Base):
    __tablename__ = "hvac_control_models"

    id = Column(BigInteger, primary_key=True)
    zone_id = Column(BigInteger, ForeignKey("hvac_zones.id", ondelete=ONDELETE_CASCADE), nullable=True)
    thermostat_id = Column(BigInteger, ForeignKey("thermostats.id", ondelete=ONDELETE_CASCADE), nullable=True)
    hvac_unit_id = Column(BigInteger, ForeignKey("hvac_units.id", ondelete=ONDELETE_CASCADE), nullable=True)
    model_type = Column(Text, nullable=False)  # pid, linear, piecewise_linear, ml_model
    version = Column(Text, nullable=True, default="v1")
    parameters = Column(JSONB, nullable=False)
    calibrated_from_ts = Column(TIMESTAMP(timezone=True), nullable=True)
    calibrated_to_ts = Column(TIMESTAMP(timezone=True), nullable=True)
    valid_from = Column(TIMESTAMP(timezone=True), nullable=True)
    valid_to = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
