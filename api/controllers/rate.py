from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models.rate import Rate
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/rates", tags=["Rates"])

# Pydantic schemas
class RateBase(BaseModel):
    service_id: int
    rating: float

class RateCreate(RateBase):
    pass

class RateRead(RateBase):
    id: int
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=RateRead)
def create_rate(rate: RateCreate, db: Session = Depends(get_db)):
    db_rate = Rate(**rate.dict())
    db.add(db_rate)
    db.commit()
    db.refresh(db_rate)
    return db_rate

@router.get("/", response_model=List[RateRead])
def read_rates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Rate).offset(skip).limit(limit).all()

@router.get("/{rate_id}", response_model=RateRead)
def read_rate(rate_id: int, db: Session = Depends(get_db)):
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    return rate

@router.put("/{rate_id}", response_model=RateRead)
def update_rate(rate_id: int, rate: RateCreate, db: Session = Depends(get_db)):
    db_rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    for key, value in rate.dict().items():
        setattr(db_rate, key, value)
    db.commit()
    db.refresh(db_rate)
    return db_rate

@router.delete("/{rate_id}")
def delete_rate(rate_id: int, db: Session = Depends(get_db)):
    db_rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not db_rate:
        raise HTTPException(status_code=404, detail="Rate not found")
    db.delete(db_rate)
    db.commit()
    return {"detail": "Rate deleted"}
