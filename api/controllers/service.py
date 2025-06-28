from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models.service import Service
from controllers.auth import get_current_user
from typing import List
from pydantic import BaseModel, Field

router = APIRouter(prefix="/services", tags=["Services"])

# Pydantic schemas
class ServiceBase(BaseModel):
    name: str
    description: str = None
    smart_contract_id: str
    link_cost: float
    callback_wallet_addresses: str
    input_parameters: dict = Field(default_factory=dict)
    knowledge_asset: dict = Field(default_factory=dict)

class ServiceCreate(ServiceBase):
    pass

class ServiceRead(ServiceBase):
    id: int
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=ServiceRead)
def create_service(service: ServiceCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_service = Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("/", response_model=List[ServiceRead])
def read_services(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Service).offset(skip).limit(limit).all()

@router.get("/{service_id}", response_model=ServiceRead)
def read_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.put("/{service_id}", response_model=ServiceRead)
def update_service(service_id: int, service: ServiceCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_service = db.query(Service).filter(Service.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")
    for key, value in service.dict().items():
        setattr(db_service, key, value)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.delete("/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    db_service = db.query(Service).filter(Service.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")
    db.delete(db_service)
    db.commit()
    return {"detail": "Service deleted"}
