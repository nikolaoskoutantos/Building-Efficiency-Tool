ALERT_NOT_FOUND = "Alert not found"
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..db import db
from ..models import alerts as alerts_model
from ..models import buildings as buildings_model
from ..models import sensor as sensor_model
from ..models import hvac_models
from ..schemas import alerts as alerts_schema

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Dependency to get DB session
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

@router.post("/", response_model=alerts_schema.Alert)
def create_alert(alert: alerts_schema.AlertCreate, db: Session = Depends(get_db)):
    db_alert = alerts_model.Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.get("/", response_model=list[alerts_schema.Alert])
def read_alerts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(alerts_model.Alert).offset(skip).limit(limit).all()

@router.get("/{alert_id}", response_model=alerts_schema.Alert)
def read_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(alerts_model.Alert).filter(alerts_model.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=ALERT_NOT_FOUND)
    return alert

@router.put("/{alert_id}", response_model=alerts_schema.Alert)
def update_alert(alert_id: int, alert: alerts_schema.AlertUpdate, db: Session = Depends(get_db)):
    db_alert = db.query(alerts_model.Alert).filter(alerts_model.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail=ALERT_NOT_FOUND)
    for key, value in alert.dict(exclude_unset=True).items():
        setattr(db_alert, key, value)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    db_alert = db.query(alerts_model.Alert).filter(alerts_model.Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail=ALERT_NOT_FOUND)
    db.delete(db_alert)
    db.commit()
    return {"ok": True}
