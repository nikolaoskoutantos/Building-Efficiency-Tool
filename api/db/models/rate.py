"""
Rate model for encrypted user ratings.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey, String, DateTime, Text
from sqlalchemy.sql import func
from ..connection import Base

class Rate(Base):
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    encrypted_wallet = Column(String, nullable=False)  # Encrypted wallet address for privacy
    rating = Column(Float, nullable=False)  # Rating value (1.0 to 5.0)
    feedback = Column(Text, nullable=True)  # Optional user feedback
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Rate(id={self.id}, service_id={self.service_id}, rating={self.rating})>"
