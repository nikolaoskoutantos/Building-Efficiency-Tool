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

from utils.auth_dependencies import get_current_user_role, resolve_registered_user
router = APIRouter(
    tags=["Users"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)

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
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Get user settings by wallet address"""
    user_obj = resolve_registered_user(user, db)
    if not user_obj:
        wallet = user.get("wallet")
        user_obj = User(wallet_address=wallet.strip().lower() if isinstance(wallet, str) else wallet)
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)
    return user_obj

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
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Save or update user settings"""
    user_obj = resolve_registered_user(user, db)
    for field, value in settings_data.dict(exclude_unset=True).items():
        setattr(user_obj, field, value)
    user_obj.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_obj)
    return user_obj

@router.delete(
    "/user/settings",
    responses={
        400: {"description": WALLET_REQUIRED_ERROR},
        404: {"description": USER_NOT_FOUND_ERROR}
    }
)
def delete_user_settings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Delete user's personal data (GDPR right to be forgotten)"""
    user_obj = resolve_registered_user(user, db)
    user_obj.phone = None
    user_obj.email = None
    user_obj.address = None
    user_obj.public_key = None
    user_obj.updated_at = datetime.now(timezone.utc)
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
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Export all user data (GDPR data portability)"""
    user_obj = resolve_registered_user(user, db)
    export_data = {
        "user_data": {
            "wallet_address": user_obj.wallet_address,
            "phone": user_obj.phone,
            "email": user_obj.email,
            "address": user_obj.address,
            "default_building_id": user_obj.default_building_id,
            "public_key": user_obj.public_key,
            "api_base_url": user_obj.api_base_url,
            "created_at": user_obj.created_at.isoformat() if user_obj.created_at else None,
            "updated_at": user_obj.updated_at.isoformat() if user_obj.updated_at else None,
            "last_login": user_obj.last_login.isoformat() if user_obj.last_login else None,
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
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Alias for get_user_settings"""
    return get_user_settings(db, user)

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
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Alias for save_user_settings"""
    return save_user_settings(settings_data, db, user)
