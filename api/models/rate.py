from sqlalchemy import Column, Integer, Float, ForeignKey, String, DateTime, Text
from sqlalchemy.sql import func
from db import Base

class Rate(Base):
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    encrypted_wallet = Column(String, nullable=False)  # Encrypted wallet address for privacy
    rating = Column(Float, nullable=False)  # 1-10 thermal comfort OR 1-5 service quality
    rating_type = Column(String(32), nullable=False, server_default="service_quality")  # 'thermal_comfort' | 'service_quality'
    feedback = Column(Text, nullable=True)  # Optional user feedback
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Rate(id={self.id}, service_id={self.service_id}, rating_type={self.rating_type}, rating={self.rating})>"
