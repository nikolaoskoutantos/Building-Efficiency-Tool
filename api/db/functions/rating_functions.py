"""
Python utilities for rating database functions.
"""

import os
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_encryption_key():
    """Get encryption key from environment."""
    return os.getenv("RATING_ENCRYPTION_KEY", "your-secret-rating-key")

def submit_rating(
    db: Session, 
    service_id: int, 
    wallet_address: str, 
    rating: float, 
    feedback: str = None
):
    """
    Submit or update a rating using PostgreSQL function.
    Returns the result of the upsert operation.
    """
    result = db.execute(
        text("""
            SELECT * FROM upsert_rating(
                :service_id, 
                :wallet_address, 
                :rating, 
                :feedback,
                :encryption_key
            )
        """),
        {
            "service_id": service_id,
            "wallet_address": wallet_address,
            "rating": rating,
            "feedback": feedback,
            "encryption_key": get_encryption_key()
        }
    ).fetchone()
    
    return result

def get_service_score(db: Session, service_id: int):
    """
    Get aggregated score for a service.
    Returns average rating, total ratings, and distribution.
    """
    result = db.execute(
        text("SELECT * FROM calculate_service_score(:service_id)"),
        {"service_id": service_id}
    ).fetchone()
    
    return result

def get_user_ratings(db: Session, wallet_address: str):
    """
    Get all ratings submitted by a specific wallet.
    """
    # First encrypt the wallet to search for it
    encrypted_wallet_result = db.execute(
        text("SELECT encrypt_wallet(:wallet, :key) as encrypted_wallet"),
        {
            "wallet": wallet_address,
            "key": get_encryption_key()
        }
    ).fetchone()
    
    if not encrypted_wallet_result:
        return []
    
    # Query ratings using the encrypted wallet
    results = db.execute(
        text("""
            SELECT r.id, r.service_id, r.rating, r.feedback, 
                   r.created_at, r.updated_at, s.name as service_name
            FROM rates r 
            LEFT JOIN services s ON r.service_id = s.id
            WHERE r.encrypted_wallet = :encrypted_wallet
            ORDER BY r.updated_at DESC
        """),
        {"encrypted_wallet": encrypted_wallet_result.encrypted_wallet}
    ).fetchall()
    
    return results
