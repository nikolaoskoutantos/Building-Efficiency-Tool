from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text

from db import Base


class OptimizationInputSnapshotBatch(Base):
    __tablename__ = "optimization_input_snapshot_batches"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    snapshot_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    __table_args__ = (
        Index("ix_opt_input_snapshot_batch_building_window", "building_id", "start_time", "end_time"),
    )


class OptimizationInputSnapshotRow(Base):
    __tablename__ = "optimization_input_snapshot_rows"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_batch_id = Column(
        Integer,
        ForeignKey("optimization_input_snapshot_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sensor_id = Column(Integer, nullable=True)
    sensor_type = Column(String, nullable=True)
    sensor_value = Column(Float, nullable=True)
    sensor_timestamp = Column(DateTime, nullable=True)
    measurement_type = Column(String, nullable=True)
    sensor_unit = Column(String, nullable=True)
    weather_timestamp = Column(DateTime, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Float, nullable=True)
    precipitation = Column(Float, nullable=True)
    weather_description = Column(String, nullable=True)
    hvac_interval_id = Column(Integer, nullable=True)
    hvac_is_on = Column(Boolean, nullable=True)
    hvac_setpoint = Column(Float, nullable=True)
    hvac_interval_start = Column(DateTime, nullable=True)
    hvac_interval_end = Column(DateTime, nullable=True)
    row_hash = Column(String(64), nullable=False, index=True)
    source_label = Column(Text, nullable=True)
