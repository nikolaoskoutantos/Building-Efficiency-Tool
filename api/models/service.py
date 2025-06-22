from sqlalchemy import Column, Integer, String, Float, JSON
from db import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    smart_contract_id = Column(String, nullable=False)
    link_cost = Column(Float, nullable=False)
    callback_wallet_addresses = Column(String, nullable=False)  # Comma-separated or JSON if you want
    input_parameters = Column(JSON, nullable=True)
    knowledge_asset = Column(JSON, nullable=True)
