from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Float, DateTime, Text
from sqlalchemy.sql import func
from db import Base

class Predictor(Base):
    __tablename__ = "predictors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    scores = Column(JSON, nullable=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id"), nullable=False)
    # Location-based fields
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    # HVAC-specific fields
    model_type = Column(String, nullable=True)  # 'linear_regression', 'random_forest', 'hvac_optimizer'
    model_data = Column(JSON, nullable=True)  # Serialized model parameters
    training_data_hash = Column(String, nullable=True)  # Hash of training data for version control
    hvac_schedule_id = Column(Integer, ForeignKey("hvac_schedules.id"), nullable=True)  # Link to schedule
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class TrainingHistory(Base):
    __tablename__ = "training_history"

    id = Column(Integer, primary_key=True, index=True)
    predictor_id = Column(Integer, ForeignKey("predictors.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    training_started_at = Column(DateTime, server_default=func.now())
    training_completed_at = Column(DateTime, nullable=True)
    training_status = Column(String, nullable=False)  # 'started', 'completed', 'failed'
    training_metrics = Column(JSON, nullable=True)  # R2, RMSE, MAPE scores
    data_size = Column(Integer, nullable=True)  # Number of training samples
    model_parameters = Column(JSON, nullable=True)  # Hyperparameters used
    notes = Column(Text, nullable=True)
