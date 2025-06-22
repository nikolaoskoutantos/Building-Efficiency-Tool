from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models.predictor import Predictor
from typing import List
from pydantic import BaseModel, Field

router = APIRouter(prefix="/predict", tags=["Predictors"])

# Pydantic schemas
class PredictorBase(BaseModel):
    name: str
    framework: str
    scores: dict = Field(default_factory=dict)
    knowledge_id: int

class PredictorCreate(PredictorBase):
    pass

class PredictorRead(PredictorBase):
    id: int
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=PredictorRead)
def create_predictor(predictor: PredictorCreate, db: Session = Depends(get_db)):
    db_predictor = Predictor(**predictor.dict())
    db.add(db_predictor)
    db.commit()
    db.refresh(db_predictor)
    return db_predictor

@router.get("/", response_model=List[PredictorRead])
def read_predictors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Predictor).offset(skip).limit(limit).all()

@router.post("/predict_one")
def predict_one(input_data: dict):
    # This is a placeholder for actual prediction logic
    # You can later load a model and return a prediction based on input_data
    return {"prediction": "This is a mock prediction", "input": input_data}
