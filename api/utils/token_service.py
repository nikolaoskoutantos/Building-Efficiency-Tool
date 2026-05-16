"""token_service.py — central JWT issuance, verification, and revocation.

All user tokens (access + refresh) are tracked in the user_tokens table.
Every authenticated request validates the jti against this table so that
revoked tokens are rejected immediately, regardless of their expiry time.

Environment variables:
  SESSION_SECRET_KEY    — HS256 signing secret (required)
  ACCESS_TOKEN_MINUTES  — access token lifetime in minutes  (default 15)
  REFRESH_TOKEN_DAYS    — refresh token lifetime in days    (default 7)
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.user_token import UserToken, TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_JWT_SECRET: Optional[str] = os.environ.get("SESSION_SECRET_KEY")
_JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.environ.get("REFRESH_TOKEN_DAYS", "7"))


def _secret() -> str:
    if not _JWT_SECRET:
        raise RuntimeError("SESSION_SECRET_KEY must be set in environment variables.")
    return _JWT_SECRET


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Token issuance
# ---------------------------------------------------------------------------

def issue_token_pair(
    user_id: int,
    role: str,
    wallet: Optional[str],
    db: Session,
) -> Tuple[str, str]:
    """Issue an access + refresh token pair and persist both in user_tokens.

    Returns:
        (access_token, refresh_token) — both as signed JWT strings.

    Example access token payload:
        {
            "sub": "42",
            "user_id": 42,
            "role": "BUILDING_MANAGER",
            "wallet": "0xabc...",
            "jti": "550e8400-e29b-41d4-a716-446655440000",
            "typ": "access",
            "exp": 1747123456
        }

    Example refresh token payload:
        {
            "sub": "42",
            "user_id": 42,
            "jti": "660e8400-e29b-41d4-a716-446655441111",
            "typ": "refresh",
            "exp": 1747728256
        }
    """
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    now = _now()
    access_exp = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    refresh_exp = now + timedelta(days=REFRESH_TOKEN_DAYS)

    access_payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "role": role,
        "wallet": wallet,
        "jti": access_jti,
        "typ": TOKEN_TYPE_ACCESS,
        "exp": access_exp,
    }
    refresh_payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "jti": refresh_jti,
        "typ": TOKEN_TYPE_REFRESH,
        "exp": refresh_exp,
    }

    access_token = jwt.encode(access_payload, _secret(), algorithm=_JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, _secret(), algorithm=_JWT_ALGORITHM)

    db.add(UserToken(
        jti=access_jti,
        user_id=user_id,
        token_type=TOKEN_TYPE_ACCESS,
        expires_at=access_exp,
    ))
    db.add(UserToken(
        jti=refresh_jti,
        user_id=user_id,
        token_type=TOKEN_TYPE_REFRESH,
        expires_at=refresh_exp,
    ))
    db.commit()

    return access_token, refresh_token


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def verify_access_token(token: str, db: Session) -> dict:
    """Fully verify an access token: signature, expiry, jti in DB, not revoked.

    Raises HTTP 401 on any validation failure.
    Returns the decoded payload dict on success.
    """
    payload = _decode_jwt(token)

    jti = payload.get("jti")
    typ = payload.get("typ")

    if not jti or typ != TOKEN_TYPE_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    record = db.query(UserToken).filter(UserToken.jti == jti).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not recognised",
        )
    if record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    return payload


def verify_refresh_token(token: str, db: Session) -> Tuple[dict, UserToken]:
    """Verify a refresh token and return (payload, UserToken record).

    If the token is already revoked, ALL tokens for that user are immediately
    revoked (token-theft response) before raising 401.
    """
    payload = _decode_jwt(token)

    jti = payload.get("jti")
    typ = payload.get("typ")

    if not jti or typ != TOKEN_TYPE_REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    record = db.query(UserToken).filter(UserToken.jti == jti).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not recognised",
        )

    if record.revoked_at is not None:
        # Token-theft detection: a revoked refresh token was reused.
        # Immediately revoke ALL active tokens for this user.
        revoke_all_user_tokens(record.user_id, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected — all sessions have been revoked",
        )

    return payload, record


# ---------------------------------------------------------------------------
# Token revocation
# ---------------------------------------------------------------------------

def revoke_token(jti: str, db: Session) -> bool:
    """Mark a single token as revoked. Returns True if the token was found."""
    record = db.query(UserToken).filter(UserToken.jti == jti).first()
    if not record:
        return False
    if record.revoked_at is None:
        record.revoked_at = _now()
        db.commit()
    return True


def revoke_all_user_tokens(user_id: int, db: Session) -> int:
    """Revoke all active (non-expired, non-revoked) tokens for a user.

    Returns the number of rows updated.
    """
    count = (
        db.query(UserToken)
        .filter(
            UserToken.user_id == user_id,
            UserToken.revoked_at.is_(None),
        )
        .update({"revoked_at": _now()}, synchronize_session=False)
    )
    db.commit()
    return count


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _decode_jwt(token: str) -> dict:
    """Decode and validate JWT signature + expiry. Raises HTTP 401 on failure."""
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        return jwt.decode(token, _secret(), algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
