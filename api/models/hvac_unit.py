from sqlalchemy import BigInteger, Column, ForeignKey, Numeric, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from db.connection import Base

class HVACUnit(Base):
    __tablename__ = "hvac_units"

    id = Column(BigInteger, primary_key=True, index=True)

    building_id = Column(
        BigInteger,
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    name = Column(Text, nullable=False)
    unit_type = Column(Text, nullable=False)  # split, fan_coil, ahu, rooftop, heat_pump, chiller, boiler
    manufacturer = Column(Text, nullable=True)
    model = Column(Text, nullable=True)

    cooling_capacity_kw = Column(Numeric, nullable=True)
    heating_capacity_kw = Column(Numeric, nullable=True)
    min_airflow_m3_s = Column(Numeric, nullable=True)
    max_airflow_m3_s = Column(Numeric, nullable=True)

    cop = Column(Numeric, nullable=True)
    eer = Column(Numeric, nullable=True)
    seer = Column(Numeric, nullable=True)
    scop = Column(Numeric, nullable=True)

    # Device authentication fields (kept for IoT device JWT auth)
    device_key = Column(String, unique=True, nullable=True, index=True)
    device_secret_hash = Column(String, nullable=True)
    device_secret_rotated_at = Column(String, nullable=True)
    device_revoked_at = Column(String, nullable=True)

    # Connectivity tracking — updated on every status/sensor message
    last_seen_at = Column(TIMESTAMP(timezone=True), nullable=True)
    connection_status = Column(String(16), nullable=True)  # online | offline

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("building_id", "name", name="uq_hvac_units_building_name"),
    )
