from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from db import Base

class Predictor(Base):
    __tablename__ = "predictors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    scores = Column(JSON, nullable=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge.id"), nullable=False)
