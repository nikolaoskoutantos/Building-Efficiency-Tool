# Constant for error messages
WALLET_REQUIRED_ERROR = "wallet_address is required"
USER_NOT_FOUND_ERROR = "User not found"
# Constant for error message
WALLET_REQUIRED_ERROR = "wallet_address is required"
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Annotated
from datetime import datetime, timezone
import jwt
import os

from db import SessionLocal
from models.hvac_models import User

router = APIRouter(tags=["Users"])

# Pydantic models for user settings
class UserSettingsBase(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    default_building_id: Optional[int] = None
    public_key: Optional[str] = None
    api_base_url: Optional[str] = None

class UserSettingsCreate(UserSettingsBase):
    pass

class UserSettingsUpdate(UserSettingsBase):
    pass

class UserSettingsResponse(UserSettingsBase):
    id: int
    wallet_address: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/user/settings",
    response_model=UserSettingsResponse,
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def get_user_settings(
    db: Annotated[Session, Depends(get_db)],
    wallet_address: str = None
):
    """Get user settings by wallet address"""
    if not wallet_address:
        raise HTTPException(status_code=400, detail=WALLET_REQUIRED_ERROR)
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        user = User(wallet_address=wallet_address)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post(
    "/user/settings",
    response_model=UserSettingsResponse,
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def save_user_settings(
    settings_data: UserSettingsCreate,
    db: Annotated[Session, Depends(get_db)],
    wallet_address: str = None
):
    """Save or update user settings"""
    if not wallet_address:
        raise HTTPException(status_code=400, detail=WALLET_REQUIRED_ERROR)
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        user = User(
            wallet_address=wallet_address,
            **settings_data.dict(exclude_unset=True)
        )
        db.add(user)
    else:
        for field, value in settings_data.dict(exclude_unset=True).items():
            setattr(user, field, value)
        user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user

@router.delete(
    "/user/settings",
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def delete_user_settings(
    db: Annotated[Session, Depends(get_db)],
    wallet_address: str = None
):
    """Delete user's personal data (GDPR right to be forgotten)"""
    if not wallet_address:
        raise HTTPException(status_code=400, detail=WALLET_REQUIRED_ERROR)
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=USER_NOT_FOUND_ERROR
        )
    user.phone = None
    user.email = None
    user.address = None
    user.public_key = None
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Personal data deleted successfully"}

@router.get(
    "/user/export",
    response_model=dict,
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def export_user_data(
    db: Annotated[Session, Depends(get_db)],
    wallet_address: str = None
):
    """Export all user data (GDPR data portability)"""
    if not wallet_address:
        raise HTTPException(status_code=400, detail=WALLET_REQUIRED_ERROR)
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=USER_NOT_FOUND_ERROR
        )
    export_data = {
        "user_data": {
            "wallet_address": user.wallet_address,
            "phone": user.phone,
            "email": user.email,
            "address": user.address,
            "default_building_id": user.default_building_id,
            "public_key": user.public_key,
            "api_base_url": user.api_base_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        "export_date": datetime.now(timezone.utc).isoformat(),
        "format_version": "1.0"
    }
    return export_data

# Alternative endpoints with different naming (if you prefer)
@router.get(
    "/user/preferences",
    response_model=UserSettingsResponse,
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def get_user_preferences(
    db: Annotated[Session, Depends(get_db)],
    wallet_address: str = None
):
    """Alias for get_user_settings"""
    return get_user_settings(db, wallet_address)

@router.post(
    "/user/preferences",
    response_model=UserSettingsResponse,
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def save_user_preferences(
    settings_data: UserSettingsCreate,
    db: Annotated[Session, Depends(get_db)],
    wallet_address: str = None
):
    """Alias for save_user_settings"""
    return save_user_settings(settings_data, db, wallet_address)