"""
Service model - enhanced for PostgreSQL
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from ..connection import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    smart_contract_id = Column(String, nullable=False)
    link_cost = Column(Float, nullable=False)
    callback_wallet_addresses = Column(String, nullable=False)  # Comma-separated addresses
    input_parameters = Column(JSON, nullable=True)
    knowledge_asset = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.name}', smart_contract_id='{self.smart_contract_id}')>"
