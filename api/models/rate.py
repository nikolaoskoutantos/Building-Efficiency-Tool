from sqlalchemy import Column, Integer, Float, ForeignKey
from db import Base

class Rate(Base):
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    rating = Column(Float, nullable=False)
