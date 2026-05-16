
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from db import get_db
from db.functions import submit_rating, get_service_score, get_user_ratings
from models.rate import Rate
from controllers.auth import get_current_user
from typing import List, Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field
import os

# Error message constants
RATE_NOT_FOUND_MSG = "Rate not found"

from utils.auth_dependencies import get_current_user_role, resolve_registered_user
router = APIRouter(
    prefix="/rates",
    tags=["Rates"],
    dependencies=[Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
)

# Get encryption key from environment
RATING_ENCRYPTION_KEY = os.getenv("RATING_ENCRYPTION_KEY", "default_key_change_in_production")

# Valid rating types
RATING_TYPE_THERMAL = "thermal_comfort"   # Occupant: 1–10 cold → hot
RATING_TYPE_SERVICE = "service_quality"   # Manager/Admin: 1–5 stars

# Pydantic schemas
class RateBase(BaseModel):
    service_id: int
    rating: float = Field(..., ge=1.0, le=10.0, description="1-10 for thermal comfort, 1-5 for service quality")
    rating_type: str = Field(RATING_TYPE_SERVICE, description="'thermal_comfort' or 'service_quality'")

    @property
    def max_rating(self):
        return 10.0 if self.rating_type == RATING_TYPE_THERMAL else 5.0

class RateCreate(RateBase):
    feedback: Optional[str] = None

    def validate_rating_range(self):
        if self.rating_type == RATING_TYPE_THERMAL and self.rating > 10.0:
            raise ValueError("Thermal comfort rating must be between 1 and 10")
        if self.rating_type == RATING_TYPE_SERVICE and self.rating > 5.0:
            raise ValueError("Service quality rating must be between 1 and 5")

class RateRead(RateBase):
    id: int
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class ServiceScore(BaseModel):
    service_id: int
    average_rating: float
    total_ratings: int
    rating_distribution: dict


def _require_registered_user(user_payload: dict, db: Session):
    return resolve_registered_user(user_payload, db)

@router.post(
    "/submit",
    responses={
        400: {"description": "Wallet address required for rating"},
        403: {"description": "You are not authorized to rate this service."},
        500: {"description": "Database error"},
    },
)
def submit_user_rating(
    rate: RateCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """
    Submit or update a rating for a service with encrypted wallet.
    Occupants submit thermal_comfort (1-10), managers/admins submit service_quality (1-5).
    Each wallet can only have one rating per (service, rating_type).
    """
    try:
        current_user = get_current_user(request)
        wallet_address = current_user.get("wallet")
        _require_registered_user(user, db)
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address required for rating")

        # Enforce role ↔ rating_type consistency
        user_role = user.get("role", "")
        if user_role == "OCCUPANT" and rate.rating_type != RATING_TYPE_THERMAL:
            raise HTTPException(status_code=403, detail="Occupants can only submit thermal comfort ratings")
        if user_role in ("BUILDING_MANAGER", "ADMIN") and rate.rating_type != RATING_TYPE_SERVICE:
            raise HTTPException(status_code=403, detail="Managers/Admins can only submit service quality ratings")

        # Enforce value range per type
        rate.validate_rating_range()

        from sqlalchemy import text

        encrypt_result = db.execute(text("SELECT encrypt_wallet(:wallet, :key) as encrypted_wallet"),
                                  {"wallet": wallet_address, "key": RATING_ENCRYPTION_KEY})
        encrypted_wallet = encrypt_result.fetchone()[0]

        # Upsert key: one rating per (service, wallet, rating_type)
        existing_result = db.execute(text("""
            SELECT id FROM rates
            WHERE service_id = :service_id
              AND encrypted_wallet = :encrypted_wallet
              AND rating_type = :rating_type
        """), {
            "service_id": rate.service_id,
            "encrypted_wallet": encrypted_wallet,
            "rating_type": rate.rating_type,
        })

        existing_row = existing_result.fetchone()

        if existing_row:
            existing_id = existing_row[0]
            update_result = db.execute(text("""
                UPDATE rates
                SET rating = :rating,
                    feedback = :feedback,
                    updated_at = NOW()
                WHERE id = :rate_id
                RETURNING id, service_id, rating, rating_type, feedback, created_at, updated_at
            """), {
                "rating": rate.rating,
                "feedback": rate.feedback,
                "rate_id": existing_id,
            })

            result = update_result.fetchone()
            db.commit()

            return {
                "success": True,
                "message": "Rating updated successfully",
                "is_new_rating": False,
                "data": {
                    "rate_id": result[0],
                    "service_id": result[1],
                    "rating": float(result[2]),
                    "rating_type": result[3],
                    "feedback": result[4],
                    "created_at": result[5].isoformat(),
                    "updated_at": result[6].isoformat(),
                }
            }
        else:
            insert_result = db.execute(text("""
                INSERT INTO rates (service_id, encrypted_wallet, rating, rating_type, feedback, created_at, updated_at)
                VALUES (:service_id, :encrypted_wallet, :rating, :rating_type, :feedback, NOW(), NOW())
                RETURNING id, service_id, rating, rating_type, feedback, created_at, updated_at
            """), {
                "service_id": rate.service_id,
                "encrypted_wallet": encrypted_wallet,
                "rating": rate.rating,
                "rating_type": rate.rating_type,
                "feedback": rate.feedback,
            })

            result = insert_result.fetchone()
            db.commit()

            return {
                "success": True,
                "message": "Rating submitted successfully",
                "is_new_rating": True,
                "data": {
                    "rate_id": result[0],
                    "service_id": result[1],
                    "rating": float(result[2]),
                    "rating_type": result[3],
                    "feedback": result[4],
                    "created_at": result[5].isoformat(),
                    "updated_at": result[6].isoformat(),
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get(
    "/service/{service_id}/score",
    responses={
        403: {"description": "You are not authorized to view this service's ratings."},
        404: {"description": "No ratings found for this service"},
        500: {"description": "Database error"},
    },
)
def get_service_rating_score(
    service_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """
    Get aggregated score and statistics for a service.
    """
    try:
        _require_registered_user(user, db)
        result = get_service_score(db, service_id)
        if not result or result.total_ratings == 0:
            raise HTTPException(status_code=404, detail="No ratings found for this service")
        return {
            "service_id": result.service_id,
            "average_rating": result.average_rating,
            "total_ratings": result.total_ratings,
            "rating_distribution": result.rating_distribution
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get(
    "/my-ratings",
    responses={
        400: {"description": "Wallet address required"},
        403: {"description": "You are not authorized to view these ratings."},
        500: {"description": "Database error"},
    },
)
def get_my_ratings(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """
    Get all ratings submitted by the current user.
    """
    try:
        current_user = get_current_user(request)
        wallet_address = current_user.get("wallet")
        if not wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address required")
        _require_registered_user(user, db)
        
        ratings = get_user_ratings(db, wallet_address)
        
        return [
            {
                "rate_id": rating.id,
                "service_id": rating.service_id,
                "service_name": getattr(rating, 'service_name', None),
                "rating": rating.rating,
                "feedback": rating.feedback,
                "created_at": rating.created_at.isoformat() if rating.created_at else None,
                "updated_at": rating.updated_at.isoformat() if rating.updated_at else None
            }
            for rating in ratings
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Keep your existing endpoints for backward compatibility
@router.post(
    "/",
    response_model=RateRead,
    responses={
        403: {"description": "You are not authorized to create a rating for this service."},
        500: {"description": "Database error"},
    },
)
def create_rate(
    rate: RateCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """Legacy endpoint - consider using /submit instead for encrypted ratings"""
    _require_registered_user(user, db)
    db_rate = Rate(**rate.dict())
    db.add(db_rate)
    db.commit()
    db.refresh(db_rate)
    return db_rate

@router.get(
    "/",
    response_model=List[RateRead],
    responses={
        500: {"description": "Database error"},
    },
)
def read_rates(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))],
    skip: int = 0,
    limit: int = 100
):
    try:
        _require_registered_user(user, db)
        return db.query(Rate).offset(skip).limit(limit).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get(
    "/{rate_id}",
    response_model=RateRead,
    responses={
        404: {"description": RATE_NOT_FOUND_MSG},
        500: {"description": "Database error"},
    },
)
def read_rate(
    rate_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    try:
        _require_registered_user(user, db)
        rate = db.query(Rate).filter(Rate.id == rate_id).first()
        if not rate:
            raise HTTPException(status_code=404, detail=RATE_NOT_FOUND_MSG)
        return rate
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put(
    "/{rate_id}",
    response_model=RateRead,
    responses={
        404: {"description": RATE_NOT_FOUND_MSG},
        500: {"description": "Database error"},
    },
)
def update_rate(
    rate_id: int,
    rate: RateCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    try:
        _require_registered_user(user, db)
        db_rate = db.query(Rate).filter(Rate.id == rate_id).first()
        if not db_rate:
            raise HTTPException(status_code=404, detail=RATE_NOT_FOUND_MSG)
        for key, value in rate.dict().items():
            setattr(db_rate, key, value)
        db.commit()
        db.refresh(db_rate)
        return db_rate
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete(
    "/{rate_id}",
    responses={
        404: {"description": RATE_NOT_FOUND_MSG},
        500: {"description": "Database error"},
    },
)
def delete_rate(
    rate_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    try:
        _require_registered_user(user, db)
        db_rate = db.query(Rate).filter(Rate.id == rate_id).first()
        if not db_rate:
            raise HTTPException(status_code=404, detail=RATE_NOT_FOUND_MSG)
        db.delete(db_rate)
        db.commit()
        return {"detail": "Rate deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Test endpoints (remove in production)
class RateTestCreate(BaseModel):
    service_id: int
    wallet_address: str
    rating: float = Field(..., ge=1.0, le=10.0, description="Thermal comfort rating 1 (cold) to 10 (hot)")
    feedback: Optional[str] = None

@router.post(
    "/test-upsert",
    responses={
        500: {"description": "Upsert test error"},
    },
)
def test_upsert_functionality(
    rate: RateTestCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """
    Test endpoint that demonstrates UPSERT with encrypted wallet addresses.
    Same wallet + same service = UPDATE existing rating.
    This endpoint is for testing only - remove in production.
    """
    try:
        _require_registered_user(user, db)
        from sqlalchemy import text
        
        # First encrypt the wallet address using deterministic encryption
        encrypt_result = db.execute(text("SELECT encrypt_wallet(:wallet, :key) as encrypted_wallet"), 
                                  {"wallet": rate.wallet_address, "key": "test_key"})
        encrypted_wallet = encrypt_result.fetchone()[0]
        
        # Check if rating already exists for this service and encrypted wallet
        existing_result = db.execute(text("""
            SELECT id FROM rates 
            WHERE service_id = :service_id 
            AND encrypted_wallet = :encrypted_wallet
        """), {
            "service_id": rate.service_id,
            "encrypted_wallet": encrypted_wallet
        })
        
        existing_row = existing_result.fetchone()
        
        if existing_row:
            # UPDATE existing rating
            existing_id = existing_row[0]
            update_result = db.execute(text("""
                UPDATE rates 
                SET rating = :rating,
                    feedback = :feedback,
                    updated_at = NOW()
                WHERE id = :rate_id
                RETURNING id, service_id, rating, feedback, created_at, updated_at
            """), {
                "rating": rate.rating,
                "feedback": rate.feedback,
                "rate_id": existing_id
            })
            
            result = update_result.fetchone()
            db.commit()
            
            return {
                "success": True,
                "message": "Rating UPDATED successfully with encryption",
                "action": "UPDATE",
                "data": {
                    "rate_id": result[0],
                    "service_id": result[1],
                    "rating": float(result[2]),
                    "feedback": result[3],
                    "created_at": result[4].isoformat(),
                    "updated_at": result[5].isoformat(),
                    "original_wallet": rate.wallet_address,
                    "encrypted_wallet_preview": encrypted_wallet[:50] + "..." if len(encrypted_wallet) > 50 else encrypted_wallet
                }
            }
        else:
            # INSERT new rating
            insert_result = db.execute(text("""
                INSERT INTO rates (service_id, encrypted_wallet, rating, feedback, created_at, updated_at)
                VALUES (:service_id, :encrypted_wallet, :rating, :feedback, NOW(), NOW())
                RETURNING id, service_id, rating, feedback, created_at, updated_at
            """), {
                "service_id": rate.service_id,
                "encrypted_wallet": encrypted_wallet,
                "rating": rate.rating,
                "feedback": rate.feedback
            })
            
            result = insert_result.fetchone()
            db.commit()
            
            return {
                "success": True,
                "message": "Rating INSERTED successfully with encryption",
                "action": "INSERT",
                "data": {
                    "rate_id": result[0],
                    "service_id": result[1],
                    "rating": float(result[2]),
                    "feedback": result[3],
                    "created_at": result[4].isoformat(),
                    "updated_at": result[5].isoformat(),
                    "original_wallet": rate.wallet_address,
                    "encrypted_wallet_preview": encrypted_wallet[:50] + "..." if len(encrypted_wallet) > 50 else encrypted_wallet
                }
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upsert test error: {str(e)}")

@router.get(
    "/test-view-data",
    responses={
        500: {"description": "View data error"},
    },
)
def view_encrypted_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user_role(["BUILDING_MANAGER", "ADMIN", "OCCUPANT"]))]
):
    """
    View all stored encrypted data in the database.
    This endpoint is for testing only - remove in production.
    """
    try:
        _require_registered_user(user, db)
        from sqlalchemy import text
        
        result = db.execute(text("""
            SELECT 
                r.id,
                r.service_id,
                s.name as service_name,
                r.encrypted_wallet,
                r.rating,
                r.feedback,
                r.created_at,
                r.updated_at
            FROM rates r
            LEFT JOIN services s ON r.service_id = s.id
            ORDER BY r.updated_at DESC, r.created_at DESC
            LIMIT 20
        """))
        
        rows = result.fetchall()
        
        return {
            "success": True,
            "message": f"Found {len(rows)} encrypted ratings",
            "data": [
                {
                    "rate_id": row[0],
                    "service_id": row[1],
                    "service_name": row[2],
                    "encrypted_wallet_preview": row[3][:50] + "..." if len(row[3]) > 50 else row[3],
                    "rating": float(row[4]),
                    "feedback": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None
                }
                for row in rows
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"View data error: {str(e)}")
