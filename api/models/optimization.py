from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON, Text, UniqueConstraint, Index, Boolean
from db import Base
from datetime import datetime

class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    snapshot_batch_id = Column(
        Integer,
        ForeignKey("optimization_input_snapshot_batches.id"),
        nullable=True,
        index=True,
    )
    optimization_time = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    input_hash = Column(String(64), nullable=False, index=True)
    output_hash = Column(String(64), nullable=False, index=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    energy_saving_kwh = Column(Float, nullable=True)
    baseline_consumption_kwh = Column(Float, nullable=True)
    optimized_consumption_kwh = Column(Float, nullable=True)
    environmental_points = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    is_optimized = Column(Boolean, nullable=False, default=False)  # True if actually applied

    __table_args__ = (
        UniqueConstraint("building_id", "input_hash", "output_hash", "optimization_time", name="uq_optimization_building_input_output_time"),
        Index("ix_optimization_results_building_id", "building_id"),
        Index("ix_optimization_results_input_hash", "input_hash"),
        Index("ix_optimization_results_output_hash", "output_hash"),
    )
