INCENTIVE_NOT_FOUND = "Incentive not found"
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..db import db
from ..models import incentives as incentives_model
from ..models import buildings as buildings_model
from ..models import sensor as sensor_model
from ..models import hvac_models
from ..schemas import incentives as incentives_schema

router = APIRouter(prefix="/incentives", tags=["incentives"])

# Dependency to get DB session
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

@router.post("/", response_model=incentives_schema.Incentive)
def create_incentive(incentive: incentives_schema.IncentiveCreate, db: Session = Depends(get_db)):
    db_incentive = incentives_model.Incentive(**incentive.dict())
    db.add(db_incentive)
    db.commit()
    db.refresh(db_incentive)
    return db_incentive

@router.get("/", response_model=list[incentives_schema.Incentive])
def read_incentives(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(incentives_model.Incentive).offset(skip).limit(limit).all()

@router.get("/{incentive_id}", response_model=incentives_schema.Incentive)
def read_incentive(incentive_id: int, db: Session = Depends(get_db)):
    incentive = db.query(incentives_model.Incentive).filter(incentives_model.Incentive.id == incentive_id).first()
    if not incentive:
        raise HTTPException(status_code=404, detail=INCENTIVE_NOT_FOUND)
    return incentive

@router.put("/{incentive_id}", response_model=incentives_schema.Incentive)
def update_incentive(incentive_id: int, incentive: incentives_schema.IncentiveUpdate, db: Session = Depends(get_db)):
    db_incentive = db.query(incentives_model.Incentive).filter(incentives_model.Incentive.id == incentive_id).first()
    if not db_incentive:
        raise HTTPException(status_code=404, detail=INCENTIVE_NOT_FOUND)
    for key, value in incentive.dict(exclude_unset=True).items():
        setattr(db_incentive, key, value)
    db.commit()
    db.refresh(db_incentive)
    return db_incentive

@router.delete("/{incentive_id}")
def delete_incentive(incentive_id: int, db: Session = Depends(get_db)):
    db_incentive = db.query(incentives_model.Incentive).filter(incentives_model.Incentive.id == incentive_id).first()
    if not db_incentive:
        raise HTTPException(status_code=404, detail=INCENTIVE_NOT_FOUND)
    db.delete(db_incentive)
    db.commit()
    return {"ok": True}
