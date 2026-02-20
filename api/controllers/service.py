
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from db import SessionLocal
from models.service import Service
from controllers.auth import get_current_user
from typing import List, Optional
from pydantic import BaseModel, Field

# Error message constants
SERVICE_NOT_FOUND_MSG = "Service not found"
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/services", tags=["Services"])

# Pydantic schemas
class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    smart_contract_id: str
    link_cost: float
    callback_wallet_addresses: str
    input_parameters: Optional[dict] = None
    knowledge_asset: Optional[dict] = None

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
def create_service(
    service: ServiceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
):
    db_service = Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("/", response_model=List[ServiceRead])
def read_services(db: Annotated[Session, Depends(get_db)],skip: int = 0, limit: int = 100):
    return db.query(Service).offset(skip).limit(limit).all()

@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    responses={404: {"description": "Service not found"}}
)
def read_service(service_id: int, db: Annotated[Session, Depends(get_db)]):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail=SERVICE_NOT_FOUND_MSG)
    return service

@router.put(
    "/{service_id}",
    response_model=ServiceRead,
    responses={404: {"description": "Service not found"}}
)
def update_service(
    service_id: int,
    service: ServiceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
):
    db_service = db.query(Service).filter(Service.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail=SERVICE_NOT_FOUND_MSG)
    for key, value in service.dict().items():
        setattr(db_service, key, value)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.delete(
    "/{service_id}",
    responses={200: {"description": "Service deleted"}, 404: {"description": "Service not found"}}
)
def delete_service(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
):
    db_service = db.query(Service).filter(Service.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail=SERVICE_NOT_FOUND_MSG)
    db.delete(db_service)
    db.commit()
    return {"detail": "Service deleted"}
